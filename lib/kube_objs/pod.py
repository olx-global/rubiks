# (c) Copyright 2017-2018 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from collections import OrderedDict
import copy

from kube_obj import KubeBaseObj, KubeSubObj, order_dict
from kube_types import *
import_relative('environment', '*')
import_relative('service_account', 'ServiceAccount')
import_relative('secret', 'Secret', 'DockerCredentials')
import_relative('mixins', 'EnvironmentPreProcessMixin')


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
        'hostPort': None,
        'hostIP': None,
        'name': None,
        'protocol': 'TCP',
        }

    _types = {
        'containerPort': Positive(NonZero(Integer)),
        'hostPort': Nullable(Positive(NonZero(Integer))),
        'hostIP': Nullable(IP),
        'name': Nullable(String),
        'protocol': Enum('TCP', 'UDP'),
        }

    def render(self):
        return self.renderer(order=('name',))


class ContainerResourceEachSpec(KubeSubObj):
    _defaults = {
        'cpu': None,
        'memory': None,
        }

    _types = {
        'cpu': Nullable(Positive(NonZero(Number))),
        'memory': Nullable(Memory),
        }

    def xf_cpu(self, v):
        if String().do_check(v, None):
            if v.isdigit() or v.strip('0123456789') == '.':
                return float(v)
            elif v.endswith('m') and v[:-1].isdigit():
                return float(v[:-1]) / 1000
        return v

    def render(self):
        return self.renderer(order=('cpu', 'memory'), return_none=True)


class ContainerResourceSpec(KubeSubObj):
    _defaults = {
        'requests': ContainerResourceEachSpec(),
        'limits': ContainerResourceEachSpec(),
        }

    def render(self):
        return self.renderer(order=('requests', 'limits'), return_none=True)


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

    _parse = {
        'path': ('mountPath',),
        }

    def render(self):
        return self.renderer(order=('name', 'path', 'readOnly'), mapping={'path': 'mountPath'})


class ContainerProbeBaseSpec(KubeSubObj):
    _defaults = {
        'initialDelaySeconds': None,
        'periodSeconds': None,
        'timeoutSeconds': None,
        'failureThreshold': None,
        'successThreshold': None,
        }

    _types = {
        'initialDelaySeconds': Nullable(Positive(Integer)),
        'periodSeconds': Nullable(Positive(NonZero(Integer))),
        'timeoutSeconds': Nullable(Positive(NonZero(Integer))),
        'failureThreshold': Nullable(Positive(NonZero(Integer))),
        'successThreshold': Nullable(Positive(NonZero(Integer))),
        }

    @classmethod
    def is_abstract_type(cls):
        return not hasattr(cls, 'render_check')

    def find_subparser(self, doc):
        if 'tcpSocket' in doc:
            return ContainerProbeTCPPortSpec
        elif 'httpGet' in doc:
            return ContainerProbeHTTPSpec

    def render(self):
        ret = OrderedDict()
        for i in ('initialDelaySeconds', 'timeoutSeconds', 'periodSeconds', 'failureThreshold', 'successThreshold'):
            if self._data[i] is not None:
                ret[i] = self._data[i]

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

    _parse = {
        'port': ('tcpSocket', 'port'),
        }

    def xf_port(self, v):
        if String().do_check(v, None):
            try:
                return int(v)
            except:
                pass
        return v

    def render_check(self):
        if self._data['port'] == 0:
            return None
        return {'tcpSocket': {'port': self._data['port']}}


