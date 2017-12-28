# (c) Copyright 2017 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from collections import OrderedDict
import sys
import yaml

__all__ = ['quoted', 'literal', 'yaml_safe_dump']

class BlockRepresenter(yaml.representer.BaseRepresenter):
    def represent_scalar(self, tag, value, style=None):
        if style is None:
            for c in u"\u000a\u000d\u001c\u001d\u001e\u0085\u2028\u2029":
                if c in value:
                    style = '|'
        return yaml.representer.BaseRepresenter.represent_scalar(self, tag, value, style=style)

class BaseDumper(BlockRepresenter, yaml.dumper.BaseDumper):
    pass

class SafeDumper(BlockRepresenter, yaml.dumper.SafeDumper):
    pass

class BlockDumper(BlockRepresenter, yaml.dumper.Dumper):
    pass

class quoted(str):
    pass

def quoted_presenter(dumper, data):
    return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='"')
yaml.add_representer(quoted, quoted_presenter, Dumper=yaml.Dumper)
yaml.add_representer(quoted, quoted_presenter, Dumper=yaml.SafeDumper)

class literal(str):
    pass

def literal_presenter(dumper, data):
    print('here')
    return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
yaml.add_representer(literal, literal_presenter, Dumper=yaml.Dumper)
yaml.add_representer(literal, literal_presenter, Dumper=yaml.SafeDumper)

def ordered_dict_presenter(dumper, data):
    return dumper.represent_dict(data.items())
yaml.add_representer(OrderedDict, ordered_dict_presenter, Dumper=yaml.Dumper)
yaml.add_representer(OrderedDict, ordered_dict_presenter, Dumper=yaml.SafeDumper)

def _should_use_block(v):
    for c in u"\u000a\u000d\u001c\u001d\u001e\u0085\u2028\u2029":
        if c in value:
            return True
    return False

def yaml_safe_dump(*args, **kwargs):
    kwargs['default_flow_style'] = False
    kwargs['allow_unicode'] = True
    kwargs['Dumper'] = SafeDumper
    return yaml.dump(*args, **kwargs)

def yaml_dump(*args, **kwargs):
    kwargs['default_flow_style'] = False
    kwargs['allow_unicode'] = True
    kwargs['Dumper'] = BlockDumper
    return yaml.dump(*args, **kwargs)
