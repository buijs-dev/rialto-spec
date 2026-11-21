import 'dart:convert';
import 'dart:io';

import 'spec_repository.dart';

/// What the checks found: every error, and how many requirements the specification has.
class SpecReport {
  SpecReport(this.errors, this.requirements);

  /// One line per error: `<file>: <what is wrong>`.
  final List<String> errors;

  final int requirements;
}

/// Checks the documents of the specification below [root] for consistency:
///
/// 1. Requirements: identifiers are unique, use the prefix of their document and count up per group.
/// 2. Key words: no lowercase or mixed-case BCP 14 key words inside requirements.
/// 3. Diagnostic codes: the table of standard codes has well-formed, unique codes, and every invalid test
///    contract expects one of them.
/// 4. References: every requirement identifier mentioned anywhere exists.
/// 5. Terminology: no bare "binding" (write field, operation or protocol binding), and no names of specific
///    projects in the specification.
/// 6. Links: every relative link and anchor resolves.
/// 7. Learning by example: every requirement group has an `Examples:` line (`bin/example_links.dart` writes it).
///
/// The specification is built in slices: each check covers the documents that exist. A reference to a
/// requirement of a document that does not exist yet is accepted; one to a missing requirement of an existing
/// document is an error.
///
/// Whether the examples are valid contracts is not checked here: that needs the tooling, and the tooling tests
/// itself against the examples.
SpecReport checkSpec(Directory root) {
  final checks = _SpecChecks(SpecRepository(root))
    ..requirementsAndKeyWords()
    ..diagnosticCodes()
    ..markdown()
    ..examplesLines();
  return SpecReport(checks.errors, checks.requirements.length);
}

final _requirementLine = RegExp(r'^- \*\*(' + requirementId + r')\*\* (.*)$', multiLine: true);
final _requirementReference = RegExp(r'(?<![\w.#-])(' + requirementId + r')(?![\w])');
final _lowercaseKeyWord = RegExp(r'\b(must|shall|should|may)\b');
final _mixedCaseKeyWord = RegExp(r'\b((?:MUST|SHALL|SHOULD) not)\b');
final _diagnosticCode = RegExp(r'^RIALTO-[KSP]\d{3}$');
final _expectedCode = RegExp(r'^# expect: (\S+)');
final _binding = RegExp(r'\b(\w+)\s+(bindings?)\b|\b(bindings?)\b', caseSensitive: false);
final _quotedBinding = RegExp(r'"bindings?"', caseSensitive: false);
final _forbiddenName = RegExp(r'\b(Fabrio|StrataStaX)\b', caseSensitive: false);
final _link = RegExp(r'\]\(([^)\s]+)\)');
final _linkTarget = RegExp(r'\]\([^)]*\)');
final _scheme = RegExp(r'^[a-z]+:');
final _heading = RegExp(r'^#+ (.*)$', multiLine: true);
final _fencedCode = RegExp(r'```.*?```', dotAll: true);
final _inlineCode = RegExp(r'`[^`]*`');

/// The words that may stand before "binding".
const _bindingKinds = {'operation', 'field', 'protocol'};

class _SpecChecks {
  _SpecChecks(this.repository);

  final SpecRepository repository;
  final List<String> errors = [];

  /// Every requirement identifier of the documents that exist.
  final Set<String> requirements = {};

  void _error(FileSystemEntity file, String message) {
    errors.add('${repository.relative(file)}: $message');
  }

  // 1 and 2. Requirements and key words ---------------------------------------------------------------------------

  void requirementsAndKeyWords() {
    repository.existingRequirementDocuments.forEach((prefix, document) {
      final identifiersByGroup = <String, List<String>>{};
      for (final match in _requirementLine.allMatches(document.readAsStringSync())) {
        final identifier = match.group(1)!;
        final body = match.group(2)!;

        if (!identifier.startsWith(prefix)) {
          _error(document, '$identifier: identifier does not use prefix $prefix');
        }
        if (!requirements.add(identifier)) {
          _error(document, '$identifier: duplicate identifier');
        }

        final group = identifier.substring(0, identifier.indexOf('.'));
        identifiersByGroup.putIfAbsent(group, () => []).add(identifier);
        _keyWords(document, identifier, body);
      }

      identifiersByGroup.forEach((group, identifiers) {
        final expected = [for (var number = 1; number <= identifiers.length; number++) '$group.$number'];
        if (identifiers.join(' ') != expected.join(' ')) {
          _error(document, '$group: expected sequential identifiers $expected, got $identifiers');
        }
      });
    });
  }

  void _keyWords(File document, String identifier, String body) {
    final prose = _withoutCode(body);
    for (final match in _lowercaseKeyWord.allMatches(prose)) {
      _error(document, "$identifier: lowercase key word '${match.group(1)}'");
    }
    for (final match in _mixedCaseKeyWord.allMatches(prose)) {
      _error(document, "$identifier: mixed-case key word '${match.group(1)}', write it in capitals");
    }
  }

  // 3. Diagnostic codes -------------------------------------------------------------------------------------------

