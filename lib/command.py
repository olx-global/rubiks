# (c) Copyright 2017-2018 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import argparse
import os
import sys
import textwrap

import user_error


class DuplicateCommandNameError(Exception):
    pass


class NoSuchCommandException(Exception):
    pass


class RuntimeException(Exception):
    pass


class Command(object):
    user_error = False

    @classmethod
    def help(cls):
        if hasattr(cls, '__doc__') and cls.__doc__ is not None and cls.__doc__ != '':
            return cls.__doc__.strip()
        for k in cls.__bases__:
            if k is object:
                continue
            if hasattr(k, 'help'):
                return k.help()
        return "*** add some help ***"

    @classmethod
    def is_abstract(cls):
        if not cls.__name__.startswith('Command_') or cls.__name__ == 'Command_':
            return True

        base = Command.populate_args
        this = cls.populate_args
        if hasattr(base, '__func__') and hasattr(this, '__func__'):
            # python2.7
            if this.__func__ is base.__func__:
                return True
        elif this is base:
            # python3 and abstract
            return True

        base = Command.run
        this = cls.run
        if hasattr(base, '__func__') and hasattr(this, '__func__'):
            # python2.7
            if this.__func__ is base.__func__:
                return True
        elif this is base:
            # python3 and abstract
            return True

        return False

    @classmethod
    def name(cls):
        if cls.is_abstract():
            return None
        return cls.__name__[8:]

    @classmethod
    def get_commands(cls):
        def _rec_command(kls):
            ret = {}
            for k in kls.__subclasses__():
                ret.update(_rec_command(k))
            if not kls.is_abstract():
                if kls.name() in ret:
                    raise DuplicateCommandNameError('Duplicate command name {} specified'.format(kls.name()))
                ret[kls.name()] = kls
            return ret
        if not hasattr(Command, '_cmd_cache'):
            Command._cmd_cache = _rec_command(Command)
        return Command._cmd_cache

    @classmethod
    def global_options(cls, parser):
        parser.add_argument('-h', '--help', action='store_true',
                            help='enumerate the various available commands')
        parser.add_argument('-v', '--verbose', action='store_true',
                            help='turn on verbose mode')
        parser.add_argument('-d', '--debug', action='store_true',
                            help='turn on debug mode')
        parser.add_argument('-b', '--base-directory',
                            help='run the repository in this directory instead of the current working directory')

    @classmethod
    def run_command(cls, prog=None, argv=None):
        if prog is None:
            prog = sys.argv[0]
            if os.path.sep in prog:
                prog = os.path.split(prog)[1]
        if argv is None:
            argv = sys.argv[1:]

        parser = argparse.ArgumentParser(
            prog=prog,
            description='A command-line tool for helping to manage Kubernetes and Openshift',
            add_help=False,
            )
        cls.global_options(parser)
        parser.add_argument('command', nargs=argparse.REMAINDER)
        args = parser.parse_args()
        cmds = cls.get_commands()

        this_cmd = None
        force_rc = None
        if len(args.command) != 0:
            this_cmd = args.command[0]
            this_cmd = this_cmd.replace('-', '_')

        if args.help or len(args.command) == 0:
            cmd = cmds['help']
        elif this_cmd not in cmds:
            print('Unknown command "{} {}"!\n'.format(prog, this_cmd), file=sys.stderr)
            force_rc = 1
            cmd = cmds['help']
        else:
            cmd = cmds[this_cmd]

        if cmd is cmds['help']:
            cmd_obj = cmd(prog, None)
            rc = cmd_obj.do_run(['help'])
        elif cmd is cmds['options']:
            cmd_obj = cmd(prog, None)
            rc = cmd_obj.do_run(['options'])
        else:
            cmd_obj = cmd(prog, args)
            rc = cmd_obj.do_run(args.command)

        if force_rc is not None:
            return force_rc

        if rc is None:
            return 0

        return rc

    def __init__(self, prog, global_args):
        self.prog = prog
        self.parser = self._get_parser()
        self.populate_args(self.parser)
        self.global_args = global_args

    def _get_parser(self):
        if self.__class__.name() is None:
            raise NoSuchCommandException("No such command")
        return argparse.ArgumentParser(prog='{} {}'.format(sys.argv[0], self.__class__.name()),
                                       description=self.__class__.help(),
                                       )
    def do_run(self, argv):
        args = self.parser.parse_args(argv[1:])
        nargs = self.preprocess_args(self.parser, args)
        if nargs is None:
            nargs = args

        try:
            if self.user_error:
                with user_error.user_errors(False):
                    rc = self.run(nargs)
            else:
                rc = self.run(nargs)
        except RuntimeException as e:
            print('{} fatal error: {}'.format(self.prog, str(e)), file=sys.stderr)
            return 1

        if rc is None:
            return 0
        return rc

    # these are populated per command
    def populate_args(self, parser):
        pass

    def preprocess_args(self, parser, args):
        pass

    def run(self, args):
        pass


class Command_help(Command):
    """Print out this help screen with the various rubiks commands"""

    def populate_args(self, parser):
        pass

    def run(self, args):
        try:
            width = int(os.environ['COLUMNS'])
        except (KeyError, ValueError):
            width = 80
        width -= 2

        text = '\n'.join(textwrap.TextWrapper(width=width).wrap(
            '\n'.join(map(lambda x: x.strip(),
            """
            {prog} is a kubernetes and openshift management tool based around keeping records
            of cluster configurations in git.
            """.format(prog=self.prog).splitlines()[1:])))) + '\n\n'

        text += 'Note that in all of these cases, the command actually is:\n'
        text += '  {prog} [global_options...] <command> [command-specific_options...]\n\n'.format(prog=self.prog)

        text += '{prog} has several subcommands:\n\n'.format(prog=self.prog)

        cmds = self.__class__.get_commands()

        text += self.help_text('help', width=width) + '\n'

        for c in sorted(cmds.keys()):
            if c in ('help', 'options'):
                continue
            text += self.help_text(c, width=width)

        text += '\n' + self.help_text('options', width=width)
        print(text)

    def help_text(self, cmd, hwidth=20, width=72):
        cmd_o = self.__class__.get_commands()[cmd]
        cmd_text = '{} {} - '.format(self.prog, cmd)
        init = ''
        if len(cmd_text) < hwidth:
            init = (' ' * (hwidth - len(cmd_text)))
        tw = textwrap.TextWrapper(width=width, initial_indent=init, subsequent_indent=(' ' * hwidth))
        return '\n'.join(tw.wrap(cmd_text + cmd_o.help())) + '\n'

class Command_options(Command):
    """Show help for the rubiks global_options"""

    def populate_args(self, parser):
        pass

    def run(self, args):
        parser = argparse.ArgumentParser(
            prog=self.prog,
            description="Rubiks global options - these are the options which are valid with every "
                "command",
            add_help=False,
            )
        self.__class__.global_options(parser)
        parser.add_argument('command')
        parser.add_argument('arguments', nargs=argparse.REMAINDER)
        output = parser.format_help()
        ol = output.splitlines()
        nol = []
        out = True
        for l in ol:
            if l.startswith('positional arguments:'):
                out = False
            elif l.startswith('optional arguments:'):
                out = True
            if out:
                nol.append(l)
        print('\n'.join(nol))
