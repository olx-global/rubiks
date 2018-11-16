# (c) Copyright 2017-2018 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import base64
import json
import os
import subprocess
import sys
import traceback

from user_error import UserError
import kube_yaml
import var_types


class Base64(var_types.VarEntity):
    def init(self, value):
        self.value = value

    def to_string(self):
        if isinstance(self.value, var_types.VarEntity) and self._in_validation:
            s = self.value.validation_value()
        else:
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
                if self._in_validation:
                    return obj.validation_value()
                else:
                    return str(obj)
            raise TypeError("Unknown type for object {}".format(repr(obj)))
        return json.JSONEncoder(default=_default_json, **(self.args)).encode(self.value)


class YAML(var_types.VarEntity):
    def init(self, value):
        self.value = value

    def to_string(self):
        ret = kube_yaml.yaml_safe_dump(self.value, default_flow_style=False)
        if isinstance(ret, var_types.VarEntity) and self._in_validation:
            return ret.validation_value()
        return str(ret)


class Confidential(var_types.VarEntity):
    def init(self, value):
        self.value = value

    def eq(self, other):
        return self.value == other.value

    def to_string(self):
        if var_types.VarContext.current_context is not None:
            var_types.VarContext.current_context['confidential'] = True
        if var_types.VarContext.show_confidential or self._in_validation:
            return str(self.value)
        return "*** HIDDEN ***"


class CommandRuntimeException(Exception):
    pass


class Command(var_types.VarEntity):
    def init(self, cmd, cwd=None, env_clear=False, env=None, good_rc=None, rstrip=False, eol=False):
        self.cmd = cmd
        self.cwd = cwd
        self.env_clear = env_clear
        self.env = env
        self.good_rc = good_rc
        self.rstrip = rstrip
        self.eol = eol
        self.tb = traceback.extract_stack()

    def to_string(self):
        if self._in_validation:
            return "command_output"

        env = {}
        if not self.env_clear:
            env.update(os.environ)
        if self.env is not None:
            for e in self.env:
                env[e] = str(self.env[e])

        try:
            p = subprocess.Popen(map(str, self.cmd), close_fds=True, shell=False, cwd=self.cwd, env=env,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except OSError as e:
            raise UserError(CommandRuntimeException("Command {} didn't run: {}: {}".format(self.cmd[0], e.__class__.__name__, str(e))), tb=self.tb)

        (out, err) = p.communicate()

        out = out.decode('utf8')
        err = err.decode('utf8')

        if len(err.strip()) != 0:
            print(err.rstrip(), file=sys.stderr)

        if self.rstrip:
            out = out.rstrip()
        if self.eol and (out == '' or out[-1] != '\n'):
            out += '\n'

        if self.good_rc is None or rc in self.good_rc:
            return out

        raise UserError(CommandRuntimeException("Command {} exited with code rc={}".format(
                                                    self.cmd[0], p.returncode)), tb=self.tb)
