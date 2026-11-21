import 'dart:io';

import 'package:rialto_spec_tools/check_spec.dart';

/// Checks the documents of the specification: `dart run tools/bin/check_spec.dart [<repository>]`. Without an
/// argument it checks the repository this script is in. The exit code is 0 when every check passes, else 1.
void main(List<String> arguments) {
  final root = arguments.isEmpty ? Directory.fromUri(Platform.script.resolve('../../')) : Directory(arguments.first);
  final report = checkSpec(root);
  if (report.errors.isEmpty) {
    stdout.writeln('OK: ${report.requirements} requirements, all checks passed.');
    return;
  }

  report.errors.forEach(stdout.writeln);
  stdout.writeln('\n${report.errors.length} error(s); ${report.requirements} requirements.');
  exitCode = 1;
}
