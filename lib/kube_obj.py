# (c) Copyright 2017 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from collections import OrderedDict

class KubeObj(object):
    def __init__(self, *args, **kwargs):
        if not hasattr(self, 'apiVersion') or not hasattr(self, 'kind') or not hasattr(self, 'identifier'):
            raise TypeError(
                "Class {} is an abstract base class and can't be instantiated".format(self.__class__.__name__))
        if self.identifier not in kwargs:
            if len(args) == 0:
                raise ValueError("Must specify identifier ({}) as part of construction".format(self.identifier))
            setattr(self, self.identifier, args[0])
        else:
            setattr(self, self.identifier, kwargs[self.identifier])

        self._data = {}

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

        ret = OrderedDict(apiVersion=self.apiVersion)
        ret['kind'] = self.kind
        if 'metadata' in obj:
            obj['metadata'] = make_first(obj['metadata'], self.identifier)
        obj = make_first(obj, 'metadata')
        ret.update(obj)
        return ret
