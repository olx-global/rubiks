# (c) Copyright 2017 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from collections import OrderedDict
import copy

from kube_obj import KubeBaseObj, KubeSubObj, order_dict
from kube_types import *


class Memory(String):
    def do_check(self, value, path):
        if not String.do_check(self, value, path):
            return False
        if not value.endswith('ki', 'Mi', 'Gi'):
            return False
        try:
            return float(value[:-2].strip()) >= 0.0
        except ValueError:
            return False


class ContainerPort(KubeSubObj):
    _defaults = {
        'containerPort': 80,
        'protocol': 'TCP',
        }

    _types = {
        'containerPort': Positive(NonZero(Integer)),
        'protocol': Enum('TCP', 'UDP'),
        }

    def render(self):
        return order_dict(self._data, ('containerPort', 'protocol'))


class ContainerResourceEachSpec(KubeSubObj):
    _defaults = {
        'cpu': None,
        'memory': None,
        }

    _types = {
        'cpu': Nullable(Positive(NonZero(Number))),
        'memory': Nullable(Memory),
        }

    def render(self):
        ret = OrderedDict()

        for i in ('cpu', 'memory'):
            if self._data[i] is not None:
                ret[i] = self._data[i]

        if len(ret) == 0:
            return None

        return ret


class ContainerResourceSpec(KubeSubObj):
    _defaults = {
        'requests': ContainerResourceEachSpec(),
        'limits': ContainerResourceEachSpec(),
        }

    def render(self):
        ret = OrderedDict()

        for i in ('requests', 'limits'):
            if self._data[i] is not None:
                r = self._data[i].do_render()
                if r is not None:
                    ret[i] = r

        if len(ret) == 0:
            return None

        return ret


class ContainerEnvBaseSpec(KubeSubObj):
    _defaults = {
        'name': '',
        }

    _types = {
        'name': NonEmpty(String),
        }


class ContainerEnvSpec(ContainerEnvBaseSpec):
    _defaults = {
        'value': '',
        }

    _types = {
        'value': NonEmpty(String),
        }

    def render(self):
        ret = OrderedDict()
        ret['name'] = self._data['name']
        ret['value'] = self._data['value']
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

    def render(self):
        ret = OrderedDict()
        ret['name'] = self._data['name']
        sret = OrderedDict()
        sret['key'] = self._data['key']
        sret['name'] = self._data['secret_name']
        ret['valueFrom'] = {'secretKeyRef': sret}
        return ret


class ContainerVolumeMountSpec(KubeSubObj):
    _defaults = {
        'name': '',
        'path': '',
        'readOnly': None,
        }

    _types = {
        'name': Identifier,
        'path': NonEmpty(Path),
        'readOnly': Nullable(Boolean),
        }

    def render(self):
        ret = OrderedDict(name=self._data['name'])
        ret['mountPath'] = self._data['path']
        if self._data['readOnly'] is not None:
            ret['readOnly'] = self._data['readOnly']
        return ret


class ContainerProbeBaseSpec(KubeSubObj):
    _defaults = {
        'initialDelaySeconds': 0,
        'periodSeconds': 1,
        'failureThreshold': 3,
        }

    _types = {
        'initialDelaySeconds': Positive(Integer),
        'periodSeconds': Positive(NonZero(Integer)),
        'failureThreshold': Positive(NonZero(Integer)),
        }

    def render(self):
        ret = order_dict({
            'initialDelaySeconds': self._data['initialDelaySeconds'],
            'periodSeconds': self._data['periodSeconds'],
            'failureThreshold': self._data['failureThreshold'],
            }, ('initialDelaySeconds', 'periodSeconds', 'failureThreshold'))

        if not hasattr(self, 'render_check'):
            return None

        r = self.render_check()
        if r is None:
            return None

        ret.update(r)
        return ret


class ContainerProbeHTTPSpec(ContainerProbeBaseSpec):
    _defaults = {
        'path': '',
        'port': 80,
        }

    _types = {
        'path': NonEmpty(Path),
        'port': Positive(NonZero(Integer)),
        }

    def render_check(self):
        if port == 0:
            return None
        return {'httpGet': {'path': self._data['path'], 'port': self._data['port']}}


class SecurityContext(KubeSubObj):
    _defaults = {
        'privileged': None,
        }

    _types = {
        'privileged': Nullable(Boolean),
        }

    def render_check(self):
        ret = {}
        if self._data['privileged'] is None:
            ret['privileged'] = self._data['privileged']
        return ret

