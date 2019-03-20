#!/usr/bin/env python3
#
# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from unittest import mock

from ..query import SELECTORS, Query
from ..types import START, TOKEN, BowlerException, Leaf
from .lib import BowlerTestCase


class QueryTest(BowlerTestCase):
    fake_paths = ["foo/bar", "baz.py"]

    def test_basic(self):
        query = Query(self.fake_paths)
        self.assertEqual(len(query.transforms), 0)
        self.assertEqual(query.paths, self.fake_paths)
        with self.assertRaises(ValueError):
            transform = query.current
            self.assertEqual(transform, None)

        query.select_root().is_filename("frob.py")
        self.assertEqual(len(query.transforms), 1)
        self.assertEqual(query.current.selector, "root")
        self.assertEqual(len(query.current.kwargs), 0)
        self.assertEqual(len(query.current.filters), 1)
        self.assertEqual(len(query.current.filters), 1)

        fixers = query.compile()
        self.assertEqual(len(fixers), 1)
        self.assertEqual(fixers[0].PATTERN, SELECTORS["root"].strip())

    def test_rename_func(self):
        def query_func(arg):
            return Query(arg).select_function("f").rename("foo")

        self.run_bowler_modifiers(
            [
                ("def f(x): pass", "def foo(x): pass"),
                ("def g(x): pass", "def g(x): pass"),
                ("f()", "foo()"),
                ("g()", "g()"),
            ],
            query_func=query_func,
        )

    def test_rename_class(self):
        self.run_bowler_modifiers(
            [("class Bar(Foo):\n  pass", "class FooBar(Foo):\n  pass")],
            query_func=lambda x: Query(x).select_class("Bar").rename("FooBar"),
        )

    def test_rename_module(self):
        self.run_bowler_modifiers(
            [("from a.b.c.d import E", "from a.f.d import E")],
            query_func=lambda x: Query(x).select_module("a.b.c").rename("a.f"),
        )

    def test_rename_subclass(self):
        def query_func(x):
            return Query(x).select_subclass("Foo").rename("somepackage.Foo")

        self.run_bowler_modifiers(
            [("class Bar(Foo):\n  pass", "class Bar(somepackage.Foo):\n  pass")],
            query_func=query_func,
        )

    def test_add_argument_positional(self):
        def query_func(x):
            return Query(x).select_function("f").add_argument("y", "5", positional=True)

        self.run_bowler_modifiers(
            [
                ("from b import f", "from b import f"),
                ("def f(x): pass", "def f(x, y): pass"),
                ("def f(x, **kwargs): pass", "def f(x, y, **kwargs): pass"),
                ("def g(x): pass", "def g(x): pass"),
                ("f()", "f(5)"),  # Wrong (type, and position)
                ("g()", "g()"),
            ],
            query_func=query_func,
        )

    def test_add_argument_positional_after(self):
        def f(x, y):
            pass

        def query_func(x):
            return (
                Query(x)
                .select_function(f)
                .add_argument("z", "5", after="x", positional=True)
            )

        self.run_bowler_modifiers(
            [
                ("def f(x, y): pass", "def f(x, z, y): pass"),
                ("def g(x): pass", "def g(x): pass"),
                ("f(1)", "f(1, 5)"),  # Wrong (type)
                ("f(1, 2)", "f(1, 5, 2)"),  # Wrong (type)
                ("f()", "f()"),  # Left unchanged due to arg count check
                ("g()", "g()"),
            ],
            query_func=query_func,
        )

    def test_add_argument_positional_after_start(self):
        def f(cls, x, y):
            pass

        def query_func(x):
            return (
                Query(x)
                .select_function(f)
                .add_argument("z", "5", after=START, positional=True)
            )

        self.run_bowler_modifiers(
            [
                ("def f(cls, x, y): pass", "def f(cls, z, x, y): pass"),
                ("def g(cls, x, y): pass", "def g(cls, x, y): pass"),
                ("def g(cls): pass", "def g(cls): pass"),
                ("f(1)", "f(5, 1)"),  # Wrong (type)
                ("f(1, 2)", "f(5, 1, 2)"),  # Wrong (type)
                ("f()", "f(5)"),  # Wrong (type)
                ("g()", "g()"),
            ],
            query_func=query_func,
        )

    def test_add_argument_positional_after_cls(self):
        def f(cls, x, y):
            pass

        def query_func(x):
            return (
                Query(x)
                .select_function(f)
                .add_argument("z", "5", after="x", positional=True)
            )

        self.run_bowler_modifiers(
            [
                ("def f(cls, x, y): pass", "def f(cls, x, z, y): pass"),
                ("def g(cls, x): pass", "def g(cls, x): pass"),
                ("f(1)", "f(1, 5)"),  # Wrong (type)
                ("f(1, 2)", "f(1, 5, 2)"),  # Wrong (type)
                ("f()", "f()"),  # Left unchanged due to arg count check
                ("g()", "g()"),
            ],
            query_func=query_func,
        )

    def test_add_argument_keyword(self):
        def query_func(x):
            return (
                Query(x).select_function("f").add_argument("y", "5", positional=False)
            )

        self.run_bowler_modifiers(
            [
                ("from b import f", "from b import f"),
                ("def f(x): pass", "def f(x, y=5): pass"),
                ("def g(x): pass", "def g(x): pass"),
                ("f()", "f(y=5)"),
                ("g()", "g()"),
            ],
            query_func=query_func,
        )

    def test_modifier_return_value(self):
        input = "a+b"

        def modifier(node, capture, filename):
            new_op = Leaf(TOKEN.MINUS, "-")
            return new_op

        output = self.run_bowler_modifier(input, "'+'", modifier)
        self.assertEqual("a-b", output)

    def test_modifier_return_value_multiple(self):
        input = "a+b"

        def noop_modifier(node, capture, filename):
            print("Noop modifier")
            pass

        def modifier(node, capture, filename):
            print("Modifier")
            new_op = Leaf(TOKEN.MINUS, "-")
            return new_op

        def add_ok_modifier(q):
            return q.modify(noop_modifier).modify(modifier)

        output = self.run_bowler_modifier(input, "'+'", modifier_func=add_ok_modifier)
        self.assertEqual("a-b", output)

        def add_bad_modifier(q):
            return q.modify(modifier).modify(noop_modifier)

        with mock.patch("bowler.tool.log.error") as error:
            output = self.run_bowler_modifier(
                input, "'+'", modifier_func=add_bad_modifier
            )
            self.assertEqual("a+b", output)  # unmodified
            self.assertTrue(error.call_args)
            self.assertIn(
                "Only the last fixer/callback may return", error.call_args[0][0]
            )
