# (c) Copyright 2017-2018 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os
import sys

import user_error

repobase = os.path.split(os.path.split(os.path.realpath(sys.modules[__name__].__file__))[0])[0]

paths = ('lib', 'vendor/{}/lib'.format(sys.version_info[0]), 'lib/{}'.format(sys.version_info[0]))

for p in paths:
    if os.path.join(repobase, p) not in sys.path:
        sys.path.insert(0, os.path.join(repobase, p))

user_error.paths = tuple(map(lambda x: os.path.join(repobase, x), paths))
