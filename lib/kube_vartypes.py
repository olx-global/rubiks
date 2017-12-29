# (c) Copyright 2017 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import base64
import json
import var_types


class Base64(var_types.VarEntity):
    def init(self, value):
        self.value = value

    def to_string(self):
        s = str(self.value)
        try:
            return base64.b64encode(s).decode('utf8')
        except TypeError:
            return base64.b64encode(s.encode('utf8')).decode('utf8')


class JSON(var_types.VarEntity):
    def init(self, value):
        self.value = value
        self.args = {'indent': None, 'separators': (',',':')}

    def to_string(self):
        def _default_json(obj):
            if isinstance(obj, var_types.VarEntity):
                return str(obj)
            raise TypeError("Unknown type for object {}".format(repr(obj)))
        return json.JSONEncoder(default=_default_json, **(self.args)).encode(self.value)


class Confidential(var_types.VarEntity):
    def init(self, value):
        self.value = value

    def to_string(self):
        if var_types.VarContext.show_confidential:
            return str(self.value)
        return "*** HIDDEN ***"
