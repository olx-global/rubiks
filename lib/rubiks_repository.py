# (c) Copyright 2017-2018 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os

try:
    from ConfigParser import ConfigParser
except ImportError:
    from configparser import ConfigParser

import repository

class ClusterInfo(object):
    def __init__(self, name, cp, section):
        self.name = name
        self.prod_state = self._value(cp, section, 'prod_state', 'string', default='production')
        self.is_prod = self.prod_state == 'production'
        self.read_only = True

    def _value(self, cp, section, option, typ='string', default=None):
        if cp.has_section(section) and cp.has_option(section, option):
            if typ == 'string':
                return str(cp.get(section, option, raw=True))
            elif typ == 'int':
                try:
                    return int(cp.get(section, option, raw=True).strip())
                except ValueError:
                    pass
            elif typ == 'float':
                try:
                    return float(cp.get(section, option, raw=True))
                except ValueError:
                    pass
            elif typ == 'bool':
                v = cp.get(section, option, raw=True)
                c = v[0].lower()
                if v == '0' or v == '1':
                    return v == '1'
                elif c == 't' or c == 'f' or c == 'y' or c == 'n':
                    return c == 't' or c == 'y'
        return default

    def __setattr__(self, k, v):
        if not hasattr(self, 'read_only') or not self.read_only:
            return object.__setattr__(self, k, v)
        raise AttributeError("ClusterInfo object is read-only")

class RubiksRepository(repository.Repository):
    def __init__(self, *args, **kwargs):
        repository.Repository.__init__(self, *args, **kwargs)
        self.pythonpath = []
        self.clusters = {}
        self.is_openshift = False
        self.confidentiality_mode = None
        if os.path.exists(os.path.join(self.basepath, '.rubiks')):
            m_cp = ConfigParser()
            m_cp.read(os.path.join(self.basepath, '.rubiks'))

            if m_cp.has_section('layout'):
                if m_cp.has_option('layout', 'sources'):
                    self.sources = m_cp.get('layout', 'sources', raw=True)
                if m_cp.has_option('layout', 'outputs'):
                    self.outputs = m_cp.get('layout', 'outputs', raw=True)
                if m_cp.has_option('layout', 'pythonpath'):
                    self.pythonpath = list(map(lambda x: os.path.join(self.basepath, x.strip()),
                                               m_cp.get('layout', 'pythonpath', raw=True).split(',')))
                if m_cp.has_option('layout', 'confidentiality_mode'):
                    self.confidentiality_mode = m_cp.get('layout', 'confidentiality_mode', raw=True)
            for s in m_cp.sections():
                if s.startswith('cluster_'):
                    self.clusters[s[8:]] = ClusterInfo(s[8:], m_cp, s)

    def get_clusters(self):
        ret = []
        ret.extend(filter(lambda x: not self.clusters[x].is_prod, sorted(self.clusters.keys())))
        ret.extend(filter(lambda x: self.clusters[x].is_prod, sorted(self.clusters.keys())))
        return ret

    def get_cluster_info(self, c):
        if c in self.clusters:
            return self.clusters[c]
        raise ValueError("No such cluster {}".format(c))
