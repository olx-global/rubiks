# (c) Copyright 2017-2018 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from kube_obj import KubeObj, order_dict
from kube_types import *


class StorageClass(KubeObj):
    apiVersion = 'storage.k8s.io/v1beta1'
    kind = 'StorageClass'
    kubectltype = 'storageclass'

    _defaults = {
        'provisioner': None,
        'parameters': {},
    }

    _types = {
        'provisioner': String,
        'parameters': Map(String, String),
    }

    def render(self):
        if len(self._data['parameters']) == 0:
            return None
        if self._data['provisioner'] is None:
            return None
        return order_dict({
            'metadata': {'name': self._data['name']},
            'provisioner': self._data['provisioner'],
            'parameters': self._data['parameters'],
            }, ('metadata', 'provisioner', 'parameters'))
