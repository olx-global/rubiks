# (c) Copyright 2017 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os

def mkdir_p(path, *args):
    parent, cur = os.path.split(path)
    if not os.path.isdir(path):
        mkdir_p(parent, *args)
        os.mkdir(path, *args)
