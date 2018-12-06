# (c) Copyright 2017-2018 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from kube_types import Map, String


# Object used to collect class definition and implement the rendering functions
class KubeHelper(object):
    # Internal data structure to store needed data
    _data = {}
    # List of all needed field to have
    _defaults = {
        'class_name': None,
        'class_subclasses': [],
        'class_superclasses': None,
        'class_types': {},
        'class_is_abstract': None,
        'class_identifier': None,
        'class_mapping': [],
        'class_parent_types': None,
        'class_has_metadata': None,
        'class_doc': None,
        'class_doc_link': None,
        'class_xf_hasattr': [],
        'class_xf_detail': []
    }
    # definition of mandatory field to display
    _mandatory = {
        'class_name': True,
        'class_subclasses': False,
        'class_superclasses': False,
        'class_types': False,
        'class_is_abstract': True,
        'class_identifier': False,
        'class_mapping': False,
        'class_parent_types': False,
        'class_has_metadata': True,
        'class_doc': False,
        'class_doc_link': False,
        'class_xf_hasattr': False,
        'class_xf_detail': False
    }

    def __init__(self, *args, **kwargs):
        self._defaults_creations()

        if 'name' in kwargs:
            self.class_name = kwargs['name']
        if 'document' in kwargs:
            self.class_doc = kwargs['document']
        if 'documentlink' in kwargs:
            self.class_doc_link = kwargs['documentlink']

    def _defaults_creations(self):
        for name in getattr(self, '_defaults'):
            if name in self._mandatory:
                self._data[name] = self._defaults[name]
            else:
                raise Exception('Missing mandatory information for {} inside {} class'.format(name, self.__class__.__name__))

    def __getattr__(self, name):
        if name in getattr(self, '_data'):
            return self._data[name]
        else:
            raise ValueError

    def __setattr__(self, name, value):
        if name in getattr(self, '_data'):
            self._data[name] = value
        else:
            raise ValueError

    def render_terminal(self):
        abstract = '' if self.class_is_abstract else ' (abstract type)'
        txt = '{}{}:\n'.format(self.class_name, abstract)

        if len(self.class_superclasses) != 0:
            txt += '  parents: {}\n'.format(', '.join(self.class_superclasses))
        if len(self.class_subclasses) != 0:
            txt += '  children: {}\n'.format(', '.join(self.class_subclasses))
        if len(self.class_parent_types) != 0:
            txt += '  parent types: {}\n'.format(', '.join(sorted(self.class_parent_types.keys())))
        if self.class_has_metadata:
            txt += '  metadata:\n'
            txt += '    annotations:          {}\n'.format(Map(String, String).name())
            txt += '    labels:               {}\n'.format(Map(String, String).name())
        txt += '  properties:\n'
        if self.class_identifier is not None:
            spc = ''
            if len(self.class_identifier) < 7:
                spc = (7 - len(self.class_identifier)) * ' '
            txt += '    {} (identifier): {}{}\n'.format(self.class_identifier, spc, self.class_types[self.class_identifier].name())

        for p in sorted(self.class_types.keys()):
            if p == self.class_identifier:
                continue
            spc = ''
            if len(p) < 20:
                spc = (20 - len(p)) * ' '
            xf = '*' if self.class_xf_detail.get(p, False) else ' '

            txt += '   {}{}: {}{}\n'.format(xf, p, spc, self.class_types[p].name())
            if p in self.class_mapping:
                txt += '      ({})\n'.format(', '.join(self.class_mapping[p]))

        return txt

    def _docstring_formatter(self):
        return '\n'.join([line.strip() for line in self.class_doc.split('\n')])
