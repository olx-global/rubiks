# (c) Copyright 2017 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from collections import OrderedDict
from kube_types import *
import copy

class KubeBaseObj(object):
    _defaults = {}
    _types = {}

    def __init__(self, *args, **kwargs):
        # put the identifier in if it's specified
        if hasattr(self, 'identifier') and len(args) > 0 and self.identifier not in kwargs:
            kwargs[self.identifier] = args[0]
        self._data = self._find_defaults(False)

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
#            if types:
#               ret[self.identifier] = self.Identifier
#            else:
                ret[self.identifier] = ''
        return ret

    def render(self):
        return None

    def do_render(self):
        def make_first(obj, k):
            if k not in obj:
                return OrderedDict(obj)
            else:
                kwargs = {k: obj[k]}
                ret = OrderedDict(**kwargs)
                if isinstance(obj, OrderedDict):
                    for kk in obj.keys():
                        if kk == k:
                            continue
                        ret[kk] = obj[kk]
                else:
                    for kk in sorted(obj.keys()):
                        if kk == k:
                            continue
                        ret[kk] = obj[kk]
            return ret

        obj = self.render()
        if obj is None:
            raise TypeError("Cannot render object of type {}: no render() method".format(self.__class__.__name__))

        if hasattr(self, 'apiVersion') and hasattr(self, 'kind'):
            ret = OrderedDict(apiVersion=self.apiVersion)
            ret['kind'] = self.kind
        else:
            ret = OrderedDict()

        if 'metadata' in obj:
            obj['metadata'] = make_first(obj['metadata'], self.identifier)
        obj = make_first(obj, 'metadata')
        ret.update(obj)
        return ret

    def __getattr__(self, k):
        if k in self._data:
            return self._data[k]
        return object.__getattr__(self, k)

    def __setattr__(self, k, v):
        if k in ('_data',):
            pass
        elif k in self._data:
            return self._data.__setitem__(k, v)
        return object.__setattr__(self, k, v)

class KubeObj(KubeBaseObj):
    identifier = 'name'

    def early_init(self, *args, **kwargs):
        if not hasattr(self, 'apiVersion') or not hasattr(self, 'kind') or not hasattr(self, 'identifier'):
            raise TypeError(
                "Class {} is an abstract base class and can't be instantiated".format(self.__class__.__name__))

class KubeSubObj(KubeBaseObj):
    pass
