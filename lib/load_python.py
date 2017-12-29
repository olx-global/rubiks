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
    _python_file_types = None

    @classmethod
    def get_python_file_type(cls, extension):
        def _rec_subclasses(kls):
            ret = {}
            for c in kls.__subclasses__():
                ret.update(_rec_subclasses(c))
            if hasattr(kls, 'extensions'):
                for e in kls.extensions:
                    ret[e] = kls
            return ret

        if cls._python_file_types is None:
            cls._python_file_types = _rec_subclasses(PythonBaseFile)

        try:
            return cls._python_file_types[extension]
        except KeyError:
            return None

    def __init__(self, repository):
        loader.Loader.__init__(self, repository)
        self.clustered_outputs = {}
        self.clusterless_outputs = {}

    def load_python(self, path):
        pth = loader.Path(os.path.join(self.repository.basepath, path), self.repository)

        python_loader = self.__class__.get_python_file_type(pth.extension)
        if python_loader is None:
            raise UserError(loader.LoaderFileNameError(
                "No valid handler for extension {} in {}".format(pth.extension, path)))

        self.get_or_add_file(pth, python_loader, (self, pth))

    def import_python(self, py_context, name, exports, **kwargs):
        path = self.import_check(py_context, name)

        basename = path.basename
        if 'import_as' in kwargs and kwargs['import_as'] is not None:
            basename = kwargs['import_as']

        if 'import_as' in kwargs:
            del kwargs['import_as']

        python_loader = self.__class__.get_python_file_type(path.extension)
        if python_loader is None:
            raise UserError(loader.LoaderFileNameError(
                "No valid handler for extension {} in {}".format(path.extension, path)))

        new_context = self.get_or_add_file(path, python_loader, (self, path))

        self.import_symbols(name, new_context.path, py_context.path, basename,
                            new_context, py_context._current_module, exports, **kwargs)

        self.add_dep(py_context.path, path)

    def add_output(self, kobj):
        if not isinstance(kobj, KubeObj):
            raise TypeError("argument to output should be a KubeObj derivative")

        if isinstance(kobj, kube_objs.Namespace):
            ns = kobj
        else:
            ns = kobj.namespace

        cluster = kobj._in_cluster
        if kobj._in_cluster is not None:
            cluster = cluster.name
            if cluster not in self.clustered_outputs:
                self.clustered_outputs[cluster] = {}

        if cluster is None:
            if ns.name not in self.clusterless_outputs:
                self.clusterless_outputs[ns.name] = {}
            outputs = self.clusterless_outputs[ns.name]
        else:
            if ns.name not in self.clustered_outputs[cluster]:
                self.clustered_outputs[cluster][ns.name] = {}
            outputs = self.clustered_outputs[cluster][ns.name]

        if ns is not kobj:
            self.add_output(ns)

        identifier = kobj.kubectltype + '-' + getattr(kobj, kobj.identifier)

        if identifier not in outputs:
            obj = kobj.do_render()
            if obj is not None:
                outputs[identifier] = (kobj, yaml_safe_dump(obj, default_flow_style=False))
            else:
                outputs[identifier] = (kobj, None)
        else:
            if kobj is not outputs[identifier][0]:
                if cluster is None:
                    c_text = '<all_clusters>'
                else:
                    c_text = 'cluster: {}'.format(cluster)
                raise RubiksOutputError("Duplicate objects {}: {}/{} found".format(c_text, ns.name, identifier))

    def gen_output(self):
        output_base = os.path.join(self.repository.basepath, self.repository.outputs)

        def write_file(pth, ident, content):
            self.debug(1, 'writing {}.yaml in {}'.format(ident, pth))
            with open(os.path.join(output_base, pth, '.' + ident + '.tmp'), 'w') as f:
                f.write(str(content))
            os.rename(os.path.join(output_base, pth, '.' + ident + '.tmp'),
                      os.path.join(output_base, pth, ident + '.yaml'))

        for c in self.repository.get_clusters():
            for ns in self.clusterless_outputs:
                if any(map(lambda x: x[1] is not None, self.clusterless_outputs[ns].values())):
                    mkdir_p(os.path.join(output_base, c))
                    for ident in self.clusterless_outputs[ns]:
                        if self.clusterless_outputs[ns][ident][0]._uses_namespace:
                            mkdir_p(os.path.join(output_base, c, ns))
                            if self.clusterless_outputs[ns][ident][1] is not None:
                                write_file(os.path.join(c, ns), ident, self.clusterless_outputs[ns][ident][1])
                        else:
                            if self.clusterless_outputs[ns][ident][1] is not None:
                                write_file(c, ident, self.clusterless_outputs[ns][ident][1])
            if not c in self.clustered_outputs:
                continue
            for ns in self.clustered_outputs[c]:
                if any(map(lambda x: x[1] is not None, self.clustered_outputs[c][ns].values())):
                    mkdir_p(os.path.join(output_base, c))
                    for ident in self.clustered_outputs[c][ns]:
                        if self.clustered_outputs[c][ns][ident][0]._uses_namespace:
                            mkdir_p(os.path.join(output_base, c, ns))
                            if self.clustered_outputs[c][ns][ident][1] is not None:
                                write_file(os.path.join(c, ns), ident, self.clustered_outputs[c][ns][ident][1])
                        else:
                            if self.clustered_outputs[c][ns][ident][1] is not None:
                                write_file(c, ident, self.clustered_outputs[c][ns][ident][1])


