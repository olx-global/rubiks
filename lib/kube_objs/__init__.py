# (c) Copyright 2017-2018 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os
import sys
from pluggable_loader import KubeObjCollection


def _loader(*extra_dirs):
    # load all the '.py' files in the directory as imports
    this = sys.modules[__name__]

    basedir = os.path.split(os.path.split(this.__file__)[0])[0]

    bases = [basedir]
    bases.extend(extra_dirs)

    coll = KubeObjCollection(bases)
    coll.load_all_python()

    for k in coll.symbols:
        if isinstance(coll.symbols[k], type):
            this.__dict__[k] = coll.symbols[k]
