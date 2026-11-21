import 'dart:io';

/// The identifier of a requirement, such as `K1.2`; a letter may follow the number (`K1.2a`).
const requirementId = r'[ACKDELMPQRSUV]\d+\.\d+[a-z]?';

/// The documents that hold requirements, by the prefix of their identifiers. The paths are relative to the
/// repository. The specification is built in slices, so not every document exists yet.
const requirementDocuments = {
  'C': 'spec/core.md',
  'K': 'spec/contract.md',
  'D': 'spec/profiles/domain.md',
  'R': 'spec/profiles/rest.md',
  'M': 'spec/profiles/mapping.md',
  'P': 'spec/profiles/persistence.md',
  'U': 'spec/profiles/presentation.md',
  'Q': 'spec/profiles/query.md',
  'E': 'spec/profiles/errors.md',
  'L': 'spec/profiles/lifecycle.md',
  'V': 'spec/profiles/versioning.md',
  'A': 'spec/profiles/events.md',
  'S': 'spec/profiles/auth.md',
};

/// A checkout of the specification: where its documents and test contracts are.
class SpecRepository {
  final Directory root;

  /// The repository at [root]. Links are resolved once, so every path below it compares as text.
  SpecRepository(Directory root) : root = Directory(root.resolveSymbolicLinksSync());

  /// The file at [path], relative to the repository.
  File file(String path) => File('${root.path}/$path');

  /// The path of [entity] relative to the repository, with `/` as separator.
  String relative(FileSystemEntity entity) => entity.path.substring(root.path.length + 1);

  /// The requirement documents that exist, by the prefix of their identifiers.
  Map<String, File> get existingRequirementDocuments =>
      requirementDocuments.map((prefix, path) => MapEntry(prefix, file(path)))
        ..removeWhere((prefix, file) => !file.existsSync());

  /// The prefixes of the requirement documents that do not exist yet: those of a later slice.
  Set<String> get pendingPrefixes =>
      requirementDocuments.keys.where((prefix) => !existingRequirementDocuments.containsKey(prefix)).toSet();

  /// The invalid test contracts, in the order of their paths: each `.yaml` file, and for a contract over several
  /// files the root in its own directory.
  List<File> get invalidTestContracts {
    final contracts = <File>[];
    final directory = Directory('${root.path}/examples/contracts/invalid');
    if (!directory.existsSync()) {
      return contracts;
    }

    for (final entry in directory.listSync()) {
      if (entry is File && entry.path.endsWith('.yaml')) {
        contracts.add(entry);
      }

      if (entry is Directory) {
        final contractRoot = File('${entry.path}/contract.rialto.yaml');
        if (contractRoot.existsSync()) {
          contracts.add(contractRoot);
        }
      }
    }

    contracts.sort((a, b) => a.path.compareTo(b.path));
    return contracts;
  }

  /// Every Markdown file of the repository, in the order of their paths.
  /// Generated and downloaded directories are left out.
  List<File> get markdownFiles {
    final files = <File>[];
    _collectMarkdown(root, files);
    files.sort((a, b) => a.path.compareTo(b.path));
    return files;
  }

  /// Directories that are not part of the specification: version control, the editor, the generated site and
  /// build output.
  static const _skipped = {'.git', '.idea', 'site', 'build', '.gradle', '.dart_tool', 'node_modules'};

  void _collectMarkdown(Directory directory, List<File> files) {
    for (final entry in directory.listSync(followLinks: false)) {
      final name = entry.uri.pathSegments.lastWhere((segment) => segment.isNotEmpty);
      if (entry is Directory && !_skipped.contains(name)) {
        _collectMarkdown(entry, files);
      }

      if (entry is File && name.endsWith('.md')) {
        files.add(entry);
      }
    }
  }
}
