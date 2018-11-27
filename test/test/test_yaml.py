# (c) Copyright 2017-2018 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from collections import OrderedDict
import unittest

import python_path
import kube_yaml


class TestBasicYAML(unittest.TestCase):
    def test_basic(self):
        src = OrderedDict(foo=[1, '2', 3])
        src['bar'] = 'baz'
        src['qux'] = {'xyzzy': 10}
        dst = """
foo:
- 1
- '2'
- 3
bar: baz
qux:
  xyzzy: 10
"""
        self.assertEqual(kube_yaml.yaml_safe_dump(src).strip(), dst.strip())

    def test_wrap(self):
        src = OrderedDict(foo='here is some text\nwith some line breaks\nin it')
        src['bar'] = 'and some more text on a single line'
        src['qux'] = 'and yet more with line breaks\nwhich will show through'
        dst = """
foo: |-
  here is some text
  with some line breaks
  in it
bar: and some more text on a single line
qux: |-
  and yet more with line breaks
  which will show through
"""
        self.assertEqual(kube_yaml.yaml_safe_dump(src).strip(), dst.strip())

    def test_quote_all_numbers(self):
        # the go yaml parser appears to interpret numbers with leading zeros as numbers
        # while py_yaml interprets them as strings. We now force this to be quoted in
        # rubiks.
        src = {'foo': '0012345'}
        dst = "foo: '0012345'"
        self.assertEqual(kube_yaml.yaml_safe_dump(src).strip(), dst.strip())
        src = {'foo': '12345'}
        dst = "foo: '12345'"
        self.assertEqual(kube_yaml.yaml_safe_dump(src).strip(), dst.strip())
        src = {'foo': '0012345abc'}
        dst = "foo: 0012345abc"
        self.assertEqual(kube_yaml.yaml_safe_dump(src).strip(), dst.strip())
if __name__ == '__main__':
    unittest.main()
