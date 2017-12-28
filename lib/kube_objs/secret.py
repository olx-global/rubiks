# (c) Copyright 2017 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import base64
from collections import OrderedDict
import json

from kube_obj import KubeObj
from kube_types import *

class Secret(KubeObj):
    apiVersion = 'v1'
    kind = 'Secret'
    kubectltype = 'secret'

    _defaults = {
        'type': 'Opaque',
        'secrets': {},
        }

    _types = {
        'type': NonEmpty(String),
        'secrets': Map(String, String),
        }

    def render(self):
        if len(self._data['secrets']) == 0:
            return None
        secrets = {}
        for s in self._data['secrets']:
            try:
                secrets[s] = base64.b64encode(self._data['secrets'][s]).decode('utf8')
            except TypeError:
                secrets[s] = base64.b64encode(self._data['secrets'][s].encode('utf8')).decode('utf8')
        return {'metadata': {'name': self.name}, 'type': self._data['type'], 'data': secrets}

class DockerCredentials(Secret):
    _defaults = {
        'type': 'kubernetes.io/dockercfg',
        'secrets': {'.dockercfg': ''},
        'dockers': {},
    }

    _types = {
        'dockers': Map(String, Map(String, String)),
        }

    def render(self):
        if len(self._data['dockers']) == 0:
            return None

        ret = OrderedDict()
        for k in sorted(self._data['dockers'].keys()):
            v = self._data['dockers'][k]
            if 'username' in v and 'password' in v and 'email' in v and 'auth' in v:
                ret[k] = OrderedDict()
                for kk in ('username', 'password', 'email', 'auth'):
                    ret[k][kk] = v[kk]
        self._data['secrets']['.dockercfg'] = json.dumps(ret, separators=(',',':'))

        return Secret.render(self)
