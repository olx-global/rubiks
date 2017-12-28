# (c) Copyright 2017 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from kube_obj import KubeSubObj
from kube_types import *


class BaseSelector(KubeSubObj):
    pass


class MatchLabelsSelector(BaseSelector):
    _defaults = {'matchLabels': {}}
    _types = {'matchLabels': Map(String, String)}

    def render(self):
        if len(self._data['matchLabels']) == 0:
            return None
        return {'matchLabels': self._data['matchLabels']}


class MatchExpression(KubeSubObj):
    _defaults = {
        'key': None,
        'operator': 'In',
        'values': [],
        }

    _types = {
        'key': NonEmpty(String),
        'operator': Enum('In', 'NotIn', 'Exists', 'DoesNotExist'),
        'values': Nullable(List(String)),
        }

    def render(self):
        return self.renderer(order=('key', 'operator', 'values'))


class MatchExpressionsSelector(BaseSelector):
    _defaults = {'matchExpressions': []}
    _types = {'matchExpressions': NonEmpty(List(MatchExpression))}

    def render(self):
        ret = self.renderer()
        if len(ret['matchExpressions']) == 0:
            return None
        return {'matchExpressions': ret['matchExpressions']}
