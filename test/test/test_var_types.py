# (c) Copyright 2017-2018 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import unittest

import python_path
import var_types
import kube_yaml


SHOW=False

class Confidential(var_types.VarEntity):
    def init(self, value):
        self.value = value

    def eq(self, other):
        return self.value == other.value

    def to_string(self):
        if SHOW:
            return self.value
        return "*** HIDDEN ***"


class TestBasicVarTypes(unittest.TestCase):
    def setUp(self):
        global SHOW
        SHOW = False

    def tearDown(self):
        global SHOW
        SHOW = False

    def test_basic_confidential_var(self):
        global SHOW
        v = Confidential("foo")
        SHOW = False
        self.assertEqual(str(v), "*** HIDDEN ***")
        SHOW = True
        self.assertEqual(str(v), "foo")
        v = 'abc' + v + 'def'
        SHOW = False
        self.assertEqual(str(v), "abc*** HIDDEN ***def")
        SHOW = True
        self.assertEqual(str(v), "abcfoodef")

    def test_compound_confidential_var(self):
        global SHOW
        x = Confidential("abc")
        y = Confidential("def")
        z = Confidential("ghi")

        a = 'xyz' + z + 'wxy'
        a = a + 'z'
        a = 'w' + a
        SHOW = True
        self.assertEqual(str(a), "wxyzghiwxyz")
        a += y + 'wxyz'
        self.assertEqual(str(a), "wxyzghiwxyzdefwxyz")
        b = 'rst' + a + 'tuv' + y + 'uvw'
        self.assertEqual(str(b), "rstwxyzghiwxyzdefwxyztuvdefuvw")
        SHOW = False
        self.assertEqual(str(b), "rstwxyz*** HIDDEN ***wxyz*** HIDDEN ***wxyztuv*** HIDDEN ***uvw")

    def test_yaml_basic(self):
        global SHOW

        v = {'a': Confidential('foo'), 'b': Confidential('bar'), 'c': 'xyzzy'}
        r = kube_yaml.yaml_safe_dump(v)
        self.assertTrue(isinstance(r, var_types.VarEntity))
        SHOW = True
        self.assertEqual(str(r), "a: foo\nb: bar\nc: xyzzy\n")
        SHOW = False
        self.assertEqual(str(r), "a: '*** HIDDEN ***'\nb: '*** HIDDEN ***'\nc: xyzzy\n")

    def test_yaml_wrapping(self):
        global SHOW

        v = {'a': Confidential('foo\nbar\nbaz'), 'b': Confidential('bar'), 'c': 'xyzzy'}
        r = kube_yaml.yaml_safe_dump(v)
        self.assertTrue(isinstance(r, var_types.VarEntity))
        SHOW = True
        self.assertEqual(str(r), "a: |-\n  foo\n  bar\n  baz\n\nb: bar\nc: xyzzy\n")
        SHOW = False
        self.assertEqual(str(r), "a: '*** HIDDEN ***'\nb: '*** HIDDEN ***'\nc: xyzzy\n")

    def test_yaml_indent(self):
        global SHOW

        v = {'a': {'x': Confidential('foo\nbar\nbaz'), 'y': 'plain'}, 'b': Confidential('bar'), 'c': 'xyzzy'}
        r = kube_yaml.yaml_safe_dump(v)
        self.assertTrue(isinstance(r, var_types.VarEntity))
        SHOW = True
        self.assertEqual(str(r), "a:\n  x: |-\n    foo\n    bar\n    baz\n\n  y: plain\nb: bar\nc: xyzzy\n")
        SHOW = False
        self.assertEqual(str(r), "a:\n  x: '*** HIDDEN ***'\n  y: plain\nb: '*** HIDDEN ***'\nc: xyzzy\n")

    def test_equality(self):
        x = Confidential("abc")
        y = Confidential("def")
        z = Confidential("abc")
        self.assertEqual(x, z)
        self.assertNotEqual(x, y)
        self.assertNotEqual(z, y)

        v0 = 'abc' + x + 'def'
        v1 = 'abc' + z + 'def'
        v2 = 'def' + x + 'abc'

        self.assertEqual(v0, v1)
        self.assertNotEqual(v0, v2)
        self.assertNotEqual(v1, v2)

        v0 = 'abc' + x + 'def' + x + 'ghi'
        v1 = 'abc' + x + 'def' + z + 'ghi'
        v2 = 'abc' + z + 'def' + x + 'ghi'
        v3 = 'abc' + z + 'def' + z + 'ghi'

        self.assertEqual(v0, v1)
        self.assertEqual(v1, v2)
        self.assertEqual(v2, v3)

if __name__ == '__main__':
    unittest.main()
