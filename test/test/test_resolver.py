# (c) Copyright 2017-2018 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os
import unittest

import python_path
import loader
import repository
import lookup
from kube_vartypes import Confidential
from user_error import UserError

Resolver = lookup.Resolver

repo = repository.Repository()
repo.sources = 'test'


class FakeClusterInfo(object):
    def __init__(self, name):
        self.name = name


class TestResolver(unittest.TestCase):
    def get_path(self, path):
        return loader.Path(os.path.join(repo.basepath, 'test/test/data', path), repo)

    def tearDown(self):
        Resolver.current_cluster = None

    def assertRaises(self, exc, fn, *args, **kwargs):
        try:
            fn(*args, **kwargs)
        except exc:
            return True
        except UserError as e:
            if isinstance(e.exc, exc):
                return True
            raise
        except:
            raise
        raise AssertionError("not true")

    def test_basic_yaml(self):
        res = Resolver(self.get_path('normal.yaml'))

        self.assertEqual(res.get_key('foo.bar.baz'), 'qux')
        self.assertEqual(res.get_key('foo.xyzzy'), 1)

        Resolver.current_cluster = FakeClusterInfo('staging')
        self.assertEqual(res.get_key('qux.{cluster}.bar'), 'foo')
        Resolver.current_cluster = FakeClusterInfo('virginia')
        self.assertEqual(res.get_key('qux.{cluster}.bar'), 'xyzzy')

    def test_basic_yaml_fail(self):
        res = Resolver(self.get_path('normal.yaml'))

        self.assertRaises(lookup.KeyIsBranch, res.get_key, 'foo')
        self.assertRaises(lookup.KeyNotExist, res.get_key, 'bar')
        self.assertRaises(lookup.KeyIsBranch, res.get_key, 'foo.bar')
        self.assertRaises(lookup.KeyNotExist, res.get_key, 'foo.baz')
        self.assertRaises(lookup.KeyNotExist, res.get_key, 'foo.bar.baz.qux')

        Resolver.current_cluster = FakeClusterInfo('ireland')
        self.assertRaises(lookup.KeyNotExist, res.get_key, 'qux.{cluster}.bar')

    def test_basic_json(self):
        res = Resolver(self.get_path('normal.json'))

        self.assertEqual(res.get_key('foo.bar.baz'), 'qux')
        self.assertEqual(res.get_key('foo.xyzzy'), 1)

        Resolver.current_cluster = FakeClusterInfo('staging')
        self.assertEqual(res.get_key('qux.{cluster}.bar'), 'foo')
        Resolver.current_cluster = FakeClusterInfo('virginia')
        self.assertEqual(res.get_key('qux.{cluster}.bar'), 'xyzzy')

    def test_basic_json_fail(self):
        res = Resolver(self.get_path('normal.json'))

        self.assertRaises(lookup.KeyIsBranch, res.get_key, 'foo')
        self.assertRaises(lookup.KeyNotExist, res.get_key, 'bar')
        self.assertRaises(lookup.KeyIsBranch, res.get_key, 'foo.bar')
        self.assertRaises(lookup.KeyNotExist, res.get_key, 'foo.baz')
        self.assertRaises(lookup.KeyNotExist, res.get_key, 'foo.bar.baz.qux')

        Resolver.current_cluster = FakeClusterInfo('ireland')
        self.assertRaises(lookup.KeyNotExist, res.get_key, 'qux.{cluster}.bar')

    def test_basic_git_crypted(self):
        res = Resolver(self.get_path('crypted.yaml'))
        self.assertEqual(res.get_key('foo.bar.baz'), '<unknown "foo.bar.baz">')

        self.assertRaises(ValueError, Resolver, self.get_path('crypted.yaml'), git_crypt_ok=False)

    def test_basic_file_not_exists(self):
        res = Resolver(self.get_path('nonexistent.yaml'))
        self.assertEqual(res.get_key('foo.bar.baz'), '<unknown "foo.bar.baz">')

        self.assertRaises(Exception, Resolver, self.get_path('nonexistent.yaml'), non_exist_ok=False)

    def test_basic_fallback(self):
        res = Resolver(self.get_path('normal.yaml'))

        self.assertEqual(res.get_key('foo.bar.baz', 'foo.bar', 'foo'), 'qux')
        self.assertEqual(res.get_key('foo', 'foo.bar', 'foo.bar.baz'), 'qux')

    def test_basic_confidential(self):
        res = Resolver(self.get_path('normal.yaml'), is_confidential=True)
        ret = res.get_key('foo.bar.baz')
        self.assertTrue(isinstance(ret, Confidential))
        self.assertEqual(ret.value, 'qux')
        ret = res.get_key('foo.xyzzy')
        self.assertTrue(isinstance(ret, Confidential))
        self.assertEqual(ret.value, '1')

        res = Resolver(self.get_path('crypted.yaml'), is_confidential=True)
        ret = res.get_key('foo.bar.baz')
        self.assertTrue(isinstance(ret, Confidential))
        self.assertEqual(ret.value, '<unknown "foo.bar.baz">')

    def test_defaults(self):
        res = Resolver(self.get_path('normal.yaml'), default='w00t')
        self.assertEqual(res.get_key('foo.bar.baz', 'foo.bar', 'foo'), 'qux')
        self.assertEqual(res.get_key('foo.bar.baz.qux', 'foo.bar', 'foo'), 'w00t')

        res = Resolver(self.get_path('normal.yaml'), default=30)
        self.assertEqual(res.get_key('woot'), 30)
        self.assertEqual(res.get_key('foo.xyzzy'), 1)
        self.assertEqual(res.get_key('foo.xyzzy.bar'), 30)

        res = Resolver(self.get_path('nonexistent.yaml'), default=30, non_exist_ok=True)
        self.assertEqual(res.get_key('woot'), 30)

    def test_typeassert(self):
        try:
            string_base=(basestring,)
        except NameError:
            string_base=(str,)
        res = Resolver(self.get_path('normal.yaml'), assert_type=string_base)
        self.assertRaises(lookup.KeyIsBranch, res.get_key, 'foo')
        self.assertRaises(lookup.KeyNotExist, res.get_key, 'bar')
        self.assertRaises(TypeError, res.get_key, 'foo.xyzzy')
        self.assertEqual(res.get_key('foo.bar.baz'), 'qux')

        res = Resolver(self.get_path('normal.yaml'), assert_type=int, default='foo')
        self.assertEqual(res.get_key('foo.xyzzy'), 1)
        self.assertRaises(TypeError, res.get_key, 'foo.xyzz')

if __name__ == '__main__':
    unittest.main()
