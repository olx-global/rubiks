# (c) Copyright 2017 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os
import weakref

import kube_objs
from kube_obj import KubeObj
from kube_yaml import yaml_safe_dump
from util import mkdir_p

class RubiksOutputError(Exception):
    pass

class OutputCollection(object):
    def __init__(self, loader, repository):
        self.repository = repository
        self.clusterless = {}
        self.clustered = {}
        self.cluster_mode = (len(self.repository.get_clusters()) != 0)
        self.loader = weakref.ref(loader)

    def debug(self, *args, **kwargs):
        self.loader().debug(*args, **kwargs)

    def add_output(self, kobj):
        if not isinstance(kobj, KubeObj):
            raise TypeError("argument to output should be a KubeObj derivative")

        cluster = None
        if self.cluster_mode:
            if kobj._in_cluster is not None:
                cluster = kobj._in_cluster.name

        op = OutputMember(self, kobj, cluster)
        if not op.is_namespace:
            self.add_output(op.kobj.namespace)

        if cluster is not None and cluster not in self.clustered:
            self.clustered[cluster] = {}

        if cluster is None:
            outputs = self.clusterless
        else:
            outputs = self.clustered[cluster]

        if op.namespace_name not in outputs:
            outputs[op.namespace_name] = {}
        outputs = outputs[op.namespace_name]

        self.check_for_dupes(op)

        if op.identifier not in outputs:
            outputs[op.identifier] = op

        outputs[op.identifier].render()

    def write_output(self):
        self.base = os.path.join(self.repository.basepath, self.repository.outputs)
        self.debug(2, "writing output to {}".format(self.base))
        if self.cluster_mode:
            self._write_output_clustered()
        else:
            self._write_output_clusterless()

    def _write_output_clustered(self):
        for c in self.repository.get_clusters():
            path = os.path.join(self.base, c)
            mkdir_p(path)

            ns_done = set()
            for ns in self.clusterless:
                ns_done.add(ns)
                outputs = []
                outputs.extend(self.clusterless[ns].values())
                if c in self.clustered and ns in self.clustered[c]:
                    outputs.extend(self.clustered[c][ns].values())

                if any(map(lambda x: x.has_data() and not x.is_namespace, outputs)):
                    for op in outputs:
                        op.write_file(path)

            if not c in self.clustered:
                continue

            for ns in self.clustered[c]:
                if ns in ns_done:
                    continue

                if any(map(lambda x: x.has_data() and not x.is_namespace, self.clustered[c][ns].values())):
                    for op in self.clustered[c][ns].values():
                        op.write_file(path)

    def _write_output_clusterless(self):
        mkdir_p(self.base)
        for ns in self.clusterless:
            if any(map(lambda x: x.has_data() and not x.is_namespace, self.clusterless[ns].values())):
                for op in self.clusterless[ns].values():
                    op.write_file(self.base)

    def check_for_dupes(self, op):
        ret = self._check_for_dupes(op)
        if ret is None:
            return

        new_obj = op.namespace_name + '/' + op.identifier
        orig_obj = new_obj
        if op.cluster is None:
            new_obj = "<all clusters>:" + new_obj
        else:
            new_obj = op.cluster + ":" + new_obj

        if ret[0] is None:
            orig_obj = "<all clusters>:" + orig_obj
        else:
            orig_obj = ret[0] + ":" + orig_obj

        raise RubiksOutputError("Duplicate (different) objects found: (orig) {}, (added) {}".format(orig_obj, new_obj))

    def _check_for_dupes(self, op):
        if op.cluster is None:
            nobj = None
            try:
                nobj = self.clusterless[op.namespace_name][op.identifier]
            except KeyError:
                pass
            if nobj is not None and not op.is_compatible(nobj):
                return (None,)

            for c in self.clustered:
                nobj = None
                try:
                    nobj = self.clustered[c][op.namespace_name][op.identifier]
                except KeyError:
                    pass
                if nobj is not None and not op.is_compatible(nobj):
                    return (c,)
        else:
            nobj = None
            try:
                nobj = self.clustered[op.cluster][op.namespace_name][op.identifier]
            except KeyError:
                pass
            if nobj is not None and not op.is_compatible(nobj):
                return (op.cluster,)

            nobj = None
            try:
                nobj = self.clusterless[op.namespace_name][op.identifier]
            except KeyError:
                pass
            if nobj is not None and not op.is_compatible(nobj):
                return (None,)

        return None

class OutputMember(object):
    def __init__(self, coll, kobj, cluster):
        self.kobj = kobj
        self.cluster = cluster
        self.coll = weakref.ref(coll)

        self.is_namespace = isinstance(kobj, kube_objs.Namespace)
        self.is_confidential = False

        if self.is_namespace:
            self.namespace = kobj
        else:
            self.namespace = kobj.namespace

        self.namespace_name = self.namespace.name
        self.uses_namespace = kobj._uses_namespace

        self.identifier = str(kobj.kubectltype + '-' + getattr(kobj, kobj.identifier))

    def debug(self, *args, **kwargs):
        return self.coll().debug(*args, **kwargs)

    def is_compatible(self, obj):
        return obj.__class__ is self.__class__ and obj.kobj is self.kobj

    def render(self):
        self.cached_obj = self.kobj.do_render()

    def has_data(self):
        if not hasattr(self, 'cached_obj'):
            self.render()
        return self.cached_obj is not None

    def yaml(self):
        self.cached_yaml = yaml_safe_dump(self.cached_obj, default_flow_style=False)

    def write_file(self, path):
        if not hasattr(self, 'cached_obj'):
            self.render()

        if self.cached_obj is None:
            return

        if not hasattr(self, 'cached_yaml'):
            self.yaml()

        if self.uses_namespace:
            path = os.path.join(path, self.namespace_name)
            mkdir_p(path)

        self.filedir = path
        self.filename = self.identifier + '.yaml'

        self.debug(3, "writing file {}/{}".format(self.filedir, self.filename))

        with open(os.path.join(path, '.' + self.identifier + '.tmp'), 'w') as f:
            f.write(str(self.cached_yaml))
        os.rename(os.path.join(path, '.' + self.identifier + '.tmp'),
                  os.path.join(path, self.filename))
