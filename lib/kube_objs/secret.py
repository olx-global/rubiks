# (c) Copyright 2017-2018 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from collections import OrderedDict

from kube_obj import KubeObj
from kube_types import *
from kube_vartypes import Base64, JSON


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
            secrets[s] = Base64(self._data['secrets'][s])
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
            if 'username' in v and 'password' in v and 'email' in v:
                ret[k] = OrderedDict()
                for kk in ('username', 'password', 'email'):
                    ret[k][kk] = v[kk]
                ret[k]['auth'] = Base64(v['username'] + ':' + v['password'])
        self._data['secrets']['.dockercfg'] = JSON(ret)

        return Secret.render(self)


class TLSCredentials(Secret):
    _defaults = {
        'type': 'kubernetes.io/tls',
        'secrets': {'tls.crt': '', 'tls.key': '', 'tls.pem': ''},
        'tls_cert': '',
        'tls_key': '',
    }

    _types = {
        'tls_cert': String,
        'tls_key': String,
        }

    def render(self):
        self._data['secrets'] = {'tls.crt': self._data['tls_cert'], 'tls.key': self._data['tls_key']}
        self._data['secrets']['tls.pem'] = \
            self._data['tls_cert'] + '\n' + self._data['tls_key'] + '\n'
        return Secret.render(self)
