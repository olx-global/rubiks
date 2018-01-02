# (c) Copyright 2017-2018 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from collections import OrderedDict
from kube_obj import KubeObj, KubeSubObj, order_dict
from kube_types import *


class RouteDest(KubeSubObj):
    _defaults = {
        'weight': 100,
        }

    _types = {
        'weight': Positive(NonZero(Integer)),
        }


class RouteDestService(RouteDest):
    _defaults = {
        'name': None,
        }

    _types = {
        'name': Identifier,
        }

    def render(self):
        ret = self.renderer(order=('name',))
        spec = OrderedDict(kind='Service')
        spec.update(ret)
        return spec


class RouteDestPort(KubeSubObj):
    _defaults = {
        'targetPort': None,
        }

    _types = {
        'targetPort': Identifier,
        }

    def render(self):
        return self.renderer()


class RouteTLS(KubeSubObj):
    _defaults = {
        'insecureEdgeTerminationPolicy': 'Redirect',
        'termination': 'edge',
        'caCertificate': None,
        'certificate': None,
        'destinationCACertificate': None,
        'key': None,
        }

    _types = {
        'insecureEdgeTerminationPolicy': Enum('Allow', 'Disable', 'Redirect'),
        'termination': Enum('edge', 'reencrypt', 'passthrough'),
        'caCertificate': Nullable(NonEmpty(String)),
        'certificate': Nullable(NonEmpty(String)),
        'destinationCACertificate': Nullable(NonEmpty(String)),
        'key': Nullable(NonEmpty(String)),
        }

    def render(self):
        return self.renderer()


class Route(KubeObj):
    apiVersion = 'v1'
    kind = 'Route'
    kubectltype = 'route'

    _defaults = {
        'host': None,
        'to': [],
        'tls': None,
        'port': RouteDestPort(),
        'wildcardPolicy': 'None',
        }

    _types = {
        'host': Domain,
        'to': NonEmpty(List(RouteDest)),
        'tls': Nullable(RouteTLS),
        'port': RouteDestPort,
        'wildcardPolicy': Enum('Subdomain', 'None'),
        }

    def render(self):
        spec = self.renderer(order=('host', 'to', 'port'))
        if len(spec['to']) > 1:
            spec['alternateBackends'] = spec['to'][1:]
        spec['to'] = spec['to'][0]
        del spec['name']
        return {'metadata': {'name': self._data['name']}, 'spec': spec}
