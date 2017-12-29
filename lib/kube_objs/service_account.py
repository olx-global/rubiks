# (c) Copyright 2017 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from kube_obj import KubeObj
from kube_types import *


class ServiceAccount(KubeObj):
    apiVersion = 'v1'
    kind = 'ServiceAccount'
    kubectltype = 'serviceaccount'

    _defaults = {
        'imagePullSecrets': None,
        'secrets': None,
        }

    _types = {
        'imagePullSecrets': Nullable(List(Identifier)),
        'secrets': Nullable(List(Identifier)),
        }

    def render(self):
        ret = self.renderer()
        del ret['name']
        ret['metadata'] = {'name': self._data['name']}
        return ret
