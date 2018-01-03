# (c) Copyright 2017-2018 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import json
import sys

from command import Command
from kube_obj import KubeObj
import load_python
import kube_yaml


class Command_gen_py(Command):
    """generate python from yaml or json input"""

    def populate_args(self, parser):
        parser.add_argument('-I', '--indent', type=int, default=0, help='number of spaces to indent')
        parser.add_argument('-n', '--namespace', help='set namespace for this object (implies -N)')
        parser.add_argument('-N', '--with-namespace', action='store_true',
                            help='write the with namespace line')
        parser.add_argument('--include-defaults', action='store_true', help='include defaults in output')
        parser.add_argument('file', help='file to try and parse (use "-" for stdin)')

    def run(self, args):
        load_python.PythonBaseFile.get_kube_objs()

        if args.file == '-':
            data = sys.stdin.read()
            sys.stdin.close()
        else:
            with open(args.file) as f:
                data = f.read()

        value = None
        if data.lstrip().startswith('{'):
            try:
                value = json.loads(data)
            except ValueError:
                pass

        if value is None:
            try:
                value = kube_yaml.yaml_load(data)
                if not isinstance(value, dict):
                    value = None
            except ValueError:
                pass

        if value is None:
            print("Cannot load {} as either JSON or YAML".format(args.file), file=sys.stderr)
            return 1

        namespace = args.namespace
        if namespace is None:
            try:
                namespace = value['metadata']['namespace']
            except KeyError:
                pass
        indent = args.indent
        if (args.namespace is not None or args.with_namespace) and namespace is not None:
            print((' ' * indent) + 'with namespace({}):'.format(repr(namespace)))
            indent += 4
        print((' ' * indent) + KubeObj.parse_obj(value).dump_obj(indent, args.include_defaults))
