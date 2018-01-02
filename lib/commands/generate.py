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
        pass

    def run(self, args):
        self.loader_setup()

        r = self.get_repository()

        collection = load_python.PythonFileCollection(r)

        collection.load_all_python(r.sources)

        collection.gen_output()
