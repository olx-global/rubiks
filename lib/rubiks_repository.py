# (c) Copyright 2017 OLX

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

class RubiksRepository(repository.Repository):
    def __init__(self):
        repository.Repository.__init__(self)
        if os.path.exists(os.path.join(self.basepath, '.rubiks')):
            m_cp = ConfigParser()
            m_cp.read(os.path.join(self.basepath, '.rubiks'))

            if m_cp.has_section('layout'):
                if m_cp.has_option('layout', 'sources'):
                    self.sources = m_cp.get('layout', 'sources', raw=True)
                if m_cp.has_option('layout', 'outputs'):
                    self.outputs = m_cp.get('layout', 'outputs', raw=True)
