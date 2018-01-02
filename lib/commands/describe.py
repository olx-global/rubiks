# (c) Copyright 2017-2018 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from command import Command
from kube_obj import KubeObj
import load_python
import sys

class Command_describe(Command):
    """describe the kubernetes object types to be included in kube files"""

    def populate_args(self, parser):
        parser.add_argument('objects', nargs='+', help='objects to describe')

    def run(self, args):
        objs = load_python.PythonBaseFile.get_kube_objs()

        found = False

        for sname in args.objects:
            this_found = False
            for oname in objs:
                if oname.lower() == sname.lower():
                    if found:
                        print('', file=sys.stdout)
                    found = True
                    this_found = True
                    print(objs[oname].get_help(), file=sys.stdout)
                    break
            if not this_found:
                sys.stdout.flush()
                print("No matching object for type {}\n".format(sname), file=sys.stderr)

        if not found:
            return 1

class Command_list_objs(Command):
    """list the kubernetes/openshift object types we support"""

    def populate_args(self, parser):
        parser.add_argument('-a', '--all', action='store_true',
                            help='show intermediate objects as well as top-level')

    def run(self, args):
        objs = load_python.PythonBaseFile.get_kube_objs()

        for oname in sorted(objs.keys()):
            if isinstance(objs[oname](), KubeObj):
                kind = objs[oname].kind
                if kind == oname:
                    print("* {}".format(oname))
                else:
                    print("* {} ({})".format(oname, kind))
            elif args.all:
                if objs[oname].is_abstract_type():
                    print("- ({})".format(oname))
                else:
                    print("- {}".format(oname))
