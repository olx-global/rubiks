# (c) Copyright 2017-2018 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import json
import os
import sys

from command import Command
from kube_obj import KubeObj
import load_python
import kube_yaml


class Command_order(Command):
    """generate correct order to apply a set of yaml files so that dependencies are met"""

    def populate_args(self, parser):
        parser.add_argument('-N', '--exclude-namespace', action='store_true',
                            help="Don't include namespace kinds (equivalent of -e namespace -e project)")
        parser.add_argument('-e', '--exclude', action='append',
                            help="Don't include named types (may be specified more than once)")
        parser.add_argument('-f', '--follow-symlinks', action='store_true',
                            help="Follow symlinks")
        parser.add_argument('-r', '--reverse', action='store_true',
                            help="Generate list in reverse order")
        parser.add_argument('file_or_dir', nargs='+', help='Files and directories to search')

    def run(self, args):
        def walk(arg):
            if os.path.isfile(arg):
                return [arg]
            elif os.path.isdir(arg):
                ret = []
                for d in os.listdir(arg):
                    if d.startswith('.'):
                        continue
                    ret.extend(walk(os.path.join(arg, d)))
                return ret
            elif args.follow_symlinks and os.path.islink(arg):
                return walk(os.path.realpath(arg))
            else:
                return []

        files = []
        for f in args.file_or_dir:
            files.extend(walk(f))

        excludes = set()
        if args.exclude_namespace:
            excludes.add('namespace')
            excludes.add('project')

        if args.exclude is not None:
            for e in args.exclude:
                excludes.add(e.lower())

        ordering = {}

        for ff in files:
            try:
                with open(ff) as f:
                    data = f.read()

                value = None
                if data.lstrip().startswith('{'):
                    try:
                        value = json.loads(data)
                    except ValueError:
                        pass

                if value is None:
                    value = kube_yaml.yaml_load(data)
                    assert isinstance(value, dict)

                obj = KubeObj.find_class_from_obj(value)
                assert obj is not None

                assert obj.kind.lower() not in excludes

                if obj._output_order not in ordering:
                    ordering[obj._output_order] = []
                ordering[obj._output_order].append(ff)
            except:
                pass

        for k in sorted(ordering.keys(), reverse=args.reverse):
            for f in ordering[k]:
                print(f)

        return 0
