# (c) Copyright 2017-2018 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from command import Command
from .bases import CommandRepositoryBase, LoaderBase
import load_python
import sys


class Command_generate(Command, LoaderBase, CommandRepositoryBase):
    """generate the yaml files in the output directory by running the source"""

    user_error = True

    def populate_args(self, parser):
        group = parser.add_mutually_exclusive_group()
        group.add_argument('-c', '--created', action='store_true',
                           help='Print out filepaths that were created by this generation run')
        group.add_argument('-C', '--contents', action='store_true',
                           help='Print out filepaths whose bytewise contents changed in this run')
        group.add_argument('-Y', '--yaml', action='store_true',
                           help='Print out filepaths whose parsed YAML contents changed in this run')

    def run(self, args):
        content_check = None

        if args.created:
            content_check = 'exists'
        elif args.contents:
            content_check = 'contents'
        elif args.yaml:
            content_check = 'yaml'

        self.loader_setup()

        r = self.get_repository()

        collection = load_python.PythonFileCollection(r, content_check)

        collection.load_all_python(r.sources)

        files = collection.gen_output()

        for f in sorted(files):
            print(f)
