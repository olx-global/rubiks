# (c) Copyright 2017-2018 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from kube_obj import KubeObj, KubeSubObj, order_dict
from kube_types import *
from .environment import *
from .pod import *
from .selectors import *
from .mixins import EnvironmentPreProcessMixin


class DCBaseUpdateStrategy(KubeSubObj):
    _defaults = {
        'annotations': {},
        'labels': {},
        'resources': ContainerResourceSpec(),
        'activeDeadlineSeconds': None,
        }

    _types = {
        'annotations': Map(String, String),
        'labels': Map(String, String),
        'resources': Nullable(ContainerResourceSpec),
        'activeDeadlineSeconds': Nullable(Positive(NonZero(Integer))),
        }

    _exclude = {
        '.type': True,
        }

    def find_subparser(self, doc):
        if 'type' in doc and doc['type'] == 'Recreate':
            return DCRecreateStrategy
        if 'type' in doc and doc['type'] == 'Rolling':
            return DCRollingStrategy
        if 'type' in doc and doc['type'] == 'Custom':
            return DCCustomStrategy


class DCCustomParams(KubeSubObj, EnvironmentPreProcessMixin):
    _defaults = {
        'image': '',
        'command': [],
        'environment': None,
        }

    _types = {
        'image': NonEmpty(String),
        'command': Nullable(List(String)),
        'environment': Nullable(List(ContainerEnvBaseSpec)),
        }

    def xf_environment(self, v):
        return self.fix_environment(self, v)

    def render(self):
        return self.renderer(order=('image', 'command', 'environment'))


class DCTagImages(KubeSubObj):
    _defaults = {
        'containerName': '',
        'toFieldPath': None,
        'toKind': None,
        'toName': None,
        'toNamespace': None,
        'toResourceVersion': None,
        'toUid': None,
        'toApiVersion': None,
        }

    _types = {
        'containerName': Identifier,
        'toFieldPath': Nullable(String),
        'toKind': Nullable(Enum('Deployment', 'DeploymentConfig', 'ImageStreamTag')),
        'toName': Nullable(Identifier),
        'toNamespace': Nullable(Identifier),
        'toResourceVersion': Nullable(String),
        'toUid': Nullable(String),
        'toApiVersion': Nullable(String),
        }

    _parse = {
        'containerName': ('containerName',),
        'toFieldPath': ('to', 'fieldPath'),
        'toKind': ('to', 'kind'),
        'toName': ('to', 'name'),
        'toNamespace': ('to', 'namespace'),
        'toResourceVersion': ('to', 'resourceVersion'),
        'toUid': ('to', 'uid'),
        'toApiVersion': ('to', 'apiVersion'),
        }

    def render(self):
        ret = OrderedDict(containerName=self._data['containerName'])
        include_to = False
        for t in self._data:
            if t.startswith('to') and self._data[t] is not None:
                include_to = True

        if include_to:
            ret['to'] = {}
            for t in self._data:
                if t.startswith('to') and self._data[t] is not None:
                    ret['to'][t[3].lower() + t[4:]] = self._data[t]

        return ret


class DCLifecycleNewPod(KubeSubObj, EnvironmentPreProcessMixin):
    _defaults = {
        'containerName': '',
        'command': [],
        'env': None,
        'volumes': None,
        }

    _types = {
        'containerName': Identifier,
        'command': NonEmpty(List(String)),
        'env': Nullable(List(ContainerEnvBaseSpec)),
        'volumes': Nullable(List(Identifier)),
        }

    def xf_env(self, v):
        return self.fix_environment(v)

    def render(self):
        return self.renderer(order=('container', 'command', 'env', 'volumes'))


class DCLifecycleHook(KubeSubObj):
    _defaults = {
        'tagImages': None,
        'execNewPod': None,
        'failurePolicy': 'Ignore',
        }

    _types = {
        'tagImages': Nullable(DCTagImages),
        'execNewPod': Nullable(DCLifecycleNewPod),
        'failurePolicy': Enum('Abort', 'Retry', 'Ignore'),
        }

    def render(self):
        ret = self.renderer(order=('failurePolicy',))
        if 'execNewPod' not in ret:
            ret['execNewPod'] = {}
        return ret


class DCRecreateParams(KubeSubObj):
    _defaults = {
        'pre': None,
        'mid': None,
        'post': None,
        'timeoutSeconds': None,
        }

    _types = {
        'pre': Nullable(DCLifecycleHook),
        'mid': Nullable(DCLifecycleHook),
        'post': Nullable(DCLifecycleHook),
        'timeoutSeconds': Nullable(Positive(NonZero(Integer))),
        }

    def render(self):
        return self.renderer(order=('pre', 'mid', 'post', 'timeoutSeconds'), return_none=True)


class DCRollingParams(KubeSubObj):
    _defaults = {
        'pre': None,
        'post': None,
        'maxSurge': None,
        'maxUnavailable': None,
        'intervalSeconds': None,
        'timeoutSeconds': None,
        'updatePeriodSeconds': None,
        }

    _types = {
        'pre': Nullable(DCLifecycleHook),
        'post': Nullable(DCLifecycleHook),
        'maxSurge': SurgeSpec,
        'maxUnavailable': SurgeSpec,
        'intervalSeconds': Nullable(Positive(NonZero(Integer))),
        'timeoutSeconds': Nullable(Positive(NonZero(Integer))),
        'updatePeriodSeconds': Nullable(Positive(NonZero(Integer))),
        }

    def do_validate(self):
        return SurgeCheck.validate(self._data['maxSurge'], self._data['maxUnavailable'])

    def render(self):
        return self.renderer(order=('pre', 'post', 'maxSurge', 'maxUnavailable'), return_none=True)


