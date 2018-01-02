# (c) Copyright 2017-2018 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from user_error import UserError
from kube_obj import KubeBaseObj, KubeObj
from kube_objs.namespace import Namespace

_REG = None

class RegistryStackError(Exception):
    pass

class ObjectRegistry(object):
    def __init__(self):
        self.registry = {}
        self.id_registry = {}
        self.classes = {}
        self.context_stack = []

    def add(self, obj):
        cls = obj.__class__
        clsname = self.get_class_name(cls)
        if clsname not in self.registry:
            self.registry[clsname] = {}
        if len(self.context_stack) != 0:
            self.context_stack[-1][1].append(obj)
        self.registry[clsname][id(obj)] = obj

    def new_context(self, identifier):
        self.context_stack.append((identifier, []))

    def close_context(self, identifier=None):
        if len(self.context_stack) == 0:
            raise RegistryStackError("close_context() called without corresponding new_context()")

        if identifier is not None:
            if identifier != self.context_stack[-1][0]:
                raise RegistryStackError("close_context() had different identifier than corresponding new_context()")

        objs = self.context_stack.pop()
        return objs[1]

    def get_class_name(self, cls):
        if cls.__name__ in self.classes:
            if self.classes[cls.__name__][0] is cls:
                return cls.__name__
            else:
                for i in range(1, len(self.classes[cls.__name__])):
                    if self.classes[cls.__name__][i] is cls:
                        return '{}_{}'.format(cls.__name__, i)
                i = len(self.classes[cls.__name__])
                self.classes[cls.__name__].append(cls)
                return '{}_{}'.format(cls.__name__, i)
        else:
            self.classes[cls.__name__] = [cls]
            return cls.__name__

    def get_id(self, cls, identifier):
        if not hasattr(cls, 'identifier'):
            return None

        id_fld = cls.identifier
        clsname = self.get_class_name(cls)

        if clsname not in self.registry:
            return None

        if clsname in self.id_registry and identifier in self.id_registry[clsname]:
            return self.id_registry[clsname][identifier]
        elif clsname not in self.id_registry:
            self.id_registry[clsname] = {}

        ret = []
        self.id_registry[clsname] = {}
        for obj in self.registry[clsname].values():
            if hasattr(obj, id_fld) and getattr(obj, id_fld) is not None:
                curr_id = getattr(obj, id_fld)
                if curr_id not in self.id_registry[clsname]:
                    self.id_registry[clsname][curr_id] = []
                self.id_registry[clsname][curr_id].append(obj)
                if curr_id == identifier:
                    ret.append(obj)

        if len(ret) == 0:
            return None
        return ret

    def get_parents(self, obj):
        ret = []
        for cls in obj._parent_types:
            for robj in self.registry[self.get_class_name(cls)].values():
                if robj.has_child_object(obj):
                    ret.append(robj)
        return ret

_REG = ObjectRegistry()

def add_obj(self):
    return _REG.add(self)

KubeBaseObj.add_obj = add_obj

def get_ns(self, name):
    ret = _REG.get_id(Namespace, name)
    if ret is None:
        return Namespace(name)
    if len(ret) > 1:
        raise UserError(ValueError("More than one namespace with name {} has been declared".format(name)))
    return ret[0]

KubeBaseObj.get_ns = get_ns

def get_parents(self):
    return _REG.get_parents(self)

KubeBaseObj.get_parents = get_parents

def init(is_openshift):
    get_ns(None, 'default')
    get_ns(None, 'kube-system')
    if is_openshift:
        get_ns(None, 'openshift-infra')

def obj_registry():
    return _REG