  void diagnosticCodes() {
    final contract = repository.file('spec/contract.md');
    final rows = _tableAfter(contract.readAsStringSync(), '## Standard diagnostic codes');
    if (rows == null) {
      _error(contract, 'Standard diagnostic codes table missing');
      return;
    }

    final codes = <String>{};
    for (final row in rows) {
      final code = row.first.replaceAll('`', '');
      if (!_diagnosticCode.hasMatch(code)) _error(contract, "invalid diagnostic code '$code'");
      if (!codes.add(code)) _error(contract, "duplicate diagnostic code '$code'");
    }

    for (final testContract in repository.invalidTestContracts) {
      final expected = _expectedCode.firstMatch(testContract.readAsStringSync())?.group(1);
      if (expected == null) {
        _error(testContract, "missing '# expect: RIALTO-...' on first line");
      } else if (!codes.contains(expected)) {
        _error(testContract, "expects undocumented diagnostic code '$expected'");
      }
    }
  }

  // 4, 5 and 6. References, terminology and links -----------------------------------------------------------------

  void markdown() {
    for (final file in repository.markdownFiles) {
      final text = file.readAsStringSync();
      // The prose of the file: without code, without the targets of links, and without the word "binding" in quotes.
      final prose = _withoutCode(text).replaceAll(_linkTarget, ']').replaceAll(_quotedBinding, '');

      _references(file, prose);
      _bindings(file, prose);
      if (repository.relative(file).startsWith('spec/')) _forbiddenNames(file, text);
      _links(file, text);
    }
  }

  void _references(File file, String prose) {
    final mentioned = _requirementReference.allMatches(prose).map((match) => match.group(1)!).toSet().toList()..sort();
    final pending = repository.pendingPrefixes;
    for (final identifier in mentioned) {
      final ofLaterSlice = pending.contains(identifier[0]);
      if (!requirements.contains(identifier) && !ofLaterSlice) {
        _error(file, 'reference to unknown requirement $identifier');
      }
    }
  }

  void _bindings(File file, String prose) {
    for (final match in _binding.allMatches(prose)) {
      final kind = match.group(1);
      final word = match.group(2) ?? match.group(3)!;
      if (kind != null && _bindingKinds.contains(kind.toLowerCase())) continue;

      final line = '\n'.allMatches(prose.substring(0, match.start)).length + 1;
      _error(file, "line $line: '$word' without operation, field or protocol");
    }
  }

  void _forbiddenNames(File file, String text) {
    for (final match in _forbiddenName.allMatches(text)) {
      _error(file, "mentions '${match.group(1)}'");
    }
  }

  void _links(File file, String text) {
    for (final match in _link.allMatches(text)) {
      final target = match.group(1)!;
      if (_scheme.hasMatch(target)) continue;

      final hash = target.indexOf('#');
      final path = hash < 0 ? target : target.substring(0, hash);
      final anchor = hash < 0 ? '' : target.substring(hash + 1);
      final destination = path.isEmpty ? file.path : file.parent.uri.resolve(path).toFilePath();

      if (FileSystemEntity.typeSync(destination) == FileSystemEntityType.notFound) {
        _error(file, 'broken link $target');
      } else if (anchor.isNotEmpty && destination.endsWith('.md') && !_anchors(File(destination)).contains(anchor)) {
        _error(file, 'broken anchor $target');
      }
    }
  }

  // 7. Learning by example ----------------------------------------------------------------------------------------

  void examplesLines() {
    repository.existingRequirementDocuments.forEach((prefix, document) {
      final groupHeading = RegExp('^##+ ($prefix\\d+)\\. ');
      final lines = const LineSplitter().convert(document.readAsStringSync());
      for (var index = 0; index < lines.length; index++) {
        final group = groupHeading.firstMatch(lines[index])?.group(1);
        if (group == null) continue;

        final below = lines.skip(index + 1).take(3);
        if (!below.any((line) => line.startsWith('Examples: '))) {
          _error(document, '$group has no Examples line (run tools/bin/example_links.dart)');
        }
      }
    });
  }
}

/// [text] without fenced and inline code, so the rules for prose ignore code samples.
String _withoutCode(String text) => text.replaceAll(_fencedCode, '').replaceAll(_inlineCode, '');

/// The rows of the first table after [heading], each as its cells, without the header and the line under it; null
/// when [heading] is not in [text].
List<List<String>>? _tableAfter(String text, String heading) {
  final start = text.indexOf(heading);
  if (start < 0) return null;

  final rows = <List<String>>[];
  for (final line in const LineSplitter().convert(text.substring(start)).skip(1)) {
    if (line.startsWith('|')) {
      rows.add(_cells(line));
    } else if (rows.isNotEmpty || line.startsWith('#')) {
      break;
    }
  }
  return rows.skip(2).toList();
}

/// The cells of one table row, without the bars at both ends.
List<String> _cells(String row) {
  var inner = row.trim();
  if (inner.startsWith('|')) inner = inner.substring(1);
  if (inner.endsWith('|')) inner = inner.substring(0, inner.length - 1);
  return inner.split('|').map((cell) => cell.trim()).toList();
}

/// The anchors of the headings of a Markdown [file], as a link names them.
Set<String> _anchors(File file) =>
    _heading.allMatches(file.readAsStringSync()).map((match) => _slug(match.group(1)!)).toSet();

/// The anchor of a [heading]: lower case, without punctuation, with a `-` for each space.
String _slug(String heading) => heading.trim().toLowerCase().replaceAll(RegExp(r'[^\w\- ]'), '').replaceAll(' ', '-');
