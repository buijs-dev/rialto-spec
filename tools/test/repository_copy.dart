import 'dart:io';

import 'package:test/test.dart';

/// A copy of the specification, the examples and the Markdown of this repository in a temporary directory, for a
/// test to break. The checks pass on it as it is. It is deleted after the test.
Directory copyOfTheRepository() {
  final repository = Directory.current.parent;
  final copy = Directory.systemTemp.createTempSync('rialto-spec-');
  addTearDown(() => copy.deleteSync(recursive: true));

  for (final name in ['spec', 'examples', 'docs']) {
    _copyDirectory(Directory('${repository.path}/$name'), Directory('${copy.path}/$name'));
  }
  for (final name in ['README.md', 'CONTRIBUTING.md', 'GOVERNANCE.md', 'CHANGELOG.md', 'LICENSE', 'NOTICE']) {
    File('${repository.path}/$name').copySync('${copy.path}/$name');
  }
  // CONTRIBUTING.md links to the README of the site.
  Directory('${copy.path}/site').createSync();
  File('${repository.path}/site/README.md').copySync('${copy.path}/site/README.md');
  return copy;
}

void _copyDirectory(Directory from, Directory to) {
  to.createSync(recursive: true);
  for (final entry in from.listSync()) {
    final name = entry.uri.pathSegments.lastWhere((segment) => segment.isNotEmpty);
    if (entry is Directory) _copyDirectory(entry, Directory('${to.path}/$name'));
    if (entry is File) entry.copySync('${to.path}/$name');
  }
}

/// Replaces the first [old] in the file at [path] of [repository] by [replacement]; fails when [old] is not there.
void edit(Directory repository, String path, String old, String replacement) {
  final file = File('${repository.path}/$path');
  final text = file.readAsStringSync();
  expect(text, contains(old), reason: '$path does not have the text to replace');
  file.writeAsStringSync(text.replaceFirst(old, replacement));
}

/// Writes [text] to the file at [path] of [repository], with the directories it needs.
void write(Directory repository, String path, String text) {
  File('${repository.path}/$path')
    ..createSync(recursive: true)
    ..writeAsStringSync(text);
}
