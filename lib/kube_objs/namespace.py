# (c) Copyright 2017-2018 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from kube_obj import KubeObj


class Namespace(KubeObj):
    apiVersion = 'v1'
    kind = 'Namespace'
    kubectltype = 'namespace'
    _output_order = 0

    def __init__(self, *args, **kwargs):
        KubeObj.__init__(self, *args, **kwargs)
        self._in_cluster = None

    def set_namespace(self, name):
        return None

    def check_namespace(self):
        return True

    _exclude = {
        '.status': True,
        '.spec': True,
        }

    def render(self):
        if self.name in ('kube-system', 'default'):
            return None
        if self._is_openshift and self.name in ('openshift', 'openshift-infra'):
            return None
        return {'metadata': {'name': self.name, 'labels': {'name': self.name}}}
