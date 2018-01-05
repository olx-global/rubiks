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
        elif 'valueFrom' in doc and 'configMapKeyRef' in doc['valueFrom']:
            return ContainerEnvConfigMapSpec
        elif 'valueFrom' in doc and 'fieldRef' in doc['valueFrom']:
            return ContainerEnvPodFieldSpec
        elif 'valueFrom' in doc and 'resourceFieldRef' in doc['valueFrom']:
            return ContainerEnvContainerResourceSpec


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


class ContainerEnvConfigMapSpec(ContainerEnvBaseSpec):
    _defaults = {
        'key': '',
        'map_name': '',
        }

    _types = {
        'key': NonEmpty(String),
        'map_name': Identifier,
        }

    _parse = {
        'key': ('valueFrom', 'configMapKeyRef', 'key'),
        'map_name': ('valueFrom', 'configMapKeyRef', 'name'),
        }

    def render(self):
        cret = order_dict({'key': self._data['key'], 'name': self._data['map_name']}, ('name', 'key'))
        return order_dict({'name': self._data['name'], 'valueFrom': {'configMapKeyRef': cret}}, ('name', 'valueFrom'))


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


class ContainerEnvPodFieldSpec(ContainerEnvBaseSpec):
    _defaults = {
        'apiVersion': None,
        'fieldPath': '',
        }

    _types = {
        'apiVersion': Nullable(Enum('v1')),
        'fieldPath': Enum('metadata.name', 'metadata.namespace',
                          'metadata.labels', 'metadata.annotations',
                          'spec.nodeName', 'spec.serviceAccountName',
                          'status.podIP',
                          ),
        }

    _parse = {
        'apiVersion': ('valueFrom', 'fieldRef', 'apiVersion'),
        'fieldPath': ('valueFrom', 'fieldRef', 'fieldPath'),
        }

    def render(self):
        if self._data['apiVersion'] is not None:
            fret = order_dict({'apiVersion': self._data['apiVersion'], 'fieldPath': self._data['fieldPath']},
                              ('apiVersion', 'fieldPath'))
        else:
            fret = {'fieldPath': self._data['fieldPath']}
        return order_dict({'name': self._data['name'], 'valueFrom': {'fieldRef': fret}},
                          ('name', 'valueFrom'))


class ContainerEnvContainerResourceSpec(ContainerEnvBaseSpec):
    _defaults = {
        'containerName': None,
        'divisor': None,
        'resource': '',
        }

    _types = {
        'containerName': Nullable(Identifier),
        'divisor': Nullable(NonEmpty(String)),
        'resource': Enum('limits.cpu', 'limits.memory', 'requests.cpu', 'requests.memory'),
        }

    _parse = {
        'containerName': ('valueFrom', 'resourceFieldRef', 'containerName'),
        'divisor': ('valueFrom', 'resourceFieldRef', 'divisor'),
        'resource': ('valueFrom', 'resourceFieldRef', 'resource'),
        }

    def render(self):
        rret = {'resource': self._data['resource']}
        for r in ('containerName', 'divisor'):
            if self._data[r] is not None:
                rret[r] = self._data[r]
        rret = order_dict(rret, ('containerName', 'divisor', 'resource'))
        return order_dict({'name': self._data['name'], 'valueFrom': {'resourceFieldRef': rret}},
                          ('name', 'valueFrom'))
