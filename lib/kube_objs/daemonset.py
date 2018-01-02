# (c) Copyright 2017-2018 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from kube_obj import KubeObj, order_dict
from .pod import *
from .selectors import BaseSelector
from .mixins import SelectorsPreProcessMixin

class DaemonSet(KubeObj, SelectorsPreProcessMixin):
    apiVersion = 'extensions/v1beta1'
    kind = 'DaemonSet'
    kubectltype = 'daemonset'

    _defaults = {
        'pod_template': PodTemplateSpec(),
        'selector': None,
        }

    _types = {
        'pod_template': PodTemplateSpec,
        'selector': Nullable(BaseSelector),
        }

    def xf_selector(self, v):
        return self.fix_selectors(v)

    def render(self):
        ret = self.renderer(mapping={'pod_template': 'template', 'name': None})
        return {'metadata': {'name': self._data['name']}, 'spec': ret}
