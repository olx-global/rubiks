# (c) Copyright 2017-2018 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import importlib
import os
import sys


def _loader():
    # load all the '.py' files in the directory as imports
    class Dummy(object):
        pass

    this = sys.modules[Dummy.__module__]
    basedir = os.path.split(this.__file__)[0]
    for dent in sorted(os.listdir(basedir)):
        if not dent.endswith('.py'):
            continue
        if dent == '__init__.py':
            # ourself
            continue
        importlib.import_module('..' + dent[:-3], package='{}.__init__'.format(Dummy.__module__))
