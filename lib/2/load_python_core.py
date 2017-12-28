# (c) Copyright 2017 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import imp

def do_compile_internal(src, path, modname, modpath, nsvars=None):
    compiled = compile(src, path, 'exec')
    mod = imp.new_module(modname)
    mod.__file__ = modpath
    if nsvars is not None:
        mod.__dict__.update(nsvars)
    exec compiled in mod.__dict__
    return mod
