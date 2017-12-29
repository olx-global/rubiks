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
from kube_obj import KubeObj, KubeBaseObj
from obj_registry import obj_registry
from user_error import UserError
import kube_objs
import kube_vartypes
from util import mkdir_p


class RubiksOutputError(Exception):
    pass


class PythonFileCollection(loader.Loader):
    def __init__(self, repository):
        loader.Loader.__init__(self, repository)
        self.outputs = {}

    def import_python(self, py_context, name, exports):
        path = self.import_check(py_context, name)
        new_context = self.get_or_add_file(pth, PythonFile, (self, path))
        self.import_symbols(name, new_context.path, py_context.path, path.basename,
                            new_context.module, py_context.module, exports)
        self.add_dep(py_context.path, path)

    def add_output(self, kobj):
        if not isinstance(kobj, KubeObj):
            raise TypeError("argument to output should be a KubeObj derivative")

        if isinstance(kobj, kube_objs.Namespace):
            ns = kobj
        else:
            ns = kobj.namespace

        if ns.name not in self.outputs:
            self.outputs[ns.name] = {}

        if ns is not kobj:
            self.add_output(ns)

        identifier = kobj.kubectltype + '-' + getattr(kobj, kobj.identifier)

        if identifier not in self.outputs[ns.name]:
            obj = kobj.do_render()
            if obj is not None:
                self.outputs[ns.name][identifier] = (kobj, yaml_safe_dump(obj, default_flow_style=False))
            else:
                self.outputs[ns.name][identifier] = (kobj, None)
        else:
            if kobj is not self.outputs[ns.name][identifier][0]:
                raise RubiksOutputError("Duplicate objects {}/{} found".format(ns.name, identifier))

    def gen_output(self):
        output_base = os.path.join(self.repository.basepath, self.repository.outputs)

        for ns in self.outputs:
            if any(map(lambda x: x[1] is not None, self.outputs[ns].values())):
                mkdir_p(os.path.join(output_base, ns))
                for ident in self.outputs[ns]:
                    if self.outputs[ns][ident][1] is not None:
                        self.debug(1, 'writing {}.yaml in {}'.format(ident, ns))
                        with open(os.path.join(output_base, ns, '.' + ident + '.tmp'), 'w') as f:
                            f.write(str(self.outputs[ns][ident][1]))
                        os.rename(os.path.join(output_base, ns, '.' + ident + '.tmp'),
                                  os.path.join(output_base, ns, ident + '.yaml'))


class PythonFile(object):
    _kube_objs = None
    _kube_vartypes = None

    def __init__(self, collection, path):
        assert path.basename != '' and '.' not in path.basename

        self.path = path
        self.collection = weakref.ref(collection)

        self.rubiks_objs = []
        self.output_was_called = False

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

            obj_registry().new_context(id(self))
            finished_ok = False
            try:
                self.module = do_compile_internal(
                    src,
                    os.path.join(self.collection().repository.sources, self.path.src_rel_path),
                    self.path.dot_path(),
                    self.path.full_path,
                    self.default_ns(),
                    )
                finished_ok = True
            finally:
                objs = obj_registry().close_context(id(self))
                if finished_ok and not self.output_was_called:
                    for o in objs:
                        if isinstance(o, KubeObj) and o._data[o.identifier] is not None:
                            try:
                                self.collection().add_output(o)
                            except UserError as e:
                                e.f_file = o._caller_file
                                e.f_line = o._caller_line
                                e.f_fn = o._caller_fn
                                raise e
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

    @classmethod
    def get_kube_objs(cls):
        if cls._kube_objs is None:
            cls._kube_objs = {}

            for k in kube_objs.__dict__:
                if isinstance(kube_objs.__dict__[k], type) and k not in ('KubeObj', 'KubeBaseObj', 'KubeSubObj'):
                    try:
                        if isinstance(kube_objs.__dict__[k](), KubeBaseObj):
                            cls._kube_objs[k] = kube_objs.__dict__[k]
                    except:
                        pass

        return cls._kube_objs

    @classmethod
    def get_kube_vartypes(cls):
        if cls._kube_vartypes is None:
            cls._kube_vartypes = {}

            for k in kube_vartypes.__dict__:
                if isinstance(kube_vartypes.__dict__[k], type) and k not in ('VarEntity'):
                    try:
                        if isinstance(kube_vartypes.__dict__[k](_test=True), kube_vartypes.VarEntity):
                            cls._kube_vartypes[k] = kube_vartypes.__dict__[k]
                    except:
                        pass
        return cls._kube_vartypes

    def default_ns(self):
        def import_python(name, *exports):
            self.debug(3, '{}: import_python({}, ...)'.format(self.path.src_rel_path, name))
            return self.collection().import_python(self, name, exports)

        def output(val):
            self.output_was_called = True
            return self.collection().add_output(val)

        def namespace(ns):
            class namespace_wrapper(object):
                def __init__(self, ns):
                    self.ns = ns

                def __enter__(self):
                    self.save_ns = KubeBaseObj._default_ns
                    KubeBaseObj._default_ns = self.ns

                def __exit__(self, etyp, eval, etb):
                    KubeBaseObj._default_ns = self.save_ns
                    return False

            return namespace_wrapper(ns)

        ret = {
            'repobase': self.collection().repository.basepath,

            'import_python': import_python,
            'namespace': namespace,

            'output': output,
            }

        ret.update(self.__class__.get_kube_objs())
        ret.update(self.__class__.get_kube_vartypes())

        return ret
