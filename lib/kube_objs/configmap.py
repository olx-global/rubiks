# (c) Copyright 2017 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from kube_obj import KubeObj

class ConfigMap(KubeObj):
    apiVersion = 'v1'
    kind = 'ConfigMap'
    kubectltype = 'configmap'

    _defaults = {
        'files': {}
        }

    def render(self):
        if len(self._data['files']) == 0:
            return None
        return {'metadata': {'name': self.name}, 'data': self._data['files']}
