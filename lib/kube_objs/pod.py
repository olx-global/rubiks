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
        'name': None,
        'protocol': 'TCP',
        }

    _types = {
        'containerPort': Positive(NonZero(Integer)),
        'name': Nullable(String),
        'protocol': Enum('TCP', 'UDP'),
        }

    def render(self):
        ret = copy.deepcopy(self._data)
        if ret['name'] is None:
            del ret['name']
        return order_dict(ret, ('name', 'containerPort', 'protocol'))


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
        return self.renderer(order=('cpu', 'memory'), return_none=True)


class ContainerResourceSpec(KubeSubObj):
    _defaults = {
        'requests': ContainerResourceEachSpec(),
        'limits': ContainerResourceEachSpec(),
        }

    def render(self):
        return self.renderer(order=('requests', 'limits'), return_none=True)


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
        return self.renderer(order=('name', 'value'))


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
        return self.renderer(order=('name', 'path', 'readOnly'), mapping={'path': 'mountPath'})


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
        'scheme': None,
        }

    _types = {
        'path': NonEmpty(Path),
        'port': Positive(NonZero(Integer)),
        'scheme': Nullable(Enum('HTTP', 'HTTPS')),
        }

    def render_check(self):
        ret = self.renderer(order=('scheme', 'port', 'path'))
        if ret['port'] == 0:
            return None
        return {'httpGet': ret}


class SecurityContext(KubeSubObj):
    _defaults = {
        'privileged': None,
        }

    _types = {
        'privileged': Nullable(Boolean),
        }

    def render(self):
        return self.renderer()


class ContainerSpec(KubeSubObj):
    identifier = 'name'

    _defaults = {
        'image': '',
        'command': None,
        'env': [],
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
        'env': Nullable(List(ContainerEnvBaseSpec)),
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
        ret = self.renderer(zlen_ok=('securityContext',))

        if 'command' in ret and len(ret['command']) > 0:
            cmd = ret['command']
            ret['command'] = cmd[0]
            ret['args'] = cmd[1:]
        else:
            del ret['command']

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
        return self.renderer(mapping={'path': 'hostPath'}, order=('name',))


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
        ret = self.renderer(zlen_ok=('securityContext',), order=('containers',), mapping={'name': None})
        if self._data['name'] is not None:
            return {'metadata': {'labels': {'name': self._data['name']}}, 'spec': ret}
        return {'spec': ret}
