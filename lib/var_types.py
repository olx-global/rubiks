# (c) Copyright 2017-2018 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import copy
import sys

if sys.version_info[0] == 3:
    basestring = str


class _VarContext(object):
    def __init__(self):
        self.values = {}
        self.current_context = None
        self.show_confidential = True

VarContext = _VarContext()


class VarEntity(object):
    def __init__(self, *args, **kwargs):
        if '_test' in kwargs and kwargs['_test'] is True:
            return

        self.text = ['', '']
        self.var = ['self']
        self.renderer = None
        self.indent = None
        self._in_validation = False

        self.init(*args, **kwargs)

    def init(self, *args, **kwargs):
        pass

    def to_string(self):
        return ''

    def encode(self, encoding):
        return self

    def clone(self):
        return copy.deepcopy(self)

    def validation_value(self):
        self._in_validation = True
        ret = self.__str__()
        self._in_validation = False
        return ret

    def __add__(self, other):
        if self.renderer is None:
            ret = self.clone()
        else:
            ret = VarEntity()
            ret.var = [self]

        if isinstance(other, VarEntity):
            ret.var.append(other)
            ret.text.append('')
            return ret
        elif isinstance(other, basestring):
            ret.text[-1] += other
            return ret

        return NotImplemented

    def __radd__(self, other):
        if isinstance(other, basestring):
            if self.renderer is None:
                ret = self.clone()
            else:
                ret = VarEntity()
                ret.var = [self]

            ret.text[0] = other + ret.text[0]
            return ret

        return NotImplemented

    def __eq__(self, other):
        if self.__class__ is not other.__class__:
            return False
        if self.text != other.text:
            return False
        if self.var != other.var:
            return False
        if hasattr(self, 'eq'):
            return self.eq(other)
        if self.__class__ is VarEntity:
            return True
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def _internal_render(self):
        ret = ''
        for i in range(0, len(self.text)):
            ret += self.text[i]
            if i < len(self.var):
                if not isinstance(self.var[i], VarEntity) and self.var[i] == 'self':
                    ret += self.to_string()
                elif isinstance(self.var[i], VarEntity):
                    if self._in_validation:
                        ret += self.var[i].validation_value()
                    else:
                        ret += self.var[i].__str__()
                else:
                    raise TypeError("Unexpected object type {} as part of vars".format(repr(self.vars)))
        return ret

    def __str__(self):
        if self.renderer is None:
            return self._internal_render()
        return self.renderer(self._internal_render())