class ContainerSpec(KubeSubObj):
    identifier = 'name'

    _defaults = {
        'image': '',
        'command': None,
        'env': {},
        'imagePullPolicy': None,
        'livenessProbe': None,
        'ports': [],
        'readinessProbe': None,
        'resources': ContainerResourceSpec(),
        'securityContext': None,
        'terminationMessagePath': None,
        'volumeMounts': [],
        }

    _types = {
        'image': NonEmpty(String),
        'command': Nullable(List(String)),
        'env': Nullable(Map(String, ContainerEnvBaseSpec)),
        'imagePullPolicy': Nullable(Enum('Always', 'IfNotPresent')),
        'livenessProbe': Nullable(ContainerProbeBaseSpec),
        'ports': Nullable(List(ContainerPort)),
        'readinessProbe': Nullable(ContainerProbeBaseSpec),
        'resources': Nullable(ContainerResourceSpec),
        'securityContext': Nullable(SecurityContext),
        'terminationMessagePath': Nullable(NonEmpty(Path)),
        'volumeMounts': Nullable(List(ContainerVolumeMountSpec)),
        }

    def render(self):
        ret = copy.copy(self._data)

        for k in self._data:
            if self._data[k] is None:
                del ret[k]

        if len(ret['command']) > 0:
            cmd = ret['command']
            ret['command'] = cmd[0]
            ret['args'] = cmd[1:]
        else:
            del ret['command']

        def _render(x):
            if isinstance(x, KubeBaseObj):
                return x.do_render()
            return x

        for i in ('env', 'ports', 'volumeMounts'):
            if i not in ret:
                continue
            if hasattr(ret[i], 'keys'):
                nkeys = set()
                for k in ret[i].keys():
                    ret[i][k] = _render(ret[i][k])
                    if ret[i][k] is None:
                        nkeys.add(k)
                for k in nkeys:
                    del ret[i][k]
            else:
                ret[i] = list(filter(lambda x: x is not None, map(_render, ret[i])))

            if len(ret[i]) == 0:
                del ret[i]

        for i in ('imagePullPolicy', 'livenessProbe', 'readinessProbe', 'terminationMessagePath', 'securityContext'):
            if i not in ret:
                continue
            ret[i] = _render(ret[i])
            if ret[i] is None:
                del ret[i]

        if ret['resources'] is not None:
            ret['resources'] = ret['resources'].do_render()

        if ret['resources'] is None:
            del ret['resources']

        return order_dict(ret, ('name', 'image', 'command', 'args', 'env', 'ports'))


class PodVolumeBaseSpec(KubeSubObj):
    _defaults = {
        'name': '',
        }

    _types = {
        'name': Identifier,
        }


class PodVolumeHostSpec(PodVolumeBaseSpec):
    _defaults = {
        'path': '',
        }

    _types = {
        'name': Identifier,
        }

    def render(self):
        ret = OrderedDict(name=self._data['name'])
        ret['hostPath'] = {'path': self._data['path']}
        return ret


class PodVolumeConfigMapSpec(PodVolumeBaseSpec):
    _defaults = {
        'defaultMode': None,
        'map_name': '',
        'item_map': {},
        }

    _types = {
        'defaultMode': Nullable(Positive(Integer)),
        'map_name': Identifier,
        'item_map': Nullable(Map(String, String)),
        }

    def render(self):
        ret = OrderedDict(name=self._data['name'])
        ret['configMap'] = OrderedDict(name=self._data['map_name'])

        if self._data['defaultMode'] is not None:
            ret['configMap']['defaultMode'] = int('{:o}'.format(self._data['defaultMode']), 10)

        if len(self._data['item_map']) != 0:
            ret['configMap']['items'] = []
            for k in sorted(self._data['item_map'].keys()):
                r = OrderedDict(key=k)
                r['path'] = self._data['item_map'][k]
                ret['configMap']['items'].append(r)

        return ret


class PodVolumeSecretSpec(PodVolumeBaseSpec):
    _defaults = {
        'defaultMode': None,
        'secret_name': '',
        'item_map': {},
        }

    _types = {
        'defaultMode': Nullable(Positive(Integer)),
        'secret_name': Identifier,
        'item_map': Nullable(Map(String, String)),
        }

    def render(self):
        ret = OrderedDict(name=self._data['name'])
        ret['secret'] = OrderedDict(secretName=self._data['secret_name'])

        if self._data['defaultMode'] is not None:
            ret['secret']['defaultMode'] = int('{:o}'.format(self._data['defaultMode']), 10)

        if len(self._data['item_map']) != 0:
            ret['secret']['items'] = []
            for k in sorted(self._data['item_map'].keys()):
                r = OrderedDict(key=k)
                r['path'] = self._data['item_map'][k]
                ret['secret']['items'].append(r)

        return ret


class PodImagePullSecret(KubeSubObj):
    _defaults = {
        'name': '',
        }

    _types = {
        'name': Identifier,
        }

    def render(self):
        return {'name': self._data['name']}


class PodTemplateSpec(KubeSubObj):
    has_metadata = True
    _defaults = {
        'name': None,
        'containers': [],
        'dnsPolicy': None,
        'imagePullSecrets': [],
        'restartPolicy': None,
        'securityContext': None,
        'terminationGracePeriodSeconds': None,
        'volumes': []
        }

    _types = {
        'name': Nullable(Identifier),
        'containers': NonEmpty(List(ContainerSpec)),
        'dnsPolicy': Nullable(Enum('ClusterFirst')),
        'imagePullSecrets': Nullable(List(PodImagePullSecret)),
        'restartPolicy': Nullable(Enum('Always')),
        'securityContext': Nullable(SecurityContext),
        'terminationGracePeriodSeconds': Nullable(Positive(Integer)),
        'volumes': Nullable(List(PodVolumeBaseSpec)),
        }

    def render(self):
        ret = copy.copy(self._data)

        for k in self._data:
            if self._data[k] is None:
                del ret[k]

        del ret['name']

        def _render(x):
            if isinstance(x, KubeBaseObj):
                return x.do_render()
            return x

        for k in ('containers', 'imagePullSecrets', 'volumes'):
            if k not in ret:
                continue

            ret[k] = list(filter(lambda x: x is not None, map(_render, ret[k])))

            if len(ret[k]) == 0:
                del ret[k]

        if self._data['name'] is not None:
            return {'metadata': {'labels': {'name': self._data['name']}}, 'spec': order_dict(ret, ('containers',))}
        return {'spec': order_dict(ret, ('containers',))}
