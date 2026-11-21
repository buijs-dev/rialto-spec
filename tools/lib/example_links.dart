import 'dart:io';

import 'spec_repository.dart';

/// Writes the `Examples:` line under every requirement group of the specification below [root], and returns how
/// many groups have one.
///
/// The line links the test contracts that belong to the group: an invalid test contract through the requirement
/// its diagnostic code enforces (the table in `spec/contract.md`), a valid one through the groups listed in
/// [validTestContracts]. Run it after adding a test contract. A second run changes nothing.
///
/// The specification is built in slices. While the Shipment example is not there, a group without a test contract
/// gets [pendingExamples]; once it is there, such a group is left without a line and `check_spec` reports it.
int writeExampleLinks(Directory root) {
  final repository = SpecRepository(root);
  final testContracts = _testContractsByGroup(repository);
  final shipmentExists = repository.file('examples/shipment/README.md').existsSync();

  var groupsWithExamples = 0;
  for (final document in repository.existingRequirementDocuments.entries) {
    final prefix = document.key;
    final file = document.value;
    // From the directory of the document up to the repository: `spec/core.md` is one directory deep.
    final up = '../' * (repository.relative(file).split('/').length - 1);

    final withoutLines = file.readAsStringSync().replaceAll(_examplesLine, '');
    final groupHeading = RegExp('^(### |## )($prefix\\d+)\\. [^\\n]+', multiLine: true);
    final withLines = withoutLines.replaceAllMapped(groupHeading, (match) {
      final heading = match.group(0)!;
      final group = match.group(2)!;
      final examples = _examples(group, testContracts[group] ?? {}, up, shipmentExists);
      if (examples == null) {
        return heading;
      }

      groupsWithExamples++;
      return '$heading\n\nExamples: $examples.';
    });

    file.writeAsStringSync(withLines);
  }
  return groupsWithExamples;
}

/// The valid test contracts and the requirement groups they are an example of. A contract over several files is
/// named by its directory. An entry is added with its test contract.
const validTestContracts = {
  'valid/fragments/': ['K5'],
  'valid/fragments-recursive/': ['K5'],
  'valid/minimal.yaml': ['K1'],
};

/// Groups that need no example: their requirements apply to the specification itself, not to a contract or a
/// generator.
const exemptGroups = {'C7': 'none: these requirements apply to the specification itself'};

/// What a group without examples gets while the Shipment example, the main source of examples, is not there yet.
const pendingExamples = 'none yet: the scenarios of the Shipment example follow in a later slice';

final _examplesLine = RegExp(r'\n\nExamples: [^\n]*');
final _expectedCode = RegExp(r'^# expect: (\S+)');
final _codeRow = RegExp(r'^\| `(RIALTO-\w+)` \|.*\| ([^|]+) \|$');
final _requirement = RegExp(r'[ACKDELMPQRSUV]\d+\.\d+');

/// What follows `Examples: ` for [group], or null when the group gets no line.
String? _examples(String group, Set<String> testContracts, String up, bool shipmentExists) {
  if (exemptGroups.containsKey(group)) {
    return exemptGroups[group];
  }

  if (testContracts.isNotEmpty) {
    final links = (testContracts.toList()..sort()).map((path) => '[`$path`](${up}examples/contracts/$path)');
    return 'test contracts ${links.join(', ')}';
  }

  return shipmentExists ? null : pendingExamples;
}

/// Per requirement group, the test contracts that are an example of it, as paths relative to `examples/contracts`.
Map<String, Set<String>> _testContractsByGroup(SpecRepository repository) {
  final byGroup = <String, Set<String>>{};
  void add(String group, String testContract) => byGroup.putIfAbsent(group, () => {}).add(testContract);

  final requirementsOfCode = _requirementsByCode(repository);
  for (final testContract in repository.invalidTestContracts) {
    // A test contract without `# expect:` has no group; check_spec reports it.
    final code = _expectedCode.firstMatch(testContract.readAsStringSync())?.group(1);
    for (final requirement in requirementsOfCode[code] ?? const <String>[]) {
      add(_group(requirement), _name(repository, testContract));
    }
  }

  validTestContracts.forEach((path, groups) {
    final exists =
        FileSystemEntity.typeSync('${repository.root.path}/examples/contracts/$path') != FileSystemEntityType.notFound;

    if (!exists) {
      return;
    }

    for (final group in groups) {
      add(group, path);
    }
  });

  return byGroup;
}

/// Per diagnostic code, the requirements the last column of its row in `spec/contract.md` names.
Map<String, List<String>> _requirementsByCode(SpecRepository repository) {
  final byCode = <String, List<String>>{};
  for (final line in repository.file('spec/contract.md').readAsLinesSync()) {
    final row = _codeRow.firstMatch(line);
    if (row == null) {
      continue;
    }

    byCode[row.group(1)!] = _requirement.allMatches(row.group(2)!).map((match) => match.group(0)!).toList();
  }
  return byCode;
}

/// The group of a requirement: `K5` of `K5.2`.
String _group(String requirement) => requirement.substring(0, requirement.indexOf('.'));

/// A test contract as the Examples line names it: its path below `examples/contracts`, and for a contract over
/// several files its directory, with a `/` at the end.
String _name(SpecRepository repository, File testContract) {
  final path = repository.relative(testContract).substring('examples/contracts/'.length);
  const rootFile = 'contract.rialto.yaml';
  return path.endsWith('/$rootFile') ? path.substring(0, path.length - rootFile.length) : path;
}
