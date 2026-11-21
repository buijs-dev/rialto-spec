import 'dart:io';

import 'package:rialto_spec_tools/example_links.dart';

/// Writes the `Examples:` line under every requirement group: `dart run tools/bin/example_links.dart
/// [<repository>]`. Without an argument it writes in the repository this script is in.
void main(List<String> arguments) {
  final root = arguments.isEmpty ? Directory.fromUri(Platform.script.resolve('../../')) : Directory(arguments.first);
  stdout.writeln('groups with examples: ${writeExampleLinks(root)}');
}
