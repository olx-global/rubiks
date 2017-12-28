# (c) Copyright 2017 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from kube_obj import KubeObj, KubeSubObj, order_dict
from kube_types import *
from .pod import *
from .selectors import *


class BaseUpdateStrategy(KubeSubObj):
    pass


class RollingUpdateStrategy(BaseUpdateStrategy):
    _defaults = {
        'maxSurge': 1,
        'maxUnavailable': 50,
    }

    _types = {
        'maxSurge': Positive(NonZero(Integer)),
        'maxUnavailable': Positive(Integer),
    }

    def render(self):
        return {'rollingUpdate': self.renderer(), 'type': 'RollingUpdate'}


class Deployment(KubeObj):
    apiVersion = 'extensions/v1beta1'
    kind = 'Deployment'
    kubectltype = 'deployment'

    _defaults = {
        'replicas': 1,
        'revisionHistoryLimit': None,
        'selector': None,
        'strategy': None,
        'minReadySeconds': None,
        'pod_template': PodTemplateSpec(),
    }

    _types = {
        'replicas': Positive(NonZero(Integer)),
        'revisionHistoryLimit': Nullable(Positive(NonZero(Integer))),
        'selector': Nullable(BaseSelector),
        'strategy': Nullable(BaseUpdateStrategy),
        'minReadySeconds': Nullable(Positive(NonZero(Integer))),
    }

    def render(self):
        ret = self.renderer(mapping={'pod_template': 'template'}, order=('replicas',))
        if isinstance(self._data['selector'], MatchLabelsSelector):
            self.labels.update(self._data['selector']._data['matchLabels'])
        del ret['name']
        return {'metadata': {'name': self._data['name']}, 'spec': ret}
