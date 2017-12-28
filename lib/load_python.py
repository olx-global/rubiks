# (c) Copyright 2017 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os
import sys
import weakref

import loader
from kube_yaml import yaml_safe_dump
from load_python_core import do_compile_internal

class PythonFileCollection(loader.Loader):
    def __init__(self, repository):
        loader.Loader.__init__(self, repository)

    def import_python(self, py_context, name, exports):
        path = self.import_check(py_context, name)
        new_context = self.get_or_add_file(pth, PythonFile, (self, path))
        self.import_symbols(name, new_context.path, py_context.path, path.basename,
                            new_context.module, py_context.module, exports)
        self.add_dep(py_context.path, path)

class PythonFile(object):
    def __init__(self, collection, path):
        assert path.basename != '' and '.' not in path.basename

        self.path = path
        self.collection = weakref.ref(collection)

        self.rubiks_objs = []

        self.do_compile()

    def debug(self, *args):
        return self.collection().debug(*args)

    def do_compile(self):
        self.debug(2, 'compiling python: {} ({})'.format(self.path.src_rel_path, self.path.full_path))
        savepath = sys.path
        try:
            newpath = []
            if hasattr(self.collection().repository, 'pythonpath'):
                newpath.extend(self.collection().repository.pythonpath)
            newpath.extend(sys.path)
            sys.path = newpath

            with open(self.path.full_path) as f:
                src = f.read()

            self.module = do_compile_internal(
                src,
                os.path.join(self.collection().repository.sources, self.path.src_rel_path),
                self.path.dot_path(),
                self.path.full_path,
                self.default_ns(),
                )
        except Exception as e:
            if loader.DEV:
                raise
            raise loader.LoaderCompileException('Got exception while loading/compiling {}: {}: {}'.format(
                                                self.path.src_rel_path, e.__class__.__name__, str(e)))
        finally:
            sys.path = savepath

    def get_symnames(self):
        return self.module.__dict__.keys()

    def get_symbol(self, symname):
        return self.module.__dict__[symname]

    def default_ns(self):
        def import_python(name, *exports):
            self.debug(3, '{}: import_python({}, ...)'.format(self.path.src_rel_path, name))
            return self.collection().import_python(self, name, exports)

        def yaml_dump(val):
            print(yaml_safe_dump(val, default_flow_style=False))

        return {
            'import_python': import_python,
            'yaml_dump': yaml_dump,
            'repobase': self.collection().repository.basepath,
            }
