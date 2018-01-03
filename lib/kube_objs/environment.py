# (c) Copyright 2017-2018 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from kube_obj import KubeSubObj, order_dict
from kube_types import *


class ContainerEnvBaseSpec(KubeSubObj):
    _defaults = {
        'name': '',
        }

    _types = {
        'name': NonEmpty(String),
        }

    def find_subparser(self, doc):
        if 'value' in doc or 'valueFrom' not in doc:
            return ContainerEnvSpec
        if 'valueFrom' in doc and 'secretKeyRef' in doc['valueFrom']:
            return ContainerEnvSecretSpec


class ContainerEnvSpec(ContainerEnvBaseSpec):
    _defaults = {
        'value': '',
        }

    _types = {
        'value': String,
        }

    def render(self):
        ret = self.renderer(order=('name', 'value'))
        if 'value' in ret and ret['value'] == '':
            del ret['value']
        return ret


class ContainerEnvSecretSpec(ContainerEnvBaseSpec):
    _defaults = {
        'key': '',
        'secret_name': '',
        }

    _types = {
        'key': NonEmpty(String),
        'secret_name': Identifier,
        }

    _parse = {
        'key': ('valueFrom', 'secretKeyRef', 'key'),
        'secret_name': ('valueFrom', 'secretKeyRef', 'name'),
        }

    def render(self):
        sret = order_dict({'key': self._data['key'], 'name': self._data['secret_name']}, ('name', 'key'))
        return order_dict({'name': self._data['name'], 'valueFrom': {'secretKeyRef': sret}}, ('name', 'valueFrom'))
