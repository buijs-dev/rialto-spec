import 'dart:io';

import 'package:rialto_spec_tools/check_spec.dart';
import 'package:rialto_spec_tools/example_links.dart';
import 'package:test/test.dart';

import 'repository_copy.dart';

void main() {
  late Directory repository;

  setUp(() => repository = copyOfTheRepository());

  String read(String path) => File('${repository.path}/$path').readAsStringSync();

  test('the repository is up to date, and a second run changes nothing', () {
    final before = {
      for (final path in ['spec/core.md', 'spec/contract.md']) path: read(path)
    };

    final groups = writeExampleLinks(repository);

    expect(groups, greaterThan(0));
    expect(writeExampleLinks(repository), groups);
    before.forEach((path, text) => expect(read(path), text, reason: path));
  });

  test('writes the lines again after they are removed', () {
    final before = read('spec/core.md');
    edit(repository, 'spec/core.md', '\n\nExamples: none: these requirements apply to the specification itself.', '');
    expect(checkSpec(repository).errors, ['spec/core.md: C7 has no Examples line (run tools/bin/example_links.dart)']);

    writeExampleLinks(repository);

    expect(read('spec/core.md'), before);
    expect(checkSpec(repository).errors, isEmpty);
  });

  test('an invalid test contract is an example of the group its code enforces', () {
    write(
      repository,
      'examples/contracts/invalid/another-unknown-type.yaml',
      '# expect: RIALTO-K004\nrialto: "1.0.0"\n',
    );

    writeExampleLinks(repository);

    expect(
      read('spec/contract.md'),
      contains('[`invalid/another-unknown-type.yaml`](../examples/contracts/invalid/another-unknown-type.yaml)'),
    );
  });

  test('a contract over several files is named by its directory', () {
    writeExampleLinks(repository);

    expect(read('spec/contract.md'), contains('[`valid/fragments/`](../examples/contracts/valid/fragments/)'));
    expect(
      read('spec/contract.md'),
      contains('[`invalid/fragment-duplicate/`](../examples/contracts/invalid/fragment-duplicate/)'),
    );
  });

  test('an invalid test contract without an expected code is no example', () {
    write(repository, 'examples/contracts/invalid/no-code.yaml', 'rialto: "1.0.0"\n');

    writeExampleLinks(repository);

    expect(read('spec/contract.md'), isNot(contains('no-code.yaml')));
    expect(read('spec/core.md'), isNot(contains('no-code.yaml')));
  });

  test('a listed valid test contract that does not exist is no example', () {
    Directory('${repository.path}/examples/contracts/valid/fragments-recursive').deleteSync(recursive: true);

    writeExampleLinks(repository);

    expect(read('spec/contract.md'), isNot(contains('valid/fragments-recursive/')));
    expect(read('spec/contract.md'), contains('valid/fragments/'));
  });

  test('a group without examples waits for the Shipment example while that is not there', () {
    writeExampleLinks(repository);

    expect(
      read('spec/core.md'),
      contains('## C2. Concepts and representations\n\nExamples: $pendingExamples.'),
    );
  });

  test('a group without examples gets no line once the Shipment example is there', () {
    write(repository, 'examples/shipment/README.md', '# Shipment\n');

    writeExampleLinks(repository);

    expect(read('spec/core.md'), contains('## C2. Concepts and representations\n\n'));
    expect(read('spec/core.md'), isNot(contains(pendingExamples)));
    expect(
      checkSpec(repository).errors,
      contains('spec/core.md: C2 has no Examples line (run tools/bin/example_links.dart)'),
    );
  });
}