class ContainerProbeHTTPSpec(ContainerProbeBaseSpec):
    _defaults = {
        'host': None,
        'path': '',
        'port': 80,
        'scheme': None,
        }

    _types = {
        'host': Nullable(Domain),
        'path': NonEmpty(Path),
        'port': Positive(NonZero(Integer)),
        'scheme': Nullable(Enum('HTTP', 'HTTPS')),
        }

    _parse = {
        'host': ('httpGet', 'host'),
        'path': ('httpGet', 'path'),
        'port': ('httpGet', 'port'),
        'scheme': ('httpGet', 'scheme'),
        }

    def xf_port(self, v):
        if String().do_check(v, None):
            try:
                return int(v)
            except:
                pass
        return v

    def render_check(self):
        if self._data['port'] == 0:
            return None
        ret = OrderedDict()
        for r in ('scheme', 'host', 'port', 'path'):
            if self._data[r] is not None:
                ret[r] = self._data[r]
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
    def find_subparser(self, doc):
        if 'exec' in doc:
            return LifeCycleExec
        elif 'httpGet' in doc:
            return LifeCycleHTTP


class LifeCycleExec(LifeCycleProbe):
    _defaults = {
        'command': [],
        }

    _types = {
        'command': NonEmpty(List(String)),
        }

    _parse_default_base = ('exec',)

    def render(self):
        return {'exec': self.renderer()}


class LifeCycleHTTP(LifeCycleProbe):
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

    _parse_default_base = ('httpGet',)

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


