# (c) Copyright 2017-2018 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from kube_obj import KubeSubObj
from kube_types import *
from user_error import UserError


class BaseSelector(KubeSubObj):
    pass


class MatchLabelsSelector(BaseSelector):
    _defaults = {'matchLabels': {}}
    _types = {'matchLabels': Map(String, String)}

    def render(self):
        ret = self.renderer()
        if len(ret['matchLabels']) == 0:
            return None
        return {'matchLabels': ret['matchLabels']}


class MatchExpressionInvalid(Exception):
    pass


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

    def do_validate(self):
        if self._data['operator'] in ('In', 'NotIn'):
            if self._data['values'] is None or len(self._data['values']) == 0:
                raise UserError(MatchExpressionInvalid('operator In/NotIn requires nonempty values'))
        else:
            if self._data['values'] is not None and len(self._data['values']) != 0:
                raise UserError(MatchExpressionInvalid('operator Exists/DoesNotExist requires empty values'))
        return True

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
