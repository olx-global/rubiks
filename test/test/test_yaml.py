# (c) Copyright 2017 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from collections import OrderedDict
import unittest

import load_all
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

if __name__ == '__main__':
    unittest.main()