class ContainerSpec(KubeSubObj, EnvironmentPreProcessMixin):
    identifier = 'name'

    _defaults = {
        'image': '',
        'command': None,
        'args': None,
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
        'args': Nullable(List(String)),
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

    def xf_env(self, v):
        return self.fix_environment(v)

    def xf_ports(self, v):
        if v is None:
            return v

        if not isinstance(v, list):
            v = [v]

        ret = []

        for vv in v:
            if Integer().do_check(vv, None):
                ret.append(ContainerPort(containerPort=vv, protocol='TCP'))
            elif String().do_check(vv, None):
                if '/' in vv:
                    port, proto = vv.split('/', 1)
                    ret.append(ContainerPort(containerPort=int(port), protocol=proto.upper()))
                else:
                    ret.append(ContainerPort(containerPort=int(vv), protocol='TCP'))
            else:
                ret.append(vv)

        return ret

    def xf_volumeMounts(self, v):
        if isinstance(v, dict):
            ret = []
            for vv in sorted(v.keys()):
                ret.append(ContainerVolumeMountSpec(name=vv, path=v[vv]))
            return ret
        return v

    def render(self):
        ret = self.renderer(zlen_ok=('securityContext',))

        if 'command' in ret and len(ret['command']) > 0:
            if 'args' not in ret or len(ret['args']) == 0:
                cmd = ret['command']
                ret['command'] = [cmd[0]]
                ret['args'] = cmd[1:]
        else:
            if 'command' in ret:
                del ret['command']

        return order_dict(ret, ('name', 'kind', 'image', 'command', 'args', 'env', 'ports'))


class PodVolumeBaseSpec(KubeSubObj):
    _defaults = {
        'name': '',
        }

    _types = {
        'name': Identifier,
        }

    def find_subparser(self, doc):
        if 'hostPath' in doc:
            return PodVolumeHostSpec
        elif 'configMap' in doc:
            return PodVolumeConfigMapSpec
        elif 'secret' in doc:
            return PodVolumeSecretSpec
        elif 'persistentVolumeClaim' in doc:
            return PodVolumePVCSpec
        elif 'emptyDir' in doc:
            return PodVolumeEmptyDirSpec


class PodVolumeHostSpec(PodVolumeBaseSpec):
    _defaults = {
        'path': '',
        }

    _types = {
        'path': String,
        }

    _parse = {
        'path': ('hostPath', 'path'),
        }

    def render(self):
        ret = self.renderer()
        r = OrderedDict(name=ret['name'])
        r['hostPath'] = {'path': ret['path']}
        return r


class PodVolumeItemMapper(PodVolumeBaseSpec):
    _defaults = {
        'item_map': {},
        }

    _types = {
        'item_map': Nullable(Map(String, String)),
        }

    def map_item_map(self, ret, base):
        if len(self._data['item_map']) != 0:
            ret[base]['items'] = []
            for k in sorted(self._data['item_map'].keys()):
                r = OrderedDict(key=k)
                r['path'] = self._data['item_map'][k]
                ret[base]['items'].append(r)

    def parser_fixup(self):
        if isinstance(self._data['item_map'], list):
            ret = {}
            for i in self._data['item_map']:
                if 'key' in i:
                    if 'path' in i:
                        ret[i['key']] = i['path']
                    else:
                        ret[i['key']] = None
                else:
                    print("Warning unparsed item_map: {}: {}".format(self.__class__.__name__, i), file=sys.stderr)
            self._data['item_map'] = ret


class PodVolumeConfigMapSpec(PodVolumeItemMapper):
    _defaults = {
        'defaultMode': None,
        'map_name': '',
        }

    _types = {
        'defaultMode': Nullable(Positive(Integer)),
        'map_name': Identifier,
        }

    _parse = {
        'defaultMode': ('configMap', 'defaultMode'),
        'map_name': ('configMap', 'name'),
        'item_map': ('configMap', 'items'),
        }

    def render(self):
        ret = OrderedDict(name=self._data['name'])
        ret['configMap'] = OrderedDict(name=self._data['map_name'])

        if self._data['defaultMode'] is not None:
            ret['configMap']['defaultMode'] = self._data['defaultMode']

        self.map_item_map(ret, 'configMap')

        return ret


class PodVolumeSecretSpec(PodVolumeItemMapper):
    _defaults = {
        'defaultMode': None,
        'secret_name': '',
        }

    _types = {
        'defaultMode': Nullable(Positive(Integer)),
        'secret_name': Identifier,
        }

    _parse = {
        'defaultMode': ('secret', 'defaultMode'),
        'secret_name': ('secret', 'secretName'),
        'item_map': ('secret', 'items'),
        }

    def render(self):
        ret = OrderedDict(name=self._data['name'])
        ret['secret'] = OrderedDict(secretName=self._data['secret_name'])

        if self._data['defaultMode'] is not None:
            ret['secret']['defaultMode'] = self._data['defaultMode']

        self.map_item_map(ret, 'secret')

        return ret


class PodVolumePVCSpec(PodVolumeBaseSpec):
    _defaults = {
        'claimName': '',
        }

    _types = {
        'claimName': Identifier,
        }

    _parse = {
        'claimName': ('persistentVolumeClaim', 'claimName'),
        }

    def render(self):
        ret = OrderedDict(name=self._data['name'])
        ret['persistentVolumeClaim'] = {'claimName': self._data['claimName']}
        return ret


class PodVolumeEmptyDirSpec(PodVolumeBaseSpec):
    _exclude = {
        '.emptyDir': True,
        }

    def render(self):
        return order_dict({'name': self._data['name'], 'emptyDir': {}}, ('name',))


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
        'restartPolicy': Nullable(Enum('Always', 'OnFailure', 'Never')),
        'securityContext': Nullable(SecurityContext),
        'serviceAccountName': Nullable(Identifier),
        'terminationGracePeriodSeconds': Nullable(Positive(Integer)),
        'volumes': Nullable(List(PodVolumeBaseSpec)),
        }

    _map = {
        'serviceAccount': 'serviceAccountName',
        }

    _parse_default_base = ('spec',)
    _parse = {
        'name': ('metadata', 'name'),
        }

    def xf_imagePullSecrets(self, v):
        if isinstance(v, DockerCredentials):
            return [PodImagePullSecret(name=v.name)]
        elif Identifier().do_check(v, None):
            return [PodImagePullSecret(name=v)]
        elif isinstance(v, list):
            ret = []
            for vv in v:
                if isinstance(vv, DockerCredentials):
                    ret.append(PodImagePullSecret(name=vv.name))
                elif Identifier().do_check(vv, None):
                    ret.append(PodImagePullSecret(name=vv))
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
            return {'metadata': {'name': self._data['name']}, 'spec': ret}
        return {'spec': ret}
