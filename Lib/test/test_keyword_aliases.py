"""Tests for the aliases of keywords (see keyword.kwaliases)."""

import ast
import codeop
import io
import keyword
import textwrap
import tokenize
import unittest


# Uses every keyword and soft keyword that has an alias.  Soft keywords are
# used only as keywords here, so that translate() doesn't change any name.
SOURCE = """\
import a.b as c
from . import d
from .e import (f as g, h)

type Alias[T] = list[T]

@decorator
class C(Base):
    x: int = None

def func(a, /, b=True, *, c=False, **kw):
    global G
    y = lambda q: q if q else None
    def inner():
        nonlocal y
        del y
    assert a is not b, 'message'
    if a and b or not c:
        return a
    elif a in b and a not in c:
        raise ValueError('x') from None
    else:
        raise
    while True:
        break
    else:
        pass
    for i in range(10):
        continue
    try:
        pass
    except ValueError as e:
        pass
    except TypeError:
        pass
    else:
        pass
    finally:
        pass
    try:
        pass
    except* OSError:
        pass
    with open(a) as f, open(b):
        pass
    yield a
    yield from b
    x = [i for i in b if i is None]
    match a:
        case [1, 2, *rest] if rest:
            pass
        case {'k': v, **kw}:
            pass
        case Point(x=0) | None | True:
            pass
        case _:
            pass

async def coro(a, b):
    async with a as b:
        pass
    async for i in b:
        await i
    return [x async for x in b]
"""


def translate(source):
    """Replace every keyword in *source* by its alias."""
    aliases = {kw: alias for alias, kw in keyword.kwaliases.items()}
    tokens = [tok for tok in tokenize.generate_tokens(io.StringIO(source).readline)
              if tok.type == tokenize.NAME and tok.string in aliases]
    lines = source.splitlines(keepends=True)
    # Replace from the end, so that the positions of the remaining tokens
    # stay valid.
    for tok in reversed(tokens):
        (row, start), (_, end) = tok.start, tok.end
        line = lines[row - 1]
        lines[row - 1] = line[:start] + aliases[tok.string] + line[end:]
    return ''.join(lines)


def names(source):
    return {tok.string
            for tok in tokenize.generate_tokens(io.StringIO(source).readline)
            if tok.type == tokenize.NAME}


def compile_result(source):
    """Return the AST of *source*, or the message of the SyntaxError."""
    try:
        tree = ast.parse(source)
        compile(tree, '<test>', 'exec')
    except SyntaxError as e:
        return e.msg
    return ast.dump(tree)


class KeywordAliasesTest(unittest.TestCase):

    def test_sample_uses_all_aliased_keywords(self):
        self.assertLessEqual(set(keyword.kwaliases.values()), names(SOURCE))
        self.assertFalse(names(translate(SOURCE)) & set(keyword.kwaliases.values()))

    def test_same_ast(self):
        self.assertEqual(ast.dump(ast.parse(translate(SOURCE))),
                         ast.dump(ast.parse(SOURCE)))

    def test_same_errors(self):
        for source in [
            'True = 1',
            'None += 1',
            'del False',
            'x.if',
            'def f(else): pass',
            'import for',
            'f(while=1)',
            'return',
            'break',
            'continue',
            'yield',
            'await x',
            'nonlocal x',
            'x = 1 if y',
            'if x\n    pass',
            'for x in',
            'try:\n    pass\n',
            'with a as b, : pass',
            'x = lambda: yield',
            'class C(x for x in y): pass',
            'def f():\n    x = 1\n    global x',
            'async def f():\n    yield from x',
            'match x:\n    case 1 if:\n        pass',
            'type X = int if',
            'a is not b is not',
            'not in b',
        ]:
            with self.subTest(source=source):
                result = compile_result(source)
                self.assertNotRegex(result, r'^Module\(')  # It is an error.
                self.assertEqual(compile_result(translate(source)), result)

    def test_aliases_of_keywords_are_not_names(self):
        for alias, kw in keyword.kwaliases.items():
            if not keyword.iskeyword(kw):
                continue
            for template in ['{} = 1', 'x.{}', 'def f({}): pass', 'import {}']:
                source = template.format(alias)
                with self.subTest(source=source):
                    with self.assertRaises(SyntaxError):
                        compile(source, '<test>', 'exec')

    def test_aliases_of_soft_keywords_are_names(self):
        namespace = {}
        exec(textwrap.dedent("""
            тип = 1
            сопоставить = тип + 1
            случай = [сопоставить]
            сопоставить сопоставить:
                случай 2 если случай:
                    результат = случай
        """), namespace)
        self.assertEqual(namespace['тип'], 1)
        self.assertEqual(namespace['сопоставить'], 2)
        self.assertEqual(namespace['результат'], [2])

    def test_names_containing_aliases(self):
        for name in ['если1', 'вернуться', 'в_', '_в', 'Если', 'истина', 'ИСТИНА',
                     'иначеесл', 'изи', 'типы']:
            with self.subTest(name=name):
                tree = ast.parse(f'{name} = 1')
                self.assertEqual(tree.body[0].targets[0].id, name)

    def test_constants(self):
        self.assertIs(eval('Истина'), True)
        self.assertIs(eval('Ложь'), False)
        self.assertIs(eval('Ничто'), None)
        self.assertIs(eval('Истина и не Ложь или Ничто'), True)

    def test_mixed_with_english_keywords(self):
        self.assertEqual(eval('[1 если x else 2 для x in range(4) if x != 2]'),
                         [2, 1, 1])

    def test_execution(self):
        namespace = {}
        exec(textwrap.dedent("""
            импорт asyncio

            функция классифицировать(x):
                если x есть Ничто:
                    вернуть 'ничто'
                иначеесли не isinstance(x, int):
                    поднять TypeError('нужно целое')
                иначеесли x < 0 или x в (7, 13):
                    вернуть 'особое'
                иначе:
                    вернуть 'обычное'

            функция генератор(n):
                для i в range(n):
                    если i % 2:
                        продолжить
                    выдать i
                выдать из [100]

            попробовать:
                классифицировать('строка')
            исключение TypeError как ошибка:
                сообщение = str(ошибка)
            наконец:
                итог = 'готово'

            асинхронно функция корутина():
                вернуть ожидать asyncio.sleep(0, 'проснулась')

            результаты = [классифицировать(x) для x в (Ничто, -1, 7, 8)]
            числа = list(генератор(5))
            ответ = asyncio.run(корутина())
        """), namespace)
        self.assertEqual(namespace['результаты'],
                         ['ничто', 'особое', 'особое', 'обычное'])
        self.assertEqual(namespace['числа'], [0, 2, 4, 100])
        self.assertEqual(namespace['сообщение'], 'нужно целое')
        self.assertEqual(namespace['итог'], 'готово')
        self.assertEqual(namespace['ответ'], 'проснулась')

    def test_source_encoding(self):
        source = '# -*- coding: cp1251 -*-\nx = Истина если 1 иначе Ложь\n'
        namespace = {}
        exec(compile(source.encode('cp1251'), '<test>', 'exec'), namespace)
        self.assertIs(namespace['x'], True)

    def test_fstring(self):
        self.assertEqual(eval('f"{1 если Ложь иначе 2}"'), '2')

    def test_incomplete_input(self):
        self.assertIsNone(codeop.compile_command('если x:'))
        self.assertIsNotNone(codeop.compile_command('если x:\n    пропустить\n'))

    def test_unparse(self):
        self.assertEqual(ast.unparse(ast.parse('если x: вернуть Ничто')),
                         'if x:\n    return None')


if __name__ == '__main__':
    unittest.main()
