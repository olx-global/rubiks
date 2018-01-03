# (c) Copyright 2017-2018 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from kube_obj import KubeObj, KubeSubObj, order_dict
from kube_types import *
from user_error import UserError
from .role import User
from .service_account import ServiceAccount


class SCCSELinux(KubeSubObj):
    _defaults = {
        'strategy': None,
        'level': None,
        'type': None,
        'role': None,
        'user': None,
        }

    _types = {
        'strategy': Nullable(Enum('MustRunAs', 'RunAsAny')),
        'level': Nullable(String),
        'type': Nullable(String),
        'role': Nullable(String),
        'user': Nullable(String),
        }

    _parse_default_base = ('seLinuxOptions',)

    _parse = {
        'strategy': ('type',),
        }

    def render(self):
        ret = self.renderer()
        if len(ret) == 0:
            return None

        rret = {}
        if 'strategy' in ret:
            rret['type'] = ret['strategy']
            del ret['strategy']

        if len(ret) != 0:
            rret['seLinuxOptions'] = ret

        return rret


class SCCGroupRange(KubeSubObj):
    _defaults = {
        'min': 0,
        'max': 0,
        }

    _types = {
        'min': Positive(NonZero(Integer)),
        'max': Positive(NonZero(Integer)),
        }

    def render(self):
        return self.renderer()


class SCCGroups(KubeSubObj):
    _defaults = {
        'type': None,
        'ranges': [],
        }

    _types = {
        'type': Nullable(Enum('MustRunAs', 'RunAsAny')),
        'ranges': Nullable(List(SCCGroupRange)),
        }

    def render(self):
        return self.renderer(return_none=True)


class SCCRunAsUser(KubeSubObj):
    _defaults = {
        'type': None,
        'uid': None,
        'uidRangeMin': None,
        'uidRangeMax': None,
        }

    _types = {
        'type': Enum('MustRunAs', 'RunAsAny', 'MustRunAsRange', 'MustRunAsNonRoot'),
        'uid': Nullable(Positive(NonZero(Integer))),
        'uidRangeMin': Nullable(Positive(NonZero(Integer))),
        'uidRangeMax': Nullable(Positive(NonZero(Integer))),
        }

    def render(self):
        return self.renderer()


class SecurityContextConstraints(KubeObj):
    apiVersion = 'v1'
    kind = 'SecurityContextConstraints'
    kubectltype = 'scc'
    _uses_namespace = False
    _always_regenerate = True
    _output_order = 10

    _defaults = {
        'allowHostDirVolumePlugin': False,
        'allowHostIPC': False,
        'allowHostNetwork': False,
        'allowHostPID': False,
        'allowHostPorts': False,
        'allowPrivilegedContainer': False,
        'readOnlyRootFilesystem': False,

        'seLinuxContext': None,
        'seccompProfiles': None,
        'runAsUser': None,
        'fsGroup': None,
        'supplementalGroups': None,

        'volumes': ['configMap', 'emptyDir', 'secret'],
        'priority': None,

        'allowedCapabilities': None,
        'defaultAddCapabilities': None,
        'requiredDropCapabilities': None,

        'users': [],
        'groups': [],
        }

    _types = {
        'allowHostDirVolumePlugin': Boolean,
        'allowHostIPC': Boolean,
        'allowHostNetwork': Boolean,
        'allowHostPID': Boolean,
        'allowHostPorts': Boolean,
        'allowPrivilegedContainer': Boolean,
        'readOnlyRootFilesystem': Boolean,

        'seLinuxContext': Nullable(SCCSELinux),
        'seccompProfiles': Nullable(List(String)),
        'runAsUser': Nullable(SCCRunAsUser),
        'fsGroup': Nullable(SCCGroups),
        'supplementalGroups': Nullable(SCCGroups),

        'volumes': List(Enum('configMap', 'downwardAPI', 'emptyDir', 'hostPath', 'nfs', 'persistentVolumeClaim', 'secret', '*')),
        'priority': Nullable(Positive(Integer)),

        'allowedCapabilities': Nullable(List(String)),
        'defaultAddCapabilities': Nullable(List(String)),
        'requiredDropCapabilities': Nullable(List(String)),

        'users': List(SystemIdentifier),
        'groups': List(SystemIdentifier),
        }

    def add_user(self, v):
        if isinstance(v, User) and v.name not in self._data['users']:
            self._data['users'].append(v.name)

        elif isinstance(v, ServiceAccount):
            sa_name = 'system:serviceaccount:' + v.namespace.name + ':' + v.name
            if sa_name not in self._data['users']:
                self._data['users'].append(sa_name)

        elif SystemIdentifier.do_check(v, None):
            self._data['users'].append(v)

        else:
            raise UserError(TypeError("can't add {} to users".format(repr(v))))

    def render(self):
        ret = self.renderer()
        for cap in ('allowedCapabilities', 'defaultAddCapabilities', 'requiredDropCapabilities', 'priority'):
            if cap not in ret:
                ret[cap] = None
        del ret['name']
        ret['metadata'] = {'name': self._data['name']}
        return order_dict(dict(ret), ('metadata',))
