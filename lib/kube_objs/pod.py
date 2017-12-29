# (c) Copyright 2017 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from collections import OrderedDict
import copy

from kube_obj import KubeBaseObj, KubeSubObj, order_dict
from kube_types import *
from .service_account import ServiceAccount
from .secret import Secret, DockerCredentials


class Memory(String):
    def do_check(self, value, path):
        if not String.do_check(self, value, path):
            return False
        if not value.endswith('ki') and not value.endswith('Mi') and not value.endswith('Gi'):
            if not value.endswith('k') and not value.endswith('M') and not value.endswith('G'):
                return False
        try:
            if value.endswith('i'):
                return float(value[:-2].strip()) >= 0.0
            return float(value[:-1].strip()) >= 0.0
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
        'periodSeconds': None,
        'timeoutSeconds': None,
        'failureThreshold': None,
        }

    _types = {
        'initialDelaySeconds': Positive(Integer),
        'periodSeconds': Nullable(Positive(NonZero(Integer))),
        'timeoutSeconds': Nullable(Positive(NonZero(Integer))),
        'failureThreshold': Nullable(Positive(NonZero(Integer))),
        }

    @classmethod
    def is_abstract_type(cls):
        return not hasattr(cls, 'render_check')

    def render(self):
        ret = order_dict({
            'initialDelaySeconds': self._data['initialDelaySeconds'],
            'timeoutSeconds': self._data['timeoutSeconds'],
            'periodSeconds': self._data['periodSeconds'],
            'failureThreshold': self._data['failureThreshold'],
            }, ('initialDelaySeconds', 'timeoutSeconds', 'periodSeconds', 'failureThreshold'))

        if not hasattr(self, 'render_check'):
            return None

        r = self.render_check()
        if r is None:
            return None

        ret.update(r)
        return ret


class ContainerProbeTCPPortSpec(ContainerProbeBaseSpec):
    _defaults = {
        'port': 80,
        }

    _types = {
        'port': Positive(NonZero(Integer)),
        }

    def render_check(self):
        ret = self.renderer()
        if ret['port'] == 0:
            return None
        return {'tcpSocket': ret}


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
        'fsGroup': None,
        'privileged': None,
        'runAsNonRoot': None,
        'runAsUser': None,
        'supplementalGroups': None,
        }

    _types = {
        'fsGroup': Nullable(Integer),
        'privileged': Nullable(Boolean),
        'runAsNonRoot': Nullable(Boolean),
        'runAsUser': Nullable(Integer),
        'supplementalGroups': Nullable(List(Integer)),
        }

    def render(self):
        return self.renderer()


class LifeCycleProbe(KubeSubObj):
    pass


class LifeCycleExec(LifeCycleProbe):
    _defaults = {
        'command': [],
        }

    _types = {
        'command': NonEmpty(List(String)),
        }

    def render(self):
        return {'exec': self.renderer()}


class LifeCycleHttp(LifeCycleProbe):
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

    def render(self):
        ret = self.renderer(order=('scheme', 'port', 'path'))
        if ret['port'] == 0:
            return None
        return {'httpGet': ret}


class LifeCycle(KubeSubObj):
    _defaults = {
        'preStop': None,
        'postStart': None,
        }

    _types = {
        'preStop': Nullable(LifeCycleProbe),
        'postStart': Nullable(LifeCycleProbe),
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
        'kind': None,
        'lifecycle': None,
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
        'kind': Nullable(Enum('DockerImage')),
        'lifecycle': Nullable(LifeCycle),
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
            ret['command'] = [cmd[0]]
            ret['args'] = cmd[1:]
        else:
            del ret['command']

        return order_dict(ret, ('name', 'kind', 'image', 'command', 'args', 'env', 'ports'))


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
        'path': String,
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
        'hostPID': None,
        'hostIPC': None,
        'hostNetwork': None,
        'imagePullSecrets': [],
        'nodeSelector': None,
        'restartPolicy': None,
        'securityContext': None,
        'serviceAccountName': None,
        'terminationGracePeriodSeconds': None,
        'volumes': []
        }

    _types = {
        'name': Nullable(Identifier),
        'containers': NonEmpty(List(ContainerSpec)),
        'dnsPolicy': Nullable(Enum('ClusterFirst')),
        'hostPID': Nullable(Boolean),
        'hostIPC': Nullable(Boolean),
        'hostNetwork': Nullable(Boolean),
        'imagePullSecrets': Nullable(List(PodImagePullSecret)),
        'nodeSelector': Nullable(Map(String, String)),
        'restartPolicy': Nullable(Enum('Always')),
        'securityContext': Nullable(SecurityContext),
        'serviceAccountName': Nullable(Identifier),
        'terminationGracePeriodSeconds': Nullable(Positive(Integer)),
        'volumes': Nullable(List(PodVolumeBaseSpec)),
        }

    _map = {
        'serviceAccount': 'serviceAccountName',
        }

    def xf_imagePullSecrets(self, v):
        if isinstance(v, DockerCredentials):
            return [PodImagePullSecret(v.name)]
        elif Identifier().do_check(v, None):
            return [PodImagePullSecret(v)]
        elif isinstance(v, list):
            ret = []
            for vv in v:
                if isinstance(vv, DockerCredentials):
                    ret.append(PodImagePullSecret(vv.name))
                elif Identifier().do_check(vv, None):
                    ret.append(PodImagePullSecret(vv))
                else:
                    ret.append(vv)
            return ret
        return v

    def xf_serviceAccountName(self, v):
        if isinstance(v, ServiceAccount):
            return v.name
        return v

    def render(self):
        ret = self.renderer(zlen_ok=('securityContext',), order=('containers',), mapping={'name': None})
        if self._data['name'] is not None:
            return {'metadata': {'labels': {'name': self._data['name']}}, 'spec': ret}
        return {'spec': ret}
