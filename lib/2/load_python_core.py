# (c) Copyright 2017-2018 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import imp

def do_compile_internal(obj, src, path, modname, modpath, nsvars=None, ignorable_exceptions=None):
    compiled = compile(src, path, 'exec')

    mod = imp.new_module(modname)
    mod.__file__ = modpath

    if nsvars is not None:
        mod.__dict__.update(nsvars)

    setattr(obj, '_current_module', mod)
    try:
        exec compiled in mod.__dict__
    except Exception as e:
        if ignorable_exceptions is not None and isinstance(e, ignorable_exceptions):
            pass
        else:
            raise
    delattr(obj, '_current_module')

    return mod
