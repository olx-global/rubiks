# (c) Copyright 2017-2018 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from collections import OrderedDict
import sys
import yaml
from var_types import VarEntity

try:
    from io import StringIO
except ImportError:
    from StringIO import StringIO

try:
    _ = basestring
except NameError:
    basestring = str

__all__ = ['quoted', 'literal', 'yaml_safe_dump', 'yaml_load']

# This file is very magical, allowing for a few deep dives in the inner workings of the pyyaml
# and in particular, allowing us to do proper lazy evaluation of our VarEntities


class FakeStringIO(object):
    def __init__(self, t=''):
        self.t = t

    def write(self, text):
        self.t = self.t + text

    def flush(self):
        pass

    def get_value(self):
        return self.t


class BlockRepresenter(yaml.representer.BaseRepresenter):
    def represent_scalar(self, tag, value, style=None):
        if tag.endswith(':str') and isinstance(value, basestring) and value != '' and value.strip('0123456789') == '':
            style = "'"
        elif style is None and not isinstance(value, VarEntity):
            for c in u"\u000a\u000d\u001c\u001d\u001e\u0085\u2028\u2029":
                if c in value:
                    style = '|'

        return yaml.representer.BaseRepresenter.represent_scalar(self, tag, value, style=style)


class VarEntitySerializer(yaml.serializer.Serializer):
    def serialize_node(self, node, parent, index):
        if node not in self.serialized_nodes and isinstance(node, yaml.nodes.ScalarNode) and \
                isinstance(node.value, VarEntity):
            self.serialized_nodes[node] = True
            self.descend_resolver(parent, index)
            self.emit(yaml.events.ScalarEvent(self.anchors[node], 'tag:yaml.org,2002:str', False, node.value, style='"'))
            self.ascend_resolver()
            return
        return yaml.serializer.Serializer.serialize_node(self, node, parent, index)


class VarEntityEmitter(yaml.emitter.Emitter):
    def process_tag(self):
        if isinstance(self.event, yaml.events.ScalarEvent) and isinstance(self.event.value, VarEntity):
            self.prepared_tag = None
            return
        return yaml.emitter.Emitter.process_tag(self)

    def process_scalar(self):
        if isinstance(self.event.value, VarEntity):
            self.event.value.indent = self.indent
            data = ''
            if not self.whitespace:
                data = ' '
                self.column += 1
            data = data + self.event.value
            self.column += 1
            self.stream.write(data)
            self.whitespace = False
            self.analysis = None
            self.style = None
            return
        return yaml.emitter.Emitter.process_scalar(self)


class BaseDumper(VarEntityEmitter, VarEntitySerializer, BlockRepresenter, yaml.dumper.BaseDumper):
    pass


class SafeDumper(VarEntityEmitter, VarEntitySerializer, BlockRepresenter, yaml.dumper.SafeDumper):
    pass


class BlockDumper(VarEntityEmitter, VarEntitySerializer, BlockRepresenter, yaml.dumper.Dumper):
    pass


class StringDumper(BlockRepresenter, yaml.dumper.SafeDumper):
    def expect_document_root(self):
        self.states.append(self.expect_document_end)
        self.expect_node(root=True)
        self.open_ended = False

    def expect_document_end(self):
        if isinstance(self.event, yaml.events.DocumentEndEvent):
            self.flush_stream()
            self.state = self.expect_document_start
        else:
            raise EmitterError("expected DocumentEndEvent, but got %s"
                    % self.event)


def ordered_dict_presenter(dumper, data):
    return dumper.represent_dict(data.items())

yaml.add_representer(OrderedDict, ordered_dict_presenter, Dumper=BlockDumper)
yaml.add_representer(OrderedDict, ordered_dict_presenter, Dumper=SafeDumper)


def var_entity_presenter(dumper, data):
    def representer(val):
        return yaml.dump(val,
                         indent=data.indent,
                         allow_unicode=True,
                         default_flow_style=False,
                         Dumper=StringDumper)
    data.renderer = representer
    if hasattr(dumper, 'represent_unicode'):
        return dumper.represent_unicode(data)
    else:
        return dumper.represent_str(data)

yaml.add_multi_representer(VarEntity, var_entity_presenter, Dumper=BlockDumper)
yaml.add_multi_representer(VarEntity, var_entity_presenter, Dumper=SafeDumper)


def yaml_safe_dump(*args, **kwargs):
    stream = FakeStringIO()
    kwargs['stream'] = stream
    kwargs['default_flow_style'] = False
    kwargs['allow_unicode'] = True
    kwargs['Dumper'] = SafeDumper
    yaml.dump(*args, **kwargs)
    return stream.get_value()

def yaml_safe_dump_all(*args, **kwargs):
    stream = FakeStringIO()
    kwargs['stream'] = stream
    kwargs['default_flow_style'] = False
    kwargs['allow_unicode'] = True
    kwargs['Dumper'] = SafeDumper
    yaml.dump_all(*args, **kwargs)
    return stream.get_value()

def yaml_dump(*args, **kwargs):
    stream = FakeStringIO()
    kwargs['stream'] = stream
    kwargs['default_flow_style'] = False
    kwargs['allow_unicode'] = True
    kwargs['Dumper'] = BlockDumper
    yaml.dump(*args, **kwargs)
    return stream.get_value()


def yaml_load(string):
    if sys.version_info[0] == 2:
        string = unicode(string)
    return yaml.load(StringIO(string))

def yaml_load_all(string):
    if sys.version_info[0] == 2:
        string = unicode(string)
    return yaml.load_all(StringIO(string))
