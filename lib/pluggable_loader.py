# (c) Copyright 2018 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os
import sys
import weakref

import loader
from load_python_core import do_compile_internal


class RubiksPluggablePython(object):
    def __init__(self, collection, path):
        if path.basename == '' or path.basename.lower().strip('0123456789abcdefghijklmnopqrstuvwxyz_') != '':
            raise ValueError(
                "Filenames should be python compliant (alphanumeric and '_'), found: {}".format(path.basename))

        if path.extension != 'py':
            raise ValueError("Expected path to end in .py")

        self.path = path
        self.collection = weakref.ref(collection)

        self.module = self.do_compile()

    def debug(self, *args):
        return self.collection().debug(*args)

    def get_symnames(self, *args, **kwargs):
        return self.module.__dict__.keys()

    def get_symbol(self, symname, *args, **kwargs):
        return self.module.__dict__[symname]

    def get_module(self, *args, **kwargs):
        return self.module

    def default_ns(self):
        def import_relative(name, *exports, **kwargs):
            self.debug(3, '{}: import_relative({}, ...)'.format(self.path.base_rel_path, name))
            if len(name) == 0 or name.startswith('.') or '..' in name or \
                    name.lower().strip('0123456789abcdefghijklmnopqrstuvwxyz_') != '':
                raise loader.LoaderImportError('import_relative() uses a python-like import (got {})'.format(name))
            name_path = '/'.join(name.split('.')) + '.py'
            kwargs['__reserved_names'] = ('import_relative', 'import_object')
            return self.collection().import_relative(self, name_path, name, exports, **kwargs)

        def import_objects(*names):
            self.debug(3, '{}: import_objects({})'.format(self.path.base_rel_path, names))
            if len(names) == 0:
                raise ValueError('import_objects() must be called with names')
            return self.collection().import_objects(self, names)

        return {'import_relative': import_relative, 'import_objects': import_objects}

    def do_compile(self):
        self.debug(2, 'compiling kubeobj python: {}'.format(self.path.full_path))

        with open(self.path.full_path) as f:
            src = f.read()

        ctx = self.default_ns()

        mod = do_compile_internal(self, src, self.path.full_path, self.path.dot_path(), self.path.full_path, ctx, ())

        return mod


class RubiksPluggableCollection(loader.Loader):
    subdir = None

    def __init__(self, bases):
        loader.Loader.__init__(self, None)
        self.bases = bases
        self.files = {}
        self.deps = {}
        self.symbols = {}
        self.current_context = []

    def debug(self, level, text):
        if loader.VERBOSE:
            if level in (0, 1):
                print(text, file=sys.stderr)

        if loader.DEBUG:
            indent = ' ' * level
            print('{}-> {}'.format(indent, text), file=sys.stderr)

    def get_file_context(self, path):
        try:
            self.current_context.append(path)
            return self.get_or_add_file(path, RubiksPluggablePython, (self, path))
        finally:
            assert self.current_context[-1] is path
            self.current_context.pop()

    def load_all_python(self):
        for b in self.bases:
            sdir = os.path.join(b, self.subdir)
            if os.path.isdir(sdir):
                for p in os.listdir(sdir):
                    if not p.endswith('.py') or len(p) <= 3 and \
                            p[:-3].strip('0123456789abcdefghijklmnopqrstuvwxyz_') != '':
                        continue
                    path = loader.Path(os.path.join(sdir, p), base=b)
                    ctx = self.get_file_context(path)
                    for symname in ctx.get_symnames():
                        # Note we take last-match here so we can sub-class properly
                        # ordering is left as an exercise to the reader
                        self.symbols[symname] = ctx.get_symbol(symname)

    def import_relative(self, py_context, name_path, name, exports, **kwargs):
        new_context = None

        b = py_context.path.base
        pth = os.path.join(b, self.subdir, name_path)
        if os.path.exists(pth):
            path = loader.Path(pth, base=b)

            basename = name
            if 'import_as' in kwargs and kwargs['import_as'] is not None:
                basename = kwargs['import_as']
            if 'import_as' in kwargs:
                del kwargs['import_as']

            self.add_dep(self.current_context[-1], path)

            new_context = self.get_file_context(path)

            self.import_symbols(name, new_context.path, py_context.path, basename,
                                new_context, py_context._current_module, exports, **kwargs)

            return new_context.get_module()
        return new_context

    def import_objects(self, py_context, names):
        for n in names:
            sn = n
            nn = n
            if isinstance(n, tuple):
                sn = n[0]
                nn = n[1]

            if sn not in self.symbols:
                raise ImportError("Can't find symbol {} in any currently loaded module".format(n))

            py_context._current_module.__dict__[nn] = self.symbols[sn]


class KubeObjCollection(RubiksPluggableCollection):
    subdir = 'kube_objs'
