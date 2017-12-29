# (c) Copyright 2017 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from collections import OrderedDict
from kube_obj import KubeObj, KubeSubObj, order_dict
from kube_types import *

class ServicePort(KubeSubObj):
    _defaults = {
        'name': None,
        'protocol': Enum('TCP', 'UDP'),
        'port': None,
        'targetPort': None,
        }

    _types = {
        'name': Nullable(Identifier),
        'protocol': Enum('TCP', 'UDP'),
        'port': Positive(NonZero(Integer)),
        'targetPort': Positive(NonZero(Integer)),
        }

    def render(self):
        return self.renderer(order=('name', 'protocol', 'port'))

class Service(KubeObj):
    apiVersion = 'v1'
    kind = 'Service'
    kubectltype = 'service'

    _defaults = {
        'sessionAffinity': None,
        'ports': [],
        'selector': {},
        }

    _types = {
        'sessionAffinity': Nullable(Boolean),
        'ports': NonEmpty(List(ServicePort)),
        'selector': NonEmpty(Map(String, String)),
        }

class ClusterIPService(Service):
    _defaults = {
        'clusterIP': None,
        }

    _types = {
        'clusterIP': Nullable(IPv4),
        }

    def render(self):
        ret = self.renderer(order=('selector', 'ports'))
        del ret['name']
        spec = OrderedDict(type='ClusterIP')
        spec.update(ret)
        return {'metadata': {'name': self._data['name']}, 'spec': spec}

class LoadBalancerService(Service):
    _defaults = {
        'aws-load-balancer-backend-protocol': None,
        'aws-load-balancer-ssl-cert': None,
        'externalTrafficPolicy': None,
        }

    _types = {
        'aws-load-balancer-backend-protocol': Nullable(Identifier),
        'aws-load-balancer-ssl-cert': Nullable(ARN),
        'externalTrafficPolicy': Nullable(Enum('Cluster', 'Local')),
        }

    def render(self):
        ret = self.renderer(order=('selector', 'ports'))
        del ret['name']

        aws_vars = set()
        for k in ret:
            if k.startswith('aws-'):
                self.annotations['service.beta.kubernetes.io/{}'.format(k)] = ret[k]
                aws_vars.add(k)

        for k in aws_vars:
            del ret[k]

        spec = OrderedDict(type='LoadBalancer')
        spec.update(ret)
        return {'metadata': {'name': self._data['name']}, 'spec': spec}
