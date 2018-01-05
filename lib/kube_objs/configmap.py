# (c) Copyright 2017-2018 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from kube_obj import KubeObj
from kube_types import *


class SingleConfig(object):
    def __init__(self, name, namespace, key):
        self.name = name
        self.namespace = namespace
        self.key = key


class ConfigMap(KubeObj):
    apiVersion = 'v1'
    kind = 'ConfigMap'
    kubectltype = 'configmap'
    _output_order = 60

    _defaults = {
        'files': {}
        }

    _types = {
        'files': Map(String, String),
        }

    _parse = {
        'files': ('data',),
        }

    def get_key(self, key):
        if not key in self._data['files']:
            raise UserError(KeyError("Key {} doesn't exist in configmap".format(key)))
        return SingleConfig(name=self._data['name'], namespace=self.namespace, key=key)

    def render(self):
        if len(self._data['files']) == 0:
            return None
        return {'metadata': {'name': self.name}, 'data': self._data['files']}
