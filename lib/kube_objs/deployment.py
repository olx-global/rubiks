# (c) Copyright 2017-2018 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from kube_obj import KubeObj, KubeSubObj, order_dict
from kube_types import *
from .pod import *
from .selectors import *


class DplBaseUpdateStrategy(KubeSubObj):
    pass


class DplRecreateStrategy(DplBaseUpdateStrategy):
    def render(self):
        return {'type': 'Recreate'}


class DplRollingUpdateStrategy(DplBaseUpdateStrategy):
    _defaults = {
        'maxSurge': None,
        'maxUnavailable': None,
        }

    _types = {
        'maxSurge': SurgeSpec,
        'maxUnavailable': SurgeSpec,
        }

    def do_validate(self):
        return SurgeCheck.validate(self._data['maxSurge'], self._data['maxUnavailable'])

    def render(self):
        ret = self.renderer()
        if len(ret) == 0:
            return {'type': 'RollingUpdate'}
        return {'rollingUpdate': ret, 'type': 'RollingUpdate'}


class ReplicationController(KubeObj):
    apiVersion = 'v1'
    kind = 'ReplicationController'
    kubectltype = 'replicationcontroller'

    _defaults = {
        'minReadySeconds': None,
        'pod_template': PodTemplateSpec(),
        'replicas': 1,
        'selector': None,
        }

    _types = {
        'minReadySeconds': Nullable(Positive(NonZero(Integer))),
        'pod_template': PodTemplateSpec(),
        'replicas': Positive(NonZero(Integer)),
        'selector': Nullable(Map(String, String)),
        }

    def render(self):
        ret = self.renderer(mapping={'pod_template': 'template'}, order=('replicas', 'selector', 'template'))
        del ret['name']
        return {'metadata': {'name': self._data['name']}, 'spec': ret}


class Deployment(KubeObj):
    apiVersion = 'extensions/v1beta1'
    kind = 'Deployment'
    kubectltype = 'deployment'

    _defaults = {
        'minReadySeconds': None,
        'paused': None,
        'pod_template': PodTemplateSpec(),
        'progressDeadlineSeconds': None,
        'replicas': 1,
        'revisionHistoryLimit': None,
        'selector': None,
        'strategy': None,
        }

    _types = {
        'minReadySeconds': Nullable(Positive(NonZero(Integer))),
        'paused': Nullable(Boolean),
        'pod_template': PodTemplateSpec(),
        'progressDeadlineSeconds': Nullable(Positive(NonZero(Integer))),
        'replicas': Positive(NonZero(Integer)),
        'revisionHistoryLimit': Nullable(Positive(NonZero(Integer))),
        'selector': Nullable(BaseSelector),
        'strategy': Nullable(DplBaseUpdateStrategy),
        }

    def render(self):
        ret = self.renderer(mapping={'pod_template': 'template'}, order=('replicas', 'template'))
        if isinstance(self._data['selector'], MatchLabelsSelector):
            self.labels.update(self._data['selector']._data['matchLabels'])
        del ret['name']
        return {'metadata': {'name': self._data['name']}, 'spec': ret}
