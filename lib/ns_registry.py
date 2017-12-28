# (c) Copyright 2017 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from kube_objs.namespace import Namespace
from kube_obj import KubeBaseObj

_NSREG = None

class NamespaceRegistry(object):
    @classmethod
    def get_ns(cls, name):
        return _NSREG.get_or_create(name)

    def __init__(self):
        self.registry = {}
        self.get_or_create('default')
        self.get_or_create('kube-system')

    def get_or_create(self, name):
        if name not in self.registry:
            self.registry[name] = Namespace(name)
        return self.registry[name]

    def get_all(self):
        return list(self.registry.values())

_NSREG = NamespaceRegistry()

def get_ns(self, name):
    return _NSREG.get_or_create(name)

KubeBaseObj.get_ns = get_ns
