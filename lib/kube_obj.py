# (c) Copyright 2017 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from collections import OrderedDict
from kube_types import *
import copy


def order_dict(src, order):
    ret = OrderedDict()
    for k in order:
        if k in src:
            ret[k] = src[k]
    if isinstance(src, OrderedDict):
        keys = src.keys()
    else:
        keys = sorted(src.keys())
    for k in keys:
        if k not in order:
            ret[k] = src[k]
    return ret


class KubeObjNoNamespace(Exception):
    pass


class KubeTypeUnresolvable(Exception):
    pass


class KubeBaseObj(object):
    _default_ns = 'default'
    _defaults = {}
    _types = {}
    has_metadata = False

    def __init__(self, *args, **kwargs):
        # put the identifier in if it's specified
        if hasattr(self, 'identifier') and len(args) > 0 and self.identifier not in kwargs:
            kwargs[self.identifier] = args[0]
        self._data = self._find_defaults(False)

        self.namespace = None
        self.set_namespace(KubeBaseObj._default_ns)

        if self.has_metadata:
            self.annotations = {}
            self.labels = {}

        if hasattr(self, 'early_init'):
            self.early_init(*args, **kwargs)

        for k in kwargs:
            if k not in self._data:
                raise TypeError("{} is not a valid argument for {} constructor".format(
                                k, self.__class__.__name__))

            if not isinstance(kwargs[k], (list, dict)):
                self._data[k] = kwargs[k]
            elif isinstance(kwargs[k], list):
                self._data[k] = []
                self._data[k].extend(kwargs[k])
            else:
                self._data[k].update(kwargs[k])

    def _find_defaults(self, types=False):
        ret = {}
        def _recurse(cls):
            if not (len(cls.__bases__) == 0 or (len(cls.__bases__) == 1 and cls.__bases__[0] is object)):
                for c in cls.__bases__:
                    _recurse(c)
            if types:
                if hasattr(cls, '_types'):
                    ret.update(copy.deepcopy(cls._types))
            else:
                if hasattr(cls, '_defaults'):
                    ret.update(copy.deepcopy(cls._defaults))
        _recurse(self.__class__)
        if hasattr(self, 'identifier'):
            if types:
                ret[self.identifier] = Identifier
            else:
                ret[self.identifier] = ''
        return ret

    def set_namespace(self, name):
        if hasattr(self, 'get_ns'):
            self.namespace = self.get_ns(name)

    def check_namespace(self):
        return True

    def do_validate(self):
        return True

    def validate(self, path=None):
        def basic_validation(typ):
            if isinstance(typ, KubeType):
                return typ
            elif isinstance(typ, (type, KubeBaseObj)):
                return KubeType.construct_arg(typ)
            elif Integer().do_check(typ, None):
                if typ > 0:
                    return Positive(NonZero(Integer))
                elif typ < 0:
                    return NonZero(Integer)
                return Integer()
            elif Number().do_check(typ, None):
                if typ > 0:
                    return Positive(Number)
                return Number()
            elif Boolean().do_check(typ, None):
                return Boolean()
            elif String().do_check(typ, None):
                return NonEmpty(String)
            return None

        if path is None:
            path = 'self'

        types = self._find_defaults(False)
        types.update(self._find_defaults(True))

        if hasattr(self, 'labels'):
            Map(String, String).check(self.labels, '{}.(labels)'.format(path))
        if hasattr(self, 'annotations'):
            Map(String, String).check(self.annotations, '{}.(annotations)'.format(path))

        if not self.check_namespace():
            raise KubeObjNoNamespace("No namespace attached to object at {}".format(path))

        for k in types:
            t = basic_validation(types[k])
            if t is not None:
                types[k] = t
            elif isinstance(types[k], (list, tuple)):
                if len(types[k]) > 0:
                    t = basic_validation(types[k][0])
                    if t is not None:
                        types[k] = NonEmpty(List(t))
            elif isinstance(types[k], dict):
                if len(types[k]) > 0:
                    kk = tuple(types[k].keys())[0]
                    vv = types[k][kk]
                    tk = basic_validation(kk)
                    tv = basic_validation(vv)
                    if tk is not None and tv is not None:
                        types[k] = NonEmpty(Dict(tk, tv))

            if not isinstance(types[k], KubeType):
                raise KubeTypeUnresolvable(
                    "Couldn't resolve (from {}) {} into a default type".format(k, repr(types[k])))

        for k in types:
            if k in self._data:
                types[k].check(self._data[k], path + '.' + k)
            else:
                types[k].check(None, path + '.' + k)

        for k in self._data:
            if k not in types:
                raise KubeTypeUnresolvable(
                    "Unknown data key {} - no type information".format(k))

        return self.do_validate()

    def render(self):
        return None

    def renderer(self, zlen_ok=(), order=(), mapping=None, return_none=False):
        ret = copy.deepcopy(self._data)

        def _render(x):
            if isinstance(x, KubeBaseObj):
                return x.do_render()
            return x

        for r in self._data:
            res = _render(ret[r])
            if res is None:
                del ret[r]
            else:
                ret[r] = res

        for r in self._data:
            if r not in ret:
                continue
            if isinstance(ret[r], (list, tuple)):
                ret[r] = list(filter(lambda x: x is not None, map(_render, ret[r])))
            elif isinstance(ret[r], dict):
                tret = OrderedDict()
                for k in ret[r]:
                    res = _render(ret[r][k])
                    if res is not None:
                        tret[k] = res
                ret[r] = tret

            if isinstance(ret[r], (list, tuple, dict)):
                if len(ret[r]) == 0 and r not in zlen_ok:
                    del ret[r]

        if mapping is not None:
            for k in mapping:
                if k in ret:
                    if mapping[k] is not None:
                        ret[mapping[k]] = ret[k]
                    del ret[k]

        if return_none and len(ret) == 0:
            return None

        if len(order) != 0:
            return order_dict(ret, order)

        return ret

    def do_render(self):
        self.validate()
        obj = self.render()
        if obj is None:
            return None

        if hasattr(self, 'apiVersion') and hasattr(self, 'kind'):
            ret = OrderedDict(apiVersion=self.apiVersion)
            ret['kind'] = self.kind
        else:
            ret = OrderedDict()

        if self.has_metadata:
            if 'metadata' in obj:
                if 'labels' in obj['metadata']:
                    obj['metadata']['labels'].update(self.labels)
                    if hasattr(self, 'identifier'):
                        obj['metadata']['labels'] = order_dict(obj['metadata']['labels'], (self.identifier,))
                elif len(self.labels) != 0:
                    obj['metadata']['labels'] = copy.copy(self.labels)

                if 'annotations' in obj['metadata']:
                    obj['metadata']['annotations'].update(self.annotations)
                elif len(self.annotations) != 0:
                    obj['metadata']['annotations'] = copy.copy(self.annotations)

                if hasattr(self, 'identifier'):
                    obj['metadata'] = order_dict(obj['metadata'], (self.identifier, 'annotations', 'labels'))
                else:
                    obj['metadata'] = order_dict(obj['metadata'], ('annotations', 'labels'))

            elif len(self.labels) != 0 or len(self.annotations) != 0:
                obj['metadata'] = {}
                if len(self.labels) != 0:
                    obj['metadata']['labels'] = copy.copy(self.labels)
                if len(self.annotations) != 0:
                    obj['metadata']['annotations'] = copy.copy(self.annotations)

            obj = order_dict(obj, ('metadata', 'spec'))

        if hasattr(self, 'identifier'):
            obj = order_dict(obj, (self.identifier,))

        ret.update(obj)
        return ret

    def __getattr__(self, k):
        if k != '_data' and k in self._data:
            return self._data[k]
        return object.__getattr__(self, k)

    def __setattr__(self, k, v):
        if k in ('_data',):
            pass
        elif k in self._data:
            return self._data.__setitem__(k, v)
        return object.__setattr__(self, k, v)

    def __getitem__(self, k):
        return self._data.__getitem__(k)

    def __setitem__(self, k, v):
        if not k in self._data:
            raise KeyError("key {} is not defined for {}".format(k, self.__class__.__name__))
        return self._data.__setitem__(k, v)


class KubeObj(KubeBaseObj):
    identifier = 'name'
    has_metadata = True

    def check_namespace(self):
        if isinstance(self.namespace, KubeObj) and hasattr(self.namespace, 'kind') and \
                self.namespace.kind == 'Namespace':
            return True
        return False

    def early_init(self, *args, **kwargs):
        if not hasattr(self, 'apiVersion') or not hasattr(self, 'kind') or not hasattr(self, 'identifier'):
            raise TypeError(
                "Class {} is an abstract base class and can't be instantiated".format(self.__class__.__name__))


class KubeSubObj(KubeBaseObj):
    pass
