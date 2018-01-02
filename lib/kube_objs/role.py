# (c) Copyright 2017-2018 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from kube_obj import KubeObj, KubeSubObj, order_dict
from kube_types import *
from .service_account import ServiceAccount


class PolicyRule(KubeSubObj):
    _defaults = {
        'resourceNames': [],
        'resources': [],
        'verbs': [],
        'apiGroups': [""],
        'attributeRestrictions': None,
        'nonResourceURLs': [],
        }

    _types = {
        'resourceNames': Nullable(List(String)),
        'resources': NonEmpty(List(NonEmpty(String))),
        'verbs': NonEmpty(List(Enum('get', 'list', 'create', 'update', 'delete', 'deletecollection', 'watch'))),
        'apiGroups': NonEmpty(List(String)),
        'attributeRestrictions': Nullable(String),
        'nonResourceURLs': Nullable(List(String)),
        }

    def render(self):
        ret = self.renderer(zlen_ok=('attributeRestrictions',))
        if 'attributeRestrictions' not in ret or ret['attributeRestrictions'] == '':
            ret['attributeRestrictions'] = None
        return ret


class RoleBase(KubeObj):
    _defaults = {
        'rules': [],
        }

    _types = {
        'rules': NonEmpty(List(PolicyRule)),
        }

    def render(self):
        ret = self.renderer()
        return {'metadata': {'name': self._data['name']}, 'rules': ret['rules']}


class ClusterRole(RoleBase):
    apiVersion = 'v1'
    kind = 'ClusterRole'
    kubectltype = 'clusterrole'
    _uses_namespace = False


class Role(RoleBase):
    apiVersion = 'v1'
    kind = 'Role'
    kubectltype = 'role'


class User(KubeObj):
    apiVersion = 'v1'
    kind = 'User'
    kubectltype = 'user'
    _uses_namespace = False

    _defaults = {
        'fullName': None,
        'identities': [],
        }

    _types = {
        'fullName': Nullable(String),
        'identities': NonEmpty(List(NonEmpty(String))),
        }

    def render(self):
        ret = self.renderer()
        return {'metadata': {'name': self._data['name']},
                'fullName': ret['fullName'], 'identities': ret['identities'], 'groups': None}


class Group(KubeObj):
    apiVersion = 'v1'
    kind = 'Group'
    kubectltype = 'group'
    _uses_namespace = False

    _defaults = {
        'users': [],
        }

    _types = {
        'users': NonEmpty(List(Identifier)),
        }

    def render(self):
        ret = self.renderer()
        return {'metadata': {'name': self._data['name']}, 'users': ret['users']}


class RoleSubject(KubeSubObj):
    _defaults = {
        'name': None,
        'kind': None,
        'ns': None,
        }

    _types = {
        'name': Nullable(SystemIdentifier),
        'kind': Nullable(CaseIdentifier),
        'ns': Nullable(Identifier),
        }

    def render(self):
        ret = self.renderer(order=('name', 'kind', 'ns'))
        if 'ns' in ret:
            ret['namespace'] = ret['ns']
            del ret['ns']
        return ret


class RoleRef(KubeSubObj):
    _defaults = {
        'name': None,
        }

    _types = {
        'name': Nullable(SystemIdentifier),
        }

    def render(self):
        return self.renderer()


class RoleBindingBase(KubeObj):
    _always_regenerate = True

    _defaults = {
        'roleRef': RoleRef(),
        'subjects': [],
        }

    _types = {
        'roleRef': RoleRef,
        'subjects': NonEmpty(List(RoleSubject)),
        }

    def xf_roleRef(self, v):
        if isinstance(v, Role) and v.namespace == self.namespace:
            return RoleRef(name=v.name)
        elif isinstance(v, ClusterRole):
            return RoleRef(name=v.name)
        elif String().do_check(v, None):
            return RoleRef(name=v)
        return v

    def xf_subjects(self, v):
        if isinstance(v, KubeObj) or String().do_check(v, None):
            v = [v]

        ret = []
        for vv in v:
            if isinstance(vv, (ServiceAccount, User, Group)):
                if vv._uses_namespace:
                    ret.append(RoleSubject(name=vv.name, kind=vv.kind, ns=vv.namespace.name))
                else:
                    ret.append(RoleSubject(name=vv.name, kind=vv.kind))
            elif String().do_check(vv, None):
                if vv.startswith('system:serviceaccounts:'):
                    ret.append(RoleSubject(name=vv, kind='SystemGroup'))
                elif vv.startswith('system:serviceaccount:'):
                    svv = vv.split(':', 3)
                    ret.append(RoleSubject(name=svv[4], kind='ServiceAccount', ns=svv[3]))
                else:
                    ret.append(RoleSubject(name=vv, kind='User'))
            else:
                ret.append(vv)
        return ret

    def render(self):
        ret = self.renderer()
        return {'metadata': {'name': self._data['name']},
                'roleRef': ret['roleRef'], 'subjects': ret['subjects'], 'userNames': None, 'groupNames': None}


class ClusterRoleBinding(RoleBindingBase):
    apiVersion = 'v1'
    kind = 'ClusterRoleBinding'
    kubectltype = 'clusterrolebinding'
    _uses_namespace = False


class RoleBinding(RoleBindingBase):
    apiVersion = 'v1'
    kind = 'RoleBinding'
    kubectltype = 'rolebinding'
