# (c) Copyright 2017-2018 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import sys

from command import Command
import kube_yaml

try:
    _ = basestring
except NameError:
    basestring = str

try:
    _ = long
except NameError:
    long = int


class Command_yaml_diff(Command):
    """compare two yaml files and show where they differ"""

    def populate_args(self, parser):
        parser.add_argument('-n', '--no-reorder', action='store_true',
                            help="don't allow reordering of arrays")
        parser.add_argument('--no-colour', action='store_true',
                            help="don't use colour even on terminal")
        parser.add_argument('-N', '--ignore-none', action='store_true',
                            help='ignore None when comparing')
        parser.add_argument('-E', '--ignore-empty', action='store_true',
                            help='ignore {} and [] when comparing')
        parser.add_argument('source', help='source file')
        parser.add_argument('dest', help='destination file')

    def run(self, args):
        try:
            with open(args.source) as f:
                s_data = f.read()
        except:
            print("Error reading {}".format(args.source), file=sys.stderr)
            return 1

        try:
            with open(args.dest) as f:
                d_data = f.read()
        except:
            print("Error reading {}".format(args.dest), file=sys.stderr)
            return 1

        try:
            src = kube_yaml.yaml_load(s_data)
        except:
            print("Error parsing {}".format(args.source), file=sys.stderr)
            return 1

        try:
            dst = kube_yaml.yaml_load(d_data)
        except:
            print("Error parsing {}".format(args.dest), file=sys.stderr)
            return 1

        self.allow_reorder = not args.no_reorder
        self.colour = not args.no_colour
        self.ignore_none = args.ignore_none
        self.ignore_empty = args.ignore_empty
        self.output = False

        if not (hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()):
            self.colour = False

        return self.diff('<top>', src, dst)

    def diff(self, path, src, dst):
        def printable(v):
            return isinstance(v, (bool, int, long, float, basestring))

        def len_zero(v):
            return isinstance(v, (dict, list)) and len(v) == 0

        def reorderable(el, typ):
            return self.allow_reorder and \
                (len(src) == 0 or all(map(lambda x: isinstance(x, dict) and el in x and isinstance(x[el], typ), src))) and \
                (len(dst) == 0 or all(map(lambda x: isinstance(x, dict) and el in x and isinstance(x[el], typ), dst))) and \
                len(set(map(lambda x: x[el], src))) == len(src) and \
                len(set(map(lambda x: x[el], dst))) == len(dst)

        def s_print(k, v):
            col_on = ''
            col_off = ''
            pfx = ''
            if self.colour:
                col_on = '\x1b[31m'
                col_off = '\x1b[39m'
            if not self.output:
                self.output = True
            else:
                pfx = '\n'
            print(pfx + col_on + '- ' + k + col_off + '\n  ' + v)

        def d_print(k, v):
            col_on = ''
            col_off = ''
            pfx = ''
            if self.colour:
                col_on = '\x1b[32m'
                col_off = '\x1b[39m'
            if not self.output:
                self.output = True
            else:
                pfx = '\n'
            print(pfx + col_on + '+ ' + k + col_off + '\n  ' + v)

        def c_print(k, v):
            col_on = ''
            col_off = ''
            pfx = ''
            if self.colour:
                col_on = '\x1b[33m'
                col_off = '\x1b[39m'
            if not self.output:
                self.output = True
            else:
                pfx = '\n'
            print(pfx + col_on + '~ ' + k + col_off + '\n  ' + v)

        if printable(src):
            if dst.__class__ == src.__class__:
                if src == dst:
                    return 0
                else:
                    c_print(path, 'values differ {} vs {}'.format(src, dst))
            else:
                if printable(dst) or len_zero(dst):
                    c_print(path, 'types differ {}({}) vs {}({})'.format(src.__class__.__name__, src,
                                                                         dst.__class__.__name__, dst))
                else:
                    c_print(path, 'types differ {}({}) vs {}'.format(src.__class__.__name__, src,
                                                                     dst.__class__.__name__))
            return 1

        elif isinstance(src, dict):
            if isinstance(dst, dict):
                ret = 0
                all_keys = set()
                all_keys.update(src.keys())
                all_keys.update(dst.keys())
                for k in sorted(all_keys):
                    if k in src and k in dst:
                        rc = self.diff(path + '.' + k, src[k], dst[k])
                        if rc != 0:
                            ret = 1
                    elif self.ignore_none and ((k not in src and dst[k] is None) or \
                                               (k not in dst and src[k] is None)):
                        pass
                    elif self.ignore_empty and ((k not in src and len_zero(dst[k])) or \
                                                (k not in dst and len_zero(src[k]))):
                        pass
                    elif k not in src:
                        if printable(dst[k]) or len_zero(dst[k]):
                            d_print(path + '.' + k, 'key exists only in destination (value={})'.format(dst[k]))
                        else:
                            d_print(path + '.' + k, 'key exists only in destination (type={})'.format(dst[k].__class__.__name__))
                        ret = 1
                    else:
                        if printable(src[k]) or len_zero(src[k]):
                            s_print(path + '.' + k, 'key exists only in source (value={})'.format(src[k]))
                        else:
                            s_print(path + '.' + k, 'key exists only in source (type={})'.format(src[k].__class__.__name__))
                        ret = 1
                return ret
            elif len_zero(src):
                if printable(dst) or len_zero(dst):
                    c_print(path, 'types differ {}({}) vs {}({})'.format(src.__class__.__name__, src,
                                                                         dst.__class__.__name__, dst))
                else:
                    c_print(path, 'types differ {}({}) vs {}'.format(src.__class__.__name__, src,
                                                                     dst.__class__.__name__))
            elif printable(dst) or len_zero(dst):
                c_print(path, 'types differ {} vs {}({})'.format(src.__class__.__name__,
                                                                 dst.__class__.__name__, dst))
            else:
                c_print(path, 'types differ {} vs {}'.format(src.__class__.__name__, dst.__class__.__name__))

            return 1

        elif isinstance(src, list):
            if isinstance(dst, list):
                ret = 0
                if reorderable('name', basestring):
                    all_names = set()
                    all_names.update(map(lambda x: x['name'], src))
                    all_names.update(map(lambda x: x['name'], dst))
                    for n in sorted(all_names):
                        s_ent = None
                        d_ent = None
                        for i in src:
                            if i['name'] == n:
                                s_ent = i
                                break
                        for i in dst:
                            if i['name'] == n:
                                d_ent = i
                                break

                        n_path = path + '[name={}]'.format(n)
                        if s_ent is not None and d_ent is not None:
                            rc = self.diff(n_path, s_ent, d_ent)
                            if rc != 0:
                                ret = 1
                        elif s_ent is not None:
                            s_print(n_path, 'element exists only in source')
                            ret = 1
                        else:
                            d_print(n_path, 'element exists only in destination')
                            ret = 1
                elif reorderable('port', int):
                    all_ports = set()
                    all_ports.update(map(lambda x: x['port'], src))
                    all_ports.update(map(lambda x: x['port'], dst))
                    for p in sorted(all_ports):
                        s_ent = None
                        d_ent = None
                        for i in src:
                            if i['port'] == p:
                                s_ent = i
                                break
                        for i in dst:
                            if i['port'] == p:
                                d_ent = i
                                break

                        n_path = path + '[port={}]'.format(p)
                        if s_ent is not None and d_ent is not None:
                            rc = self.diff(n_path, s_ent, d_ent)
                            if rc != 0:
                                ret = 1
                        elif s_ent is not None:
                            s_print(n_path, 'element exists only in source')
                            ret = 1
                        else:
                            d_print(n_path, 'element exists only in destination')
                            ret = 1
                else:
                    ret = 0
                    for i in range(0, min(len(src), len(dst))):
                        rc = self.diff('{}[{}]'.format(path, i), src[i], dst[i])
                        if rc != 0:
                            ret = 1
                    if len(src) != len(dst):
                        if len(src) > len(dst):
                            s_print(path, '{} element(s) more in source than destination'.format(len(src) - len(dst)))
                            ret = 1
                        else:
                            d_print(path, '{} element(s) more in destination than source'.format(len(dst) - len(src)))
                            ret = 1
                return ret
            elif len_zero(src):
                if printable(dst) or len_zero(dst):
                    c_print(path, 'types differ {}({}) vs {}({})'.format(src.__class__.__name__, src,
                                                                         dst.__class__.__name__, dst))
                else:
                    c_print(path, 'types differ {}({}) vs {}'.format(src.__class__.__name__, src,
                                                                     dst.__class__.__name__))
            elif printable(dst) or len_zero(dst):
                c_print(path, 'types differ {} vs {}({})'.format(src.__class__.__name__,
                                                                 dst.__class__.__name__, dst))
            else:
                c_print(path, 'types differ {} vs {}'.format(src.__class__.__name__, dst.__class__.__name__))

            return 1

        else:
            if src is dst:
                return 0

            if src.__class__ is not dst.__class__:
                if printable(dst) or len_zero(dst):
                    c_print(path, 'types differ {} vs {}({})'.format(src.__class__.__name__,
                                                                     dst.__class__.__name__, dst))
                else:
                    c_print(path, 'types differ {} vs {}'.format(src.__class__.__name__,
                                                                 dst.__class__.__name__))
            else:
                c_print(path, 'objects differ {} vs {}'.format(repr(src), repr(dst)))

            return 1

        raise ValueError("unreachable")
