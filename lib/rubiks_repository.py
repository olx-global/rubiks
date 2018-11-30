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

DEFAULT_MODULE='openshift1.5'

class IniValue(object):
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


class ClusterInfo(IniValue):
    def __init__(self, name, cp, section):
        self.name = name
        self.prod_state = self._value(cp, section, 'prod_state', 'string', default='production')
        self.is_openshift = self._value(cp, section, 'is_openshift', 'bool', default=False)
        self.output_policybinding = self._value(cp, section, 'output_policybinding', 'bool', default=False)
        self.is_prod = self.prod_state == 'production'
        self.read_only = True

    def __setattr__(self, k, v):
        if not hasattr(self, 'read_only') or not self.read_only:
            return object.__setattr__(self, k, v)
        raise AttributeError("ClusterInfo object is read-only")


class RubiksModule(object):
    def __init__(self, mode=None, name=None, location=None, basepath=None):
        self.mode = mode
        self.name = name
        self.location = location
        self.basepath = basepath

        if mode is None or name is None or location is None or location == '':
            raise Exception('Unable to validate module {}'.format(self.__repr__()))

    def get_module_path(self):
        # TODO: Implement a proper path management for all the types
        if self.mode == 'rubiks':
            basedir = os.path.split(os.path.split(__file__)[0])[0]
            return os.path.join(basedir, 'lib', 'versions', self.location)
        elif self.mode == 'repo':
            return os.path.join(self.basepath, self.location)

        return self.location

    def fetch(self):
        # TODO: Implement fetch for all the supported modules type
        return True

    def __repr__(self):
        return 'RubiksModule<{},{},{}>'.format(self.mode, self.name, self.location)


class RubiksRepository(repository.Repository, IniValue):
    def __init__(self, *args, **kwargs):
        repository.Repository.__init__(self, *args, **kwargs)
        self.pythonpath = []
        self.clusters = {}
        self.is_openshift = False
        self.output_policybinding = False
        self.confidentiality_mode = None
        self.modules = []

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

            self.is_openshift = self._value(m_cp, 'global', 'is_openshift', 'bool', default=False)
            self.output_policybinding = self._value(m_cp, 'global', 'output_policybinding', 'bool', default=False)

            for s in m_cp.sections():
                if s.startswith('cluster_'):
                    self.clusters[s[8:]] = ClusterInfo(s[8:], m_cp, s)

            order = 'sorted'
            modules = {}
            if m_cp.has_section('modules'):
                if m_cp.has_option('modules', '_load'):
                    order = m_cp.get('modules', '_load')
                for module in m_cp.items('modules'):
                    if not module[0] == '_load':
                        details = module[1].split(':')
                        mode = details.pop(0)
                        location = ':'.join(details)

                        if mode == '' or location == '':
                            raise AttributeError("Module string needs to be in format of type:location received: {}".format(module[1]))

                        modules[module[0]] = RubiksModule(mode, module[0], location, self.get_basepath())

            if len(modules) == 0:
                modules[DEFAULT_MODULE] = (RubiksModule('rubiks', 'default', DEFAULT_MODULE, self.get_basepath()))
            if order == 'sorted':
                self.modules = sorted(list(modules.values()))
            else:
                order = order.split(':')
                for module in order:
                    if not module in modules:
                        raise AttributeError("Module {} inside _sorted was not set in the [modules] section".format(module))
                    self.modules.append(modules[module])

    def get_basepath(self):
        return self.basepath

    def get_modules(self):
        return self.modules

    def get_clusters(self):
        ret = []
        ret.extend(filter(lambda x: not self.clusters[x].is_prod, sorted(self.clusters.keys())))
        ret.extend(filter(lambda x: self.clusters[x].is_prod, sorted(self.clusters.keys())))
        return ret

    def get_cluster_info(self, c):
        if c in self.clusters:
            return self.clusters[c]
        raise ValueError("No such cluster {}".format(c))
