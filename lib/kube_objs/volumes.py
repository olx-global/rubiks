# (c) Copyright 2017-2018 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from collections import OrderedDict
from kube_obj import KubeSubObj, KubeObj
from kube_types import *
from .selectors import BaseSelector
from .pod import Memory


class AWSVolID(String):
    validation_text = 'Expected amazon volume id'

    def do_check(self, value, path):
        if not String().do_check(self, value, path):
            return False
        if value.startswith('aws://'):
            value = value.split('/')[-1]
        if not value.startswith('vol-'):
            return False
        if len(value) == 4:
            return False
        if len(value[4:].rstrip('0123456789abcdef')) != 0:
            return False
        return True


class AWSElasticBlockStore(KubeSubObj):
    _defaults = {
        'volumeID': None,
        'fsType': 'ext4',
        }

    _types = {
        'volumeID': AWSVolID,
        'fsType': Enum('ext4'),
        }

    def render(self):
        return self.renderer(order=('volumeID', 'fsType'))


class PersistentVolumeRef(KubeSubObj):
    _defaults = {
        'apiVersion': None,
        'kind': 'PersistentVolumeClaim',
        'name': '',
        'ns': '',
        }

    _types = {
        'apiVersion': Nullable(String),
        'name': Nullable(Identifier),
        'kind': Nullable(CaseIdentifier),
        'ns': Nullable(Identifier),
        }

    _parse = {
        'ns': ('namespace',),
        }

    _exclude = {
        '.resourceVersion': True,
        '.uid': True,
        }

    def render(self):
        ret = self.renderer(order=('apiVersion', 'name', 'kind', 'ns'))
        if 'ns' in ret:
            ret['namespace'] = ret['ns']
            del ret['ns']
        return ret


class PersistentVolume(KubeObj):
    apiVersion = 'v1'
    kind = 'PersistentVolume'
    kubectltype = 'persistentvolume'
    _uses_namespace = False
    _output_order = 35

    _defaults = {
        'accessModes': ['ReadWriteOnce'],
        'capacity': None,
        'awsElasticBlockStore': None,
        'persistentVolumeReclaimPolicy': None,
        'claimRef': None,
        }

    _types = {
        'accessModes': List(Enum('ReadWriteOnce', 'ReadOnlyMany', 'ReadWriteMany')),
        'capacity': Memory,
        'awsElasticBlockStore': Nullable(AWSElasticBlockStore),
        'persistentVolumeReclaimPolicy': Nullable(Enum('Retain', 'Recycle', 'Delete')),
        'claimRef': Nullable(PersistentVolumeRef),
        }

    _parse_default_base = ('spec',)

    _parse = {
        'capacity': ('spec', 'capacity', 'storage'),
        }

    _exclude = {
        '.status': True,
        }

    def do_validate(self):
        return len(filter(lambda x: self._data[x] is not None, ('awsElasticBlockStore',))) == 1

    def render(self):
        ret = self.renderer(order=('accessModes', 'capacity'))
        del ret['name']
        ret['capacity'] = {'storage': ret['capacity']}
        return {'metadata': {'name': self._data['name']}, 'spec': ret}


class PersistentVolumeClaim(KubeObj):
    apiVersion = 'v1'
    kind = 'PersistentVolumeClaim'
    kubectltype = 'persistentvolumeclaim'
    _output_order = 40

    _defaults = {
        'accessModes': ['ReadWriteOnce'],
        'request': None,
        'selector': None,
        'volumeName': None,
        }

    _types = {
        'accessModes': List(Enum('ReadWriteOnce', 'ReadOnlyMany', 'ReadWriteMany')),
        'request': Memory,
        'selector': Nullable(BaseSelector),
        'volumeName': Nullable(Identifier),
        }

    _parse_default_base = ('spec',)

    _parse = {
        'request': ('spec', 'resources', 'requests', 'storage'),
        }

    _exclude = {
        '.status': True,
        }

    def xf_volumeName(self, v):
        if isinstance(v, PersistentVolume):
            return v.name
        return v

    def render(self):
        ret = self.renderer(return_none=True)
        spec = OrderedDict()
        if 'accessModes' in ret:
            spec['accessModes'] = ret['accessModes']
        if 'request' in ret:
            spec['resources'] = OrderedDict(requests=OrderedDict(storage=ret['request']))
        if 'selector' in ret:
            spec['selector'] = ret['selector']
        if 'volumeName' in ret:
            spec['volumeName'] = ret['volumeName']
        return {'metadata': {'name': ret['name']}, 'spec': spec}
