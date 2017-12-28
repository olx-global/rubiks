# (c) Copyright 2017 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import importlib
import importlib.util
import importlib.machinery

def do_compile_internal(src, path, modname, modpath, nsvars=None):
    compiled = compile(src, path, 'exec')
    mod = importlib.util.module_from_spec(importlib.machinery.ModuleSpec(modname, None, origin=modpath))
    if nsvars is not None:
        mod.__dict__.update(nsvars)
    exec(compiled, mod.__dict__, mod.__dict__)
    return mod
