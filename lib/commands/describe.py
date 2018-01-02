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
        obj = None

        for sname in args.objects:
            ss = sname.split('.')

            for oname in objs:
                if oname.lower() == ss[0].lower():
                    obj = objs[oname]
                    break

            if obj is None:
                sys.stdout.flush()
                print("No matching object for type {} ({})\n".format(sname, ss[0]), file=sys.stderr)

            else:
                use_obj = True
                if len(ss) > 1:
                    use_obj = False

                    for i in range(1, len(ss)):
                        comp = ss[i]
                        mapping = obj._find_defaults('_map')
                        if comp in mapping:
                            comp = mapping[comp]
                        types = obj.resolve_types()

                        if comp not in types:
                            sys.stdout.flush()
                            print("No matching object for type {} ({})\n".format(sname, '.'.join(ss[0:i + 1])), file=sys.stderr)
                            break

                        if types[comp].original_type() is not None:
                            obj = types[comp].original_type()

                            if isinstance(obj, list):
                                obj = obj[0]
                            elif isinstance(obj, dict):
                                obj = obj['value']

                            if 1 + i == len(ss):
                                use_obj = True

                        elif i + 1 != len(ss):
                            if found:
                                print('', file=sys.stdout)
                            found = True
                            print('.'.join(ss[0:i + 1]) + ':', file=sys.stdout)
                            print(types[comp].name(), file=sys.stdout)
                            sys.stdout.flush()
                            print("No matching object for type {} ({})\n".format(sname, '.'.join(ss[0:i + 2])), file=sys.stderr)
                            break

                        else:
                            if found:
                                print('', file=sys.stdout)
                            found = True
                            print('.'.join(ss[0:i + 1]) + ':', file=sys.stdout)
                            print(types[comp].name(), file=sys.stdout)

                if use_obj:
                    if found:
                        print('', file=sys.stdout)
                    found = True
                    print('.'.join(ss[0:]) + ':', file=sys.stdout)
                    print(obj.get_help(), file=sys.stdout)

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
