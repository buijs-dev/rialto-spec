import 'dart:io';

import 'package:rialto_spec_tools/check_spec.dart';
import 'package:test/test.dart';

import 'repository_copy.dart';

/// Each check passes on a consistent copy of the repository and fails on a broken one.
void main() {
  late Directory repository;

  setUp(() => repository = copyOfTheRepository());

  List<String> errors() => checkSpec(repository).errors;

  group('the repository as it is', () {
    test('passes every check', () {
      final report = checkSpec(repository);

      expect(report.errors, isEmpty);
      expect(report.requirements, greaterThan(0));
    });

    test('a reference to a requirement of a document of a later slice is accepted', () {
      // The domain profile (prefix D) does not exist yet, so D9.1 may be named; core (prefix C) exists, so
      // C99.1 may not.
      expect(File('${repository.path}/spec/profiles/domain.md').existsSync(), isFalse);
      write(repository, 'docs/later.md', '# Later\n\nSee D9.1 and C99.1.\n');

      expect(errors(), ['docs/later.md: reference to unknown requirement C99.1']);
    });
  });

  group('requirements and key words', () {
    test('an identifier with the prefix of another document, and one that is used twice', () {
      edit(repository, 'spec/core.md', '- **C1.1** ', '- **K1.1** ');

      expect(
        errors(),
        containsAll([
          'spec/core.md: K1.1: identifier does not use prefix C',
          'spec/contract.md: K1.1: duplicate identifier',
        ]),
      );
    });

    test('identifiers count up per group', () {
      edit(repository, 'spec/core.md', '- **C1.2** ', '- **C1.9** ');

      expect(
        errors(),
        contains(startsWith('spec/core.md: C1: expected sequential identifiers [C1.1, C1.2, C1.3')),
      );
    });

    test('a lowercase key word', () {
      edit(repository, 'spec/core.md', 'Cleanup MUST remove', 'Cleanup must remove');

      expect(errors(), ["spec/core.md: C1.5: lowercase key word 'must'"]);
    });

    test('a key word in code is ignored', () {
      edit(repository, 'spec/core.md', 'Cleanup MUST remove', 'Cleanup `must` MUST remove');

      expect(errors(), isEmpty);
    });

    test('a mixed-case key word', () {
      edit(repository, 'spec/core.md', 'Cleanup MUST remove', 'Cleanup MUST not keep');

      expect(errors(), ["spec/core.md: C1.5: mixed-case key word 'MUST not', write it in capitals"]);
    });
  });

  group('diagnostic codes', () {
    test('the table is missing', () {
      edit(repository, 'spec/contract.md', '## Standard diagnostic codes\n', '## Codes\n');

      expect(errors(), contains('spec/contract.md: Standard diagnostic codes table missing'));
    });

    test('a code that is not well formed, and one that is listed twice', () {
      edit(repository, 'spec/contract.md', '| `RIALTO-S005` |', '| `RIALTO-X005` |');
      edit(repository, 'spec/contract.md', '| `RIALTO-S004` |', '| `RIALTO-S003` |');

      expect(
        errors(),
        containsAll([
          "spec/contract.md: invalid diagnostic code 'RIALTO-X005'",
          "spec/contract.md: duplicate diagnostic code 'RIALTO-S003'",
        ]),
      );
    });

    test('an invalid test contract without an expected code', () {
      edit(repository, 'examples/contracts/invalid/unknown-key.yaml', '# expect: RIALTO-K002\n', '');

      expect(errors(), ["examples/contracts/invalid/unknown-key.yaml: missing '# expect: RIALTO-...' on first line"]);
    });

    test('an invalid test contract that expects a code the table does not have', () {
      edit(repository, 'examples/contracts/invalid/unknown-key.yaml', 'RIALTO-K002', 'RIALTO-K999');

      expect(
        errors(),
        ["examples/contracts/invalid/unknown-key.yaml: expects undocumented diagnostic code 'RIALTO-K999'"],
      );
    });

    test('a test contract over several files is checked through its root', () {
      edit(
        repository,
        'examples/contracts/invalid/fragment-duplicate/contract.rialto.yaml',
        '# expect: RIALTO-K005',
        '# expect: RIALTO-K998',
      );

      expect(errors().single, contains("fragment-duplicate/contract.rialto.yaml: expects undocumented"));
    });
  });

  group('references, terminology and links', () {
    test('a reference to a requirement that does not exist; one in code is ignored', () {
      write(repository, 'docs/notes.md', '# Notes\n\nSee C1.99, not `C1.98` in code.\n');

      expect(errors(), ['docs/notes.md: reference to unknown requirement C1.99']);
    });

    test('a bare binding is reported with its line', () {
      write(repository, 'docs/terms.md', 'A binding.\n\nUI bindings.\n');

      expect(errors(), [
        "docs/terms.md: line 1: 'binding' without operation, field or protocol",
        "docs/terms.md: line 3: 'bindings' without operation, field or protocol",
      ]);
    });

    test('a qualified binding, the quoted word and the word in code are accepted', () {
      write(
        repository,
        'docs/terms.md',
        'A field binding, an operation binding, protocol bindings, the word "binding" and `binding` in code.\n',
      );

      expect(errors(), isEmpty);
    });

    test('the name of a specific project in the specification', () {
      write(repository, 'spec/notes.md', '# Notes\n\nLike fabrio and `StrataStaX` did.\n');

      expect(errors(), ["spec/notes.md: mentions 'fabrio'", "spec/notes.md: mentions 'StrataStaX'"]);
    });

    test('the name of a specific project outside the specification is accepted', () {
      write(repository, 'docs/notes.md', '# Notes\n\nFabrio.\n');

      expect(errors(), isEmpty);
    });

    test('links and anchors', () {
      write(
        repository,
        'docs/links.md',
        '# Links\n\n## Here\n\n'
            '[ok](../spec/core.md#c1-generated-and-authored-code) [self](#here) [web](https://example.com/x.md) '
            '[file](../spec/contract-1.0.0.schema.json#anything) [directory](../examples/contracts/valid/fragments/)\n'
            '[gone](missing.md) [bad](../spec/core.md#nowhere) [badself](#there)\n',
      );

      expect(errors(), [
        'docs/links.md: broken link missing.md',
        'docs/links.md: broken anchor ../spec/core.md#nowhere',
        'docs/links.md: broken anchor #there',
      ]);
    });

    test('the generated site and build output are skipped', () {
      write(repository, 'site/page.md', '[gone](missing.md) a binding\n');
      write(repository, 'build/page.md', '[gone](missing.md) a binding\n');

      expect(errors(), isEmpty);
    });

    test('a checkout below a directory named site is still checked', () {
      final moved = Directory('${repository.path}/site/rialto-spec')..createSync(recursive: true);
      for (final name in ['spec', 'examples', 'docs']) {
        Directory('${repository.path}/$name').renameSync('${moved.path}/$name');
      }
      write(moved, 'docs/links.md', '[gone](missing.md)\n');

      expect(checkSpec(moved).errors, contains('docs/links.md: broken link missing.md'));
    });
  });

  group('learning by example', () {
    test('a requirement group without an Examples line', () {
      edit(
        repository,
        'spec/core.md',
        '## C2. Concepts and representations\n\nExamples: ',
        '## C2. Concepts and representations\n\nSee: ',
      );

      expect(errors(), ['spec/core.md: C2 has no Examples line (run tools/bin/example_links.dart)']);
    });
  });
}