class DCRecreateStrategy(DCBaseUpdateStrategy):
    _defaults = {
        'customParams': None,
        'recreateParams': None,
        }

    _types = {
        'customParams': Nullable(DCCustomParams),
        'recreateParams': Nullable(DCRecreateParams),
        }

    def render(self):
        ret = OrderedDict(type='Recreate')
        ret.update(self.renderer())
        return ret


class DCRollingStrategy(DCBaseUpdateStrategy):
    _defaults = {
        'customParams': None,
        'rollingParams': None,
        }

    _types = {
        'customParams': Nullable(DCCustomParams),
        'rollingParams': Nullable(DCRollingParams),
        }

    def render(self):
        ret = OrderedDict(type='Rolling')
        ret.update(self.renderer())
        return ret


class DCCustomStrategy(DCBaseUpdateStrategy):
    _defaults = {
        'customParams': DCCustomParams(),
        }

    _types = {
        'customParams': DCCustomParams,
        }

    def render(self):
        ret = OrderedDict(type='Custom')
        ret.update(self.renderer())
        return ret


class DCTrigger(KubeSubObj):
    _exclude = {
        '.type': True,
        }

    def find_subparser(self, doc):
        if 'type' in doc and doc['type'] == 'ConfigChange':
            return DCConfigChangeTrigger
        if 'type' in doc and doc['type'] == 'ImageChange':
            return DCImageChangeTrigger


class DCConfigChangeTrigger(DCTrigger):
    def render(self):
        return {'type': 'ConfigChange'}


class DCImageChangeTrigger(DCTrigger):
    _default = {
        'automatic': None,
        'containerNames': [],
        'lastTriggeredImage': None,
        'fromName': '',
        'fromNamespace': None,
        'fromResourceVersion': None,
        'fromUid': None,
        'fromApiVersion': None,
        'fromFieldPath': None,
        'fromKind': None,
        }

    _type = {
        'automatic': Nullable(Boolean),
        'containerNames': Nullable(List(Identifier)),
        'lastTriggeredImage': Nullable(String),
        'fromName': Identifier,
        'fromNamespace': Nullable(Identifier),
        'fromResourceVersion': Nullable(String),
        'fromUid': Nullable(String),
        'fromApiVersion': Nullable(String),
        'fromFieldPath': Nullable(String),
        'fromKind': Nullable(Enum('ImageStreamTag')),
        }

    _parse_default_base = ('imageChangeParams',)

    _parse = {
        'fromName': ('imageChangeParams', 'from', 'name'),
        'fromNamespace': ('imageChangeParams', 'from', 'namespace'),
        'fromResourceVersion': ('imageChangeParams', 'from', 'resourceVersion'),
        'fromUid': ('imageChangeParams', 'from', 'uid'),
        'fromApiVersion': ('imageChangeParams', 'from', 'apiVersion'),
        'fromFieldPath': ('imageChangeParams', 'from', 'fieldPath'),
        'fromKind': ('imageChangeParams', 'from', 'kind'),
        }

    def render(self):
        ret = OrderedDict(type='ImageChange')
        ret['imageChangeParams'] = {'from': {}}

        for f in self._data:
            if self._data[f] is not None:
                if f.startswith('from'):
                    ret['imageChangeParams']['from'][f[5].lower() + f[6:]] = self._data[f]
                else:
                    ret['imageChangeParams'][f] = self._data[f]

        ret['imageChangeParams'] = order_dict(ret['imageChangeParams'], ())
        ret['imageChangeParams']['from'] = order_dict(ret['imageChangeParams']['from'], ())

        return ret


class DeploymentConfig(KubeObj):
    apiVersion = 'v1'
    kind = 'DeploymentConfig'
    kubectltype = 'deploymentconfig'

    _defaults = {
        'minReadySeconds': None,
        'paused': None,
        'pod_template': PodTemplateSpec(),
        'replicas': 1,
        'revisionHistoryLimit': None,
        'selector': None,
        'strategy': DCRollingStrategy(),
        'test': False,
        'triggers': [DCConfigChangeTrigger()],
        }

    _types = {
        'minReadySeconds': Nullable(Positive(NonZero(Integer))),
        'paused': Nullable(Boolean),
        'pod_template': PodTemplateSpec,
        'replicas': Positive(NonZero(Integer)),
        'revisionHistoryLimit': Nullable(Positive(NonZero(Integer))),
        'selector': Nullable(Map(String,String)),
        'strategy': DCBaseUpdateStrategy,
        'test': Boolean,
        'triggers': List(DCTrigger),
        }

    _parse_default_base = ('spec',)

    _parse = {
        'pod_template': ('spec', 'template'),
        }

    _exclude = {
        '.status': True,
        }

    def render(self):
        ret = self.renderer(mapping={'pod_template': 'template'}, order=('replicas', 'template'))
        del ret['name']
        return {'metadata': {'name': self._data['name']}, 'spec': ret}