class PythonBaseFile(object):
    _kube_objs = None
    _kube_vartypes = None
    compile_in_init = True
    default_export_objects = False
    can_cluster_context = True

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
                        if isinstance(kube_vartypes.__dict__[k](_test=True), kube_vartypes.var_types.VarEntity):
                            cls._kube_vartypes[k] = kube_vartypes.__dict__[k]
                    except:
                        pass
        return cls._kube_vartypes

    def __init__(self, collection, path):
        if path.basename == '' or path.basename.lower().strip('0123456789abcdefghijklmnopqrstuvwxyz_') != '':
            raise UserError(ValueError(
                "Filenames should be python compliant (alphanumeric and '_'), found: {}".format(path.basename)))

        if hasattr(self, 'extensions') and len(self.extensions) != 0:
            assert path.extension in self.extensions

        self.path = path
        self.collection = weakref.ref(collection)

        self.output_was_called = False
        self.default_import_args = {}

        if self.compile_in_init:
            self.module = self.do_compile()

    def debug(self, *args):
        return self.collection().debug(*args)

    def get_module(self, **kwargs):
        return self.module

    def get_symnames(self, **kwargs):
        return self.module.__dict__.keys()

    def get_symbol(self, symname, **kwargs):
        return self.module.__dict__[symname]

    def default_ns(self):
        def import_python(name, *exports, **kwargs):
            self.debug(3, '{}: import_python({}, ...)'.format(self.path.src_rel_path, name))
            nargs = {}
            nargs.update(self.default_import_args)
            nargs.update(kwargs)
            nargs['__reserved_names'] = self.reserved_names
            return self.collection().import_python(self, name, exports, **nargs)

        def output(val):
            self.output_was_called = True
            return self.collection().add_output(val)

        def cluster_context(clstr):
            class cluster_wrapper(object):
                def __init__(self, clstr):
                    self.cluster = clstr

                def __enter__(self):
                    self.save_cluster = KubeBaseObj._default_cluster
                    KubeBaseObj._default_cluster = self.cluster

                def __exit__(self, etyp, eval, etb):
                    KubeBaseObj._default_cluster = self.save_cluster
                    return False

            return cluster_wrapper(self.collection().repository.get_cluster_info(clstr))

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

        clusters = tuple(self.collection().repository.get_clusters())

        def cluster_info(c):
            assert c in clusters
            return self.collection().repository.get_cluster_info(c)

        ret = {
            'repobase': self.collection().repository.basepath,

            'import_python': import_python,
            'namespace': namespace,

            'clusters': clusters,
            'cluster_info': cluster_info,

            'output': output,
            }

        if self.can_cluster_context:
            ret['cluster_context'] = cluster_context

        ret.update(self.__class__.get_kube_objs())
        ret.update(self.__class__.get_kube_vartypes())

        self.reserved_names = tuple(ret.keys())

        return ret

    def do_compile(self, extra_context=None):
        self.debug(2, 'compiling python: {} ({})'.format(self.path.src_rel_path, self.path.full_path))
        mod = None
        savepath = sys.path
        try:
            newpath = []
            if hasattr(self.collection().repository, 'pythonpath'):
                newpath.extend(self.collection().repository.pythonpath)
            newpath.extend(sys.path)
            sys.path = newpath
            self.debug(3, 'sys.path = {}'.format(':'.join(sys.path)))

            with open(self.path.full_path) as f:
                src = f.read()

            ctx = self.default_ns()
            if extra_context is not None:
                ctx.update(extra_context)

            obj_registry().new_context(id(self))
            finished_ok = False
            try:
                mod = do_compile_internal(
                    self, src,
                    os.path.join(self.collection().repository.sources, self.path.src_rel_path),
                    self.path.dot_path(), self.path.full_path, ctx)
                finished_ok = True
            finally:
                objs = obj_registry().close_context(id(self))
                if finished_ok and not self.output_was_called and self.default_export_objects:
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

        return mod

class PythonImportFile(PythonBaseFile):
    extensions = ('kube',)

class PythonRunOnceFile(PythonBaseFile):
    default_export_objects = True
    extensions = ('gkube',)

class PythonRunPerClusterFile(PythonBaseFile):
    compile_in_init = False
    default_export_objects = True
    extensions = ('ekube',)
    can_cluster_context = False

    def __init__(self, *args, **kwargs):
        PythonBaseFile.__init__(self, *args, **kwargs)
        self.module = {}
        for c in self.collection().repository.get_clusters():
            this_cluster = self.collection().repository.get_cluster_info(c)
            try:
                KubeBaseObj._default_cluster = this_cluster
                self.default_import_args = {'cluster': c}
                self.module[c] = self.do_compile({'current_cluster': this_cluster, 'current_cluster_name': c})
            finally:
                self.default_import_args = {}
                KubeBaseObj._default_cluster = None

    def get_module(self, **kwargs):
        if not 'cluster' in kwargs:
            raise loader.LoaderImportError("must specify 'cluster' param when importing .ekube files")
        return self.module[kwargs['cluster']]

    def get_symnames(self, **kwargs):
        if not 'cluster' in kwargs:
            raise loader.LoaderImportError("must specify 'cluster' param when importing .ekube files")
        return self.module[kwargs['cluster']].__dict__.keys()

    def get_symbol(self, symname, **kwargs):
        if not 'cluster' in kwargs:
            raise loader.LoaderImportError("must specify 'cluster' param when importing .ekube files")
        return self.module[kwargs['cluster']].__dict__[symname]
