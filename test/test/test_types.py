# (c) Copyright 2017-2018 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from collections import OrderedDict
import unittest

import python_path
import user_error
from kube_types import *
import kube_loader


class TestBasicTypes(unittest.TestCase):
    def assertUserRaises(self, exc, fn, *args, **kwargs):
        try:
            fn(*args, **kwargs)
            self.assertTrue(False, "Didn't throw exception")
        except AssertionError:
            raise
        except Exception as e:
            if isinstance(e, user_error.UserError):
                e = e.exc
            self.assertTrue(isinstance(e, exc), "Exception was wrong type {} isn't {}".
                            format(e.__class__.__name__, exc.__name__))

    def test_basic_types(self):
        self.assertUserRaises(KubeTypeValidationError, Boolean().check, None)
        self.assertUserRaises(KubeTypeValidationError, Boolean().check, 5)
        self.assertUserRaises(KubeTypeValidationError, Boolean().check, 5.5)
        self.assertUserRaises(KubeTypeValidationError, Boolean().check, "string")
        self.assertUserRaises(KubeTypeValidationError, Boolean().check, [])
        self.assertUserRaises(KubeTypeValidationError, Boolean().check, {})
        Boolean().check(True)
        Boolean().check(False)

        self.assertUserRaises(KubeTypeValidationError, Integer().check, None)
        self.assertUserRaises(KubeTypeValidationError, Integer().check, True)
        self.assertUserRaises(KubeTypeValidationError, Integer().check, 5.5)
        self.assertUserRaises(KubeTypeValidationError, Integer().check, "string")
        self.assertUserRaises(KubeTypeValidationError, Integer().check, [])
        self.assertUserRaises(KubeTypeValidationError, Integer().check, {})
        Integer().check(549)
        Integer().check(1234567891234567)

        self.assertUserRaises(KubeTypeValidationError, Number().check, None)
        self.assertUserRaises(KubeTypeValidationError, Number().check, True)
        self.assertUserRaises(KubeTypeValidationError, Number().check, "string")
        self.assertUserRaises(KubeTypeValidationError, Number().check, [])
        self.assertUserRaises(KubeTypeValidationError, Number().check, {})
        Number().check(549)
        Number().check(1234567891234567)
        Number().check(12.34567891234567)

        self.assertUserRaises(KubeTypeValidationError, String().check, None)
        self.assertUserRaises(KubeTypeValidationError, String().check, True)
        self.assertUserRaises(KubeTypeValidationError, String().check, 5)
        self.assertUserRaises(KubeTypeValidationError, String().check, 5.5)
        self.assertUserRaises(KubeTypeValidationError, String().check, [])
        self.assertUserRaises(KubeTypeValidationError, String().check, {})
        String().check("")
        String().check("foo")

        self.assertUserRaises(KubeTypeValidationError, Enum('a', 'b').check, None)
        self.assertUserRaises(KubeTypeValidationError, Enum('a', 'b').check, True)
        self.assertUserRaises(KubeTypeValidationError, Enum('a', 'b').check, 5)
        self.assertUserRaises(KubeTypeValidationError, Enum('a', 'b').check, [])
        self.assertUserRaises(KubeTypeValidationError, Enum('a', 'b').check, {})
        self.assertUserRaises(KubeTypeValidationError, Enum('a', 'b').check, 'afoo')
        self.assertUserRaises(KubeTypeValidationError, Enum('a', 'b').check, 'bfoo')
        Enum('a', 'b').check('a')
        Enum('a', 'b').check('b')

    def test_compound_types(self):
        self.assertUserRaises(KubeTypeValidationError, List(String).check, None)
        self.assertUserRaises(KubeTypeValidationError, List(String).check, "foo")
        self.assertUserRaises(KubeTypeValidationError, List(String).check, {})
        self.assertUserRaises(KubeTypeValidationError, List(String).check, ["a", None])
        self.assertUserRaises(KubeTypeValidationError, List(String).check, [1, 2, 3])
        List(String).check([])
        List(String).check(["abc"])
        List(String).check(["abc", "xyz"])

        self.assertUserRaises(KubeTypeValidationError, Map(Integer, String).check, None)
        self.assertUserRaises(KubeTypeValidationError, Map(Integer, String).check, True)
        self.assertUserRaises(KubeTypeValidationError, Map(Integer, String).check, ["a", None])
        self.assertUserRaises(KubeTypeValidationError, Map(Integer, String).check, [1, 2, 3])
        self.assertUserRaises(KubeTypeValidationError, Map(Integer, String).check, {'a': 'b', 'c': 'd'})
        self.assertUserRaises(KubeTypeValidationError, Map(Integer, String).check, {'a': 'b', 1: 'd'})
        self.assertUserRaises(KubeTypeValidationError, Map(Integer, String).check, {2: None, 1: 'd'})
        Map(Integer, String).check({})
        Map(Integer, String).check({1: 'abc', 3: 'def'})

    def test_modifiers(self):
        self.assertUserRaises(KubeTypeValidationError, Nullable(String).check, True)
        self.assertUserRaises(KubeTypeValidationError, Nullable(String).check, 5)
        self.assertUserRaises(KubeTypeValidationError, Nullable(String).check, 5.5)
        self.assertUserRaises(KubeTypeValidationError, Nullable(String).check, [])
        self.assertUserRaises(KubeTypeValidationError, Nullable(String).check, {})
        Nullable(String).check(None)
        Nullable(String).check("")
        Nullable(String).check("foo")

        self.assertUserRaises(KubeTypeValidationError, NonEmpty(String).check, None)
        self.assertUserRaises(KubeTypeValidationError, NonEmpty(String).check, True)
        self.assertUserRaises(KubeTypeValidationError, NonEmpty(String).check, 5)
        self.assertUserRaises(KubeTypeValidationError, NonEmpty(String).check, 5.5)
        self.assertUserRaises(KubeTypeValidationError, NonEmpty(String).check, '')
        self.assertUserRaises(KubeTypeValidationError, NonEmpty(String).check, [])
        self.assertUserRaises(KubeTypeValidationError, NonEmpty(String).check, ['a', 'b'])
        self.assertUserRaises(KubeTypeValidationError, NonEmpty(String).check, {})
        self.assertUserRaises(KubeTypeValidationError, NonEmpty(String).check, {'a': 'b'})
        NonEmpty(String).check("foo")

        self.assertUserRaises(KubeTypeValidationError, Positive(Integer).check, None)
        self.assertUserRaises(KubeTypeValidationError, Positive(Integer).check, -1)
        self.assertUserRaises(KubeTypeValidationError, Positive(Integer).check, -5.5)
        self.assertUserRaises(KubeTypeValidationError, Positive(Integer).check, 5.5)
        Positive(Integer).check(0)
        Positive(Integer).check(5)

        self.assertUserRaises(KubeTypeValidationError, Positive(Number).check, None)
        self.assertUserRaises(KubeTypeValidationError, Positive(Number).check, -1)
        self.assertUserRaises(KubeTypeValidationError, Positive(Number).check, -5.5)
        Positive(Number).check(0)
        Positive(Number).check(0.)
        Positive(Number).check(5)
        Positive(Number).check(5.5)

        self.assertUserRaises(KubeTypeValidationError, NonZero(Integer).check, None)
        self.assertUserRaises(KubeTypeValidationError, NonZero(Integer).check, 0)
        NonZero(Integer).check(-1)
        NonZero(Integer).check(1)

    def test_string_derives(self):
        self.assertUserRaises(KubeTypeValidationError, Identifier().check, None)
        self.assertUserRaises(KubeTypeValidationError, Identifier().check, 0)
        self.assertUserRaises(KubeTypeValidationError, Identifier().check, '')
        self.assertUserRaises(KubeTypeValidationError, Identifier().check, 'a' * 254)
        self.assertUserRaises(KubeTypeValidationError, Identifier().check, 'abc_def')
        self.assertUserRaises(KubeTypeValidationError, Identifier().check, 'arn:aws:12345::::')
        self.assertUserRaises(KubeTypeValidationError, Identifier().check, 'ABCDEF')
        Identifier().check('my-foo-bar')
        Identifier().check('my-foo-bar0')
        Identifier().check('my-foo-bar0.1')

        self.assertUserRaises(KubeTypeValidationError, ARN().check, None)
        self.assertUserRaises(KubeTypeValidationError, ARN().check, 0)
        self.assertUserRaises(KubeTypeValidationError, ARN().check, 'foo:bar:12345')
        self.assertUserRaises(KubeTypeValidationError, ARN().check, 'arn:aws')
        self.assertUserRaises(KubeTypeValidationError, ARN().check, 'arn:aws1')
        ARN().check('arn:aws:iam:12345:....')
        ARN().check('arn:aws-beijing:iam:12345:....')

        self.assertUserRaises(KubeTypeValidationError, Path().check, None)
        self.assertUserRaises(KubeTypeValidationError, Path().check, 0)
        self.assertUserRaises(KubeTypeValidationError, Path().check, 'foo:bar:12345')
        self.assertUserRaises(KubeTypeValidationError, Path().check, '::foo:bar:12345')
        self.assertUserRaises(KubeTypeValidationError, Path().check, 'foo/bar/12345')
        Path().check('')
        Path().check('/a/b/c')
        Path().check('/a')

    def assertNameFormatter(self, cls):
        # Markdown link renderer
        md_render = lambda x: '[{}](#{})'.format(x, x.lower())
        # Default formatter
        null_render = lambda x: x

        # Assertion using the formatter
        self.assertEqual(cls().name(), cls.__name__)
        self.assertEqual(cls().name(render=null_render), cls.__name__)
        self.assertEqual(cls().name(render=md_render), '[{}](#{})'.format(cls().name(), cls().name().lower()))
    
    def test_name_render(self):
        # Markdown link renderer
        render=lambda x: '[{}](#{})'.format(x, x.lower())

        self.assertNameFormatter(Boolean)
        self.assertNameFormatter(ARN,)
        self.assertNameFormatter(Domain)
        self.assertNameFormatter(String)
        self.assertNameFormatter(Number)
        self.assertNameFormatter(Integer)
        self.assertNameFormatter(IPv4)
        self.assertNameFormatter(SurgeSpec)
        self.assertNameFormatter(IP)
        self.assertNameFormatter(Identifier)
        self.assertNameFormatter(CaseIdentifier)
        self.assertNameFormatter(SystemIdentifier)
        self.assertNameFormatter(ColonIdentifier)
        self.assertNameFormatter(Path)

        self.assertEqual(List(String).name(render=render), '[List](#list)<[String](#string)>')

        self.assertEqual(Map(Number, String).name(render=render), '[Map](#map)<{}, {}>'.format(
            Number().name(render=render), 
            String().name(render=render)
            ))

        self.assertEqual(Map(String, List([])).name(render=render), '[Map](#map)<{}, {}>'.format(
            String().name(render=render), 
            List([]).name(render=render)
            ))


if __name__ == '__main__':
    unittest.main()
