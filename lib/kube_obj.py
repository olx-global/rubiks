# (c) Copyright 2017-2018 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import copy
import traceback
from collections import OrderedDict

from kube_types import *
from user_error import UserError, paths as user_error_paths


def _rec_update_objs(obj):
    for k in obj._data:
        if isinstance(obj._data[k], KubeBaseObj):
            obj._data[k]._caller_file = obj._caller_file
            obj._data[k]._caller_line = obj._caller_line
            obj._data[k]._caller_fn = obj._caller_fn
            _rec_update_objs(obj._data[k])


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


class KubeAttributeError(UserError, AttributeError):
    pass


class KubeBaseObj(object):
    _default_ns = 'default'
    _default_cluster = None
    _uses_namespace = False
    _defaults = {}
    _types = {}
    _map = {}
    _parent_types = None
    has_metadata = False
    _is_openshift = False
    _always_regenerate = False

    def __init__(self, *args, **kwargs):
        # put the identifier in if it's specified
        if hasattr(self, 'identifier') and len(args) > 0 and self.identifier not in kwargs:
            kwargs[self.identifier] = args[0]
        self._data = self.__class__._find_defaults('_defaults')

        self._caller_file, self._caller_line, self._caller_fn = traceback.extract_stack(limit=2)[0][0:3]

        for k in self.__class__._find_defaults('_map'):
            self._data[k] = None

        self.namespace = None
        self.set_namespace(KubeBaseObj._default_ns)

        self._in_cluster = KubeBaseObj._default_cluster

        if hasattr(self, 'add_obj'):
            self.add_obj()

        if self.has_metadata:
            self.annotations = {}
            self.labels = {}

        if hasattr(self, 'early_init'):
            self.early_init(*args, **kwargs)

        for k in kwargs:
            if k not in self._data:
                raise UserError(TypeError("{} is not a valid argument for {} constructor".format(
                                          k, self.__class__.__name__)))

            if not isinstance(kwargs[k], (list, dict)):
                self._data[k] = kwargs[k]
            elif isinstance(kwargs[k], list):
                self._data[k] = []
                self._data[k].extend(kwargs[k])
            else:
                if not isinstance(self._data[k], dict):
                    self._data[k] = {}
                self._data[k].update(kwargs[k])

        _rec_update_objs(self)

    def clone(self, *args, **kwargs):
        ret = self._clone()
        ret._caller_file, ret._caller_line, ret._caller_fn = traceback.extract_stack(limit=2)[0][0:3]
        _rec_update_objs(self)

        if hasattr(self, 'identifier') and len(args) > 0 and self.identifier not in kwargs:
            kwargs[self.identifier] = args[0]

        for k in kwargs:
            if k not in self._data:
                raise UserError(TypeError("{} is not a valid argument for {} constructor".format(
                                          k, self.__class__.__name__)))

            if not isinstance(kwargs[k], (list, dict)):
                self._data[k] = kwargs[k]
            elif isinstance(kwargs[k], list):
                self._data[k] = []
                self._data[k].extend(kwargs[k])
            else:
                if not isinstance(self._data[k], dict):
                    self._data[k] = {}
                self._data[k].update(kwargs[k])

        return ret

    def _clone(self):
        ret = self.__class__()

        for k in self._data:
            if isinstance(self._data[k], KubeBaseObj):
                ret._data[k] = self._data[k]._clone()
            else:
                ret._data[k] = copy.deepcopy(self._data[k])

        if self.has_metadata:
            ret.annotations = copy.deepcopy(self.annotations)
            ret.labels = copy.deepcopy(self.labels)

        return ret

    @classmethod
    def _find_defaults(cls, clsmap):
        ret = {}
        def _recurse(kls):
            if not (len(kls.__bases__) == 0 or (len(kls.__bases__) == 1 and kls.__bases__[0] is object)):
                for c in kls.__bases__:
                    _recurse(c)
            if hasattr(kls, clsmap):
                ret.update(copy.deepcopy(getattr(kls, clsmap)))
        _recurse(cls)
        if hasattr(cls, 'identifier'):
            if clsmap == '_types':
                ret[cls.identifier] = Identifier
            elif clsmap == '_defaults':
                ret[cls.identifier] = None
        return ret

    def set_namespace(self, name):
        if hasattr(self, 'get_ns'):
            self.namespace = self.get_ns(name)

    def check_namespace(self):
        return True

    def do_validate(self):
        return True

    @classmethod
    def resolve_types(cls):
        if not hasattr(cls, '_resolved_types'):
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

            types = cls._find_defaults('_defaults')
            types.update(cls._find_defaults('_types'))

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

            cls._resolved_types = types

        return cls._resolved_types

    @classmethod
    def get_child_types(cls):
        types = cls.resolve_types()
        ret = {}
        for t in types.values():
            actual_type = t.original_type()
            if actual_type is None:
                continue
            if isinstance(actual_type, list):
                actual_type = actual_type[0]
            elif isinstance(actual_type, dict):
                actual_type = actual_type['value']
            ret[actual_type.__name__] = actual_type
        return ret

    @classmethod
    def is_abstract_type(cls):
        base = KubeBaseObj.render
        this = cls.render
        if hasattr(base, '__func__') and hasattr(this, '__func__'):
            # python 2.7
            return this.__func__ is base.__func__
        # python 3
        return this is base

    @classmethod
    def get_subclasses(cls, non_abstract=True, include_self=False, depth_first=False):
        def _rec_subclasses(kls):
            ret = []
            subclasses = kls.__subclasses__()
            if len(subclasses) > 0:
                if depth_first:
                    for c in subclasses:
                        ret.extend(_rec_subclasses(c))

                if non_abstract:
                    ret.extend(filter(lambda x: not x.is_abstract_type(), subclasses))
                else:
                    ret.extend(subclasses)

                if not depth_first:
                    for c in subclasses:
                        ret.extend(_rec_subclasses(c))

            return ret

        ret = _rec_subclasses(cls)
        if include_self and not(non_abstract and cls.is_abstract_type()):
            if depth_first:
                ret.append(cls)
            else:
                ret.insert(0, cls)

        return ret

    @classmethod
    def get_help(cls):
        def _rec_superclasses(kls):
            ret = []
            superclasses = list(filter(lambda x: x is not KubeBaseObj and x is not KubeSubObj and
                                                 x is not KubeObj and x is not object,
                                       kls.__bases__))

            if len(superclasses) > 0:
                ret.extend(superclasses)
                for c in superclasses:
                    ret.extend(_rec_superclasses(c))

            return ret

        subclasses = list(map(lambda x: x.__name__, cls.get_subclasses(non_abstract=False, include_self=False)))
        superclasses = list(map(lambda x: x.__name__, _rec_superclasses(cls)))

        types = cls.resolve_types()

        abstract = ''
        if cls.is_abstract_type():
            abstract = ' (abstract type)'

        identifier = None
        if hasattr(cls, 'identifier') and cls.identifier is not None:
            identifier = cls.identifier

        txt = '{}{}:\n'.format(cls.__name__, abstract)
        if len(superclasses) != 0:
            txt += '  parents: {}\n'.format(', '.join(superclasses))
        if len(subclasses) != 0:
            txt += '  children: {}\n'.format(', '.join(subclasses))
        if len(cls._parent_types) != 0:
            txt += '  parent types: {}\n'.format(', '.join(sorted(cls._parent_types.keys())))
        txt += '  properties:\n'
        if identifier is not None:
            spc = ''
            if len(identifier) < 7:
                spc = (7 - len(identifier)) * ' '
            txt += '    {} (identifier): {}{}\n'.format(identifier, spc, types[identifier].name())

        mapping = cls._find_defaults('_map')
        rmapping = {}
        for d in mapping:
            if mapping[d] not in rmapping:
                rmapping[mapping[d]] = []
            rmapping[mapping[d]].append(d)

        for p in sorted(types.keys()):
            if p == identifier:
                continue
            spc = ''
            if len(p) < 20:
                spc = (20 - len(p)) * ' '
            if hasattr(cls, 'xf_{}'.format(p)):
                xf = '*'
            else:
                xf = ' '
            txt += '   {}{}: {}{}\n'.format(xf, p, spc, types[p].name())
            if p in rmapping:
                txt += '      ({})\n'.format(', '.join(rmapping[p]))
        return txt

    def has_child_object(self, obj):
        assert isinstance(obj, KubeBaseObj)
        for d in self._data:
            if obj is self._data[d]:
                return True
        return False

    def validate(self, path=None):
        if path is None:
            path = 'self'

        types = self.__class__.resolve_types()
        mapping = self.__class__._find_defaults('_map')

        if hasattr(self, 'labels'):
            Map(String, String).check(self.labels, '{}.(labels)'.format(path))
        if hasattr(self, 'annotations'):
            Map(String, String).check(self.annotations, '{}.(annotations)'.format(path))

        if not self.check_namespace():
            raise UserError(KubeObjNoNamespace("No namespace attached to object at {}".format(path)))

        data = self.xform()

        for k in types:
            if k in data:
                types[k].check(data[k], path + '.' + k)
            else:
                types[k].check(None, path + '.' + k)

        for k in data:
            if k not in types and k not in mapping:
                raise KubeTypeUnresolvable(
                    "Unknown data key {} - no type information".format(k))

        sav_data = self._data
        try:
            self._data = data
            return self.do_validate()
        finally:
            self._data = sav_data

    def render(self):
        return None

    def get_obj(self, prop, *args, **kwargs):
        types = self.__class__.resolve_types()

        mapping = self.__class__._find_defaults('_map')
        if prop in mapping:
            prop = mapping[prop]

        fmt = (prop, self.__class__.__name__)
        if prop not in types:
            raise KeyError("No such property '{}' on {}".format(*fmt))

        typ = types[prop]

        actual_type = typ.original_type()
        if actual_type is None:
            raise UserError(KeyError("Property '{}' can't be auto-constructed in {}".format(*fmt)))

        rtype = None
        if isinstance(actual_type, list):
            actual_type = actual_type[0]
            rtype = 'list'
        elif isinstance(actual_type, dict):
            actual_type = actual_type['value']
            rtype = 'dict'
        else:
            rtype = 'obj'

        if not isinstance(actual_type, type):
            raise TypeError("Unexpected type isn't a type is actually a {} for property '{}' in {}".
                            format(actual_type.__class__.__name__, *fmt))

        if not any(map(lambda x: x is actual_type,
                       KubeBaseObj.get_subclasses(non_abstract=False, include_self=False))):
            raise TypeError("Unexpected type {} for property '{}' in {}, must be a subclass of KubeBaseObj".
                            format(actual_type.__name__, *fmt))

        if len(args) > 0 and isinstance(args[0], type):
            if any(map(lambda x: x is args[0],
                       actual_type.get_subclasses(non_abstract=True, include_self=True))):
                actual_type = args[0]
                args = args[1:]
            else:
                raise UserError(TypeError(("Unexpected type as first argument for property '{}' in {}, must be subclass " +
                                           "of {}. Valid types are: {}").
                                           format(prop, self.__class__.__name__, actual_type.__name__,
                                                  ", ".join(map(lambda x: x.__name__,
                                                                actual_type.get_subclasses(
                                                                    non_abstract=True, include_self=True))))))

        if actual_type.is_abstract_type():
            raise UserError(TypeError("Can't construct {} for '{}' in {}, you probably want one of: {}".
                                      format(actual_type.__name__, prop, self.__class__.__name__,
                                             ", ".join(map(lambda x: x.__name__,
                                                           actual_type.get_subclasses(non_abstract=True))))))

        if rtype == 'dict':
            if len(args) == 0:
                raise UserError(ValueError("Must supply key for newly constructed property '{}' on {}".format(*fmt)))
            dkey = args[0]
            args = args[1:]

        result = actual_type(*args, **kwargs)

        new = result
        if rtype == 'list':
            new = [result]
        elif rtype == 'dict':
            new = {dkey: result}

        if self._data[prop] is None or rtype == 'obj':
            self._data[prop] = new
            return result

        if rtype == 'list' and isinstance(self._data[prop], list):
            self._data[prop].extend(new)
        elif rtype == 'dict' and isinstance(self._data[prop], dict):
            self._data[prop].update(new)
        else:
            raise UserError(TypeError("Expecting {} or None for property '{}' on {}".format(rtype, *fmt)))

        return result

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

        return order_dict(ret, ())

    def xform(self):
        ret = {}
        mapping = self.__class__._find_defaults('_map')

        for d in self._data:
            if hasattr(self, 'xf_{}'.format(d)):
                ret[d] = getattr(self, 'xf_{}'.format(d))(self._data[d])
            elif d in mapping and hasattr(self, 'xf_{}'.format(mapping[d])):
                ret[d] = getattr(self, 'xf_{}'.format(mapping[d]))(self._data[d])
            else:
                ret[d] = self._data[d]

        for d in mapping:
            if d not in ret or ret[d] is None:
                continue
            if mapping[d] in ret and ret[mapping[d]] is None:
                ret[mapping[d]] = ret[d]
            del ret[d]

        return ret

    def do_render(self):
        self.validate()

        sav_data = self._data
        try:
            self._data = self.xform()
            obj = self.render()
        finally:
            self._data = sav_data

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

                if self._uses_namespace and hasattr(self, 'namespace') and self.namespace is not None:
                    obj['metadata']['namespace'] = self.namespace.name

                if hasattr(self, 'identifier'):
                    obj['metadata'] = order_dict(obj['metadata'], (self.identifier, 'namespace', 'annotations', 'labels'))
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
        if k != '_data' and hasattr(self, '_data') and k in self._data:
            return self._data[k]
        if k.startswith('new_') and k[4:] in self._data:
            def get_prop(*args, **kwargs):
                return self.get_obj(k[4:], *args, **kwargs)
            get_prop.__name__ = k
            return get_prop
        elif k.startswith('new_') and k[4:] + 's' in self._data:
            def get_prop(*args, **kwargs):
                return self.get_obj(k[4:] + 's', *args, **kwargs)
            get_prop.__name__ = k
            return get_prop
        raise KubeAttributeError(AttributeError('No such attribute {} for {}'.format(k, self.__class__.__name__)))

    def __setattr__(self, k, v):
        if k in ('_data',):
            pass
        elif k in self._data:
            return self._data.__setitem__(k, v)
        if k in ('labels', 'annotations', 'namespace'):
            return object.__setattr__(self, k, v)

        fn = traceback.extract_stack(limit=2)[0][0]
        for p in user_error_paths:
            if fn.startswith(p + '/'):
                return object.__setattr__(self, k, v)

        raise KubeAttributeError(AttributeError('No such attribute {} for {}'.format(k, self.__class__.__name__)))

    def __getitem__(self, k):
        if not k in self._data:
            raise UserError(KeyError("key {} is not defined for {}".format(k, self.__class__.__name__)))
        return self._data.__getitem__(k)

    def __setitem__(self, k, v):
        if not k in self._data:
            raise UserError(KeyError("key {} is not defined for {}".format(k, self.__class__.__name__)))
        return self._data.__setitem__(k, v)


class KubeObj(KubeBaseObj):
    identifier = 'name'
    has_metadata = True
    _uses_namespace = True

    @classmethod
    def is_abstract_type(cls):
        if not hasattr(cls, 'apiVersion') or not hasattr(cls, 'kind'):
            return True
        base = KubeBaseObj.render
        this = cls.render
        if hasattr(base, '__func__') and hasattr(this, '__func__'):
            # python 2.7
            return this.__func__ is base.__func__
        # python 3
        return this is base

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
