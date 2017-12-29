# (c) Copyright 2017 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from kube_obj import KubeObj, order_dict
from .pod import *


class DaemonSet(KubeObj):
    apiVersion = 'extensions/v1beta1'
    kind = 'DaemonSet'
    kubectltype = 'daemonset'

    _defaults = {
        'pod_template': PodTemplateSpec(),
    }

    def render(self):
        return {'metadata': {'name': self._data['name']}, 'spec': {'template': self._data['pod_template'].do_render()}}
