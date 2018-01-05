# (c) Copyright 2017-2018 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from .environment import *
from .secret import SingleSecret
from .configmap import SingleConfig
from .selectors import *
from kube_types import *


class EnvironmentPreProcessMixin(object):
    def fix_environment(self, env):
        if env is None:
            return env

        ret = []
        if isinstance(env, dict):
            for k in sorted(env.keys()):
                if isinstance(env[k], ContainerEnvBaseSpec):
                    ret.append(env[k].clone(name=k))
                elif isinstance(env[k], SingleSecret):
                    ret.append(ContainerEnvSecretSpec(name=k, secret_name=env[k].name, key=env[k].key))
                elif isinstance(env[k], SingleConfig):
                    ret.append(ContainerEnvConfigMapSpec(name=k, map_name=env[k].name, key=env[k].key))
                else:
                    ret.append(ContainerEnvSpec(name=k, value=env[k]))

        elif isinstance(env, list):
            for e in env:
                if isinstance(e, dict) and len(e) == 2 and 'name' in e and 'value' in e:
                    if isinstance(e['value'], ContainerEnvBaseSpec):
                        ret.append(e['value'].clone(name=e['name']))
                    elif isinstance(e['value'], SingleSecret):
                        ret.append(ContainerEnvSecretSpec(name=e['name'],
                                                          secret_name=e['value'].name,
                                                          key=e['value'].key))
                    elif isinstance(e['value'], SingleConfig):
                        ret.append(ContainerEnvConfigMapSpec(name=e['name'],
                                                             map_name=e['value'].name,
                                                             key=e['value'].key))
                    else:
                        ret.append(ContainerEnvSpec(name=e['name'], value=e['value']))
                else:
                    ret.append(e)
        else:
            ret = env

        if len(ret) == 0:
            return None

        return ret


class SelectorsPreProcessMixin(object):
    def fix_selectors(self, sel):
        try:
            Map(String, String).check(sel, None)
            return MatchLabelsSelector(matchLabels=sel)
        except:
            pass
        return sel
