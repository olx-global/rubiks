# (c) Copyright 2017-2018 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import imp

def do_compile_internal(obj, src, path, modname, modpath, nsvars=None):
    compiled = compile(src, path, 'exec')

    mod = imp.new_module(modname)
    mod.__file__ = modpath

    if nsvars is not None:
        mod.__dict__.update(nsvars)

    setattr(obj, '_current_module', mod)
    exec compiled in mod.__dict__
    delattr(obj, '_current_module')

    nsvar_syms = set()
    for d in mod.__dict__:
        if d in nsvars and mod.__dict__[d] is nsvars[d]:
            nsvar_syms.add(d)
    for d in nsvar_syms:
        del mod.__dict__[d]

    return mod
