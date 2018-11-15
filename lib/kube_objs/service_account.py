# (c) Copyright 2017-2018 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from kube_obj import KubeObj, KubeSubObj
from kube_types import *
import_relative('secret', 'Secret')


class SASecretSubject(KubeSubObj):
    _defaults = {
        'name': None,
        'kind': None,
        'ns': None,
        }

    _types = {
        'name': Nullable(Identifier),
        'kind': Nullable(CaseIdentifier),
        'ns': Nullable(Identifier),
        }

    _parse = {
        'ns': ('namespace',),
        }

    def render(self):
        ret = self.renderer(order=('name', 'kind', 'ns'))
        if 'ns' in ret:
            ret['namespace'] = ret['ns']
            del ret['ns']
        return ret


class SAImgPullSecretSubject(KubeSubObj):
    _defaults = {
        'name': None,
    }

    _types = {
        'name': Identifier,
    }

    def render(self):
        return self.renderer()


class ServiceAccount(KubeObj):
    apiVersion = 'v1'
    kind = 'ServiceAccount'
    kubectltype = 'serviceaccount'
    _output_order = 15

    _defaults = {
        'imagePullSecrets': None,
        'secrets': None,
        }

    _types = {
        'imagePullSecrets': Nullable(List(SAImgPullSecretSubject)),
        'secrets': Nullable(List(SASecretSubject)),
        }

    def xf_secrets(self, v):
        if v is None:
            return v

        if isinstance(v, KubeObj) or String().do_check(v, None):
            v = [v]

        ret = []
        for vv in v:
            if vv is None:
                continue
            if isinstance(vv, Secret):
                ret.append(SASecretSubject(name=vv.name, ns=vv.namespace.name, kind=vv.kind))
            elif String().do_check(vv, None):
                ret.append(SASecretSubject(name=vv))
            else:
                ret.append(vv)

        return ret

    def xf_imagePullSecrets(self, v):
        if v is None:
            return v

        if isinstance(v, KubeObj) or String().do_check(v, None):
            v = [v]

        ret = []
        for vv in v:
            if vv is None:
                continue
            if isinstance(vv, Secret):
                ret.append(SAImgPullSecretSubject(name=vv.name))
            elif String().do_check(vv, None):
                ret.append(SAImgPullSecretSubject(name=vv))
            else:
                ret.append(vv)

        return ret

    def render(self):
        ret = self.renderer()
        del ret['name']
        ret['metadata'] = {'name': self._data['name']}
        return ret
