# (c) Copyright 2017-2018 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from collections import OrderedDict
import sys
import traceback
from kube_obj import KubeObj, KubeSubObj, order_dict
from kube_types import *
from user_error import UserError
from . import router
from .pod import PodTemplateSpec


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
        'targetPort': OneOf(Positive(NonZero(Integer)), Identifier),
        }

    def render(self):
        return self.renderer(order=('name', 'protocol', 'port'))


class Service(KubeObj):
    apiVersion = 'v1'
    kind = 'Service'
    kubectltype = 'service'
    _output_order = 120

    _defaults = {
        'sessionAffinity': None,
        'ports': [],
        'selector': {},
        }

    _types = {
        'sessionAffinity': Nullable(Enum('ClientIP', 'None')),
        'ports': NonEmpty(List(ServicePort)),
        'selector': NonEmpty(Map(String, String)),
        }

    _exclude = {
        '.spec.type': True,
        '.status': True,
        }

    _parse_default_base = ('spec',)

    def find_subparser(self, doc):
        if 'spec' in doc and 'type' in doc['spec'] and doc['spec']['type'] == 'ClusterIP':
            return ClusterIPService
        if 'spec' in doc and 'type' in doc['spec'] and doc['spec']['type'] == 'LoadBalancer':
            return AWSLoadBalancerService

    def xf_selector(self, v):
        if isinstance(v, PodTemplateSpec):
            return order_dict(v.labels, ())

        return v

    def xf_ports(self, v):
        if v is None:
            return v

        if not isinstance(v, list):
            v = [v]

        ret = []

        for vv in v:
            if Integer().do_check(vv, None):
                ret.append(ServicePort(name='{}-tcp'.format(vv), port=vv, targetPort=vv, protocol='TCP'))
            elif String().do_check(vv, None):
                if '/' in vv:
                    port, proto = vv.split('/', 1)
                else:
                    port = vv
                    proto = 'tcp'

                if '->' in port:
                    sport, dport = port.split('->', 1)
                else:
                    sport = port
                    dport = port
                ret.append(ServicePort(name='{}-{}'.format(sport, proto.lower()), port=int(dport),
                                       targetPort=int(sport), protocol=proto.upper()))
            else:
                ret.append(vv)

        return ret

    def internal_addr(self, *args, **kwargs):
        caller_file, caller_line, caller_fn = traceback.extract_stack(limit=2)[0][0:3]
        print("internal_addr() called on non-ClusterIPService at {}:{} in {} - check output".format(
                  caller_file, caller_line, caller_fn,
                  ), file=sys.stderr)
        return None


class ClusterIPService(Service):
    _defaults = {
        'clusterIP': None,
        }

    _types = {
        'clusterIP': Nullable(IPv4),
        }

    def route(self, port=None, name=None, host=None):
        ports = self.xf_ports(self._data['ports'])
        if port is None and len(ports) == 1:
            port = ports[0]
        elif len(ports) == 0:
            raise UserError(ValueError("Can't create route on service with no ports!"))
        elif port is None:
            raise UserError(ValueError("Multiple ports available, pick one!"))
        elif Integer().do_check(port, None):
            for p in ports:
                if p._data['port'] == port or p._data['targetPort'] == port:
                    port = p
                    break
        elif String().do_check(port, None):
            for p in ports:
                if p._data['port'] == int(port) or p._data['targetPort'] == int(port):
                    port = p
                    break
                if p._data['name'] == port:
                    port = p
                    break

        if not isinstance(port, ServicePort):
            raise UserError(TypeError("Unknown specification for port {}, please specify something consistent".format(
                                      port)))

        return router.Route(port=router.RouteDestPort(targetPort=port._data['name']),
                            to=[router.RouteDestService(name=self.name)],
                            name=name, host=host)

    def internal_addr(self, port=None, scheme='http'):
        ports = self.xf_ports(self._data['ports'])
        if port is None and len(ports) == 1:
            port = ports[0]._data['port']
        if port is None or not Positive(NonZero(Integer)).do_check(port, None):
            return None
        if port not in list(map(lambda x: x._data['port'], ports)):
            return None

        ret = ''
        if scheme is not None:
            ret += scheme + '://'
        ret += self._data['name'] + '.' + self.namespace.name + '.svc.cluster.local'
        if scheme is None or scheme != 'http' or port != 80:
            ret += ':{}'.format(port)

        return ret

    def render(self):
        ret = self.renderer(order=('selector', 'ports'))
        del ret['name']
        spec = OrderedDict(type='ClusterIP')
        spec.update(ret)
        return {'metadata': {'name': self._data['name']}, 'spec': spec}


class AWSLoadBalancerService(Service):
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

    def parser_fixup(self):
        for i in ('aws-load-balancer-backend-protocol', 'aws-load-balancer-ssl-cert'):
            if 'service.beta.kubernetes.io/' + i in self.annotations:
                self._data[i] = self.annotations['service.beta.kubernetes.io/' + i]
                del self.annotations['service.beta.kubernetes.io/' + i]

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
