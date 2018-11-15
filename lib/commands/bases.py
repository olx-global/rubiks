# (c) Copyright 2017-2018 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from command import Command, RuntimeException
from rubiks_repository import RubiksRepository
from repository import RepositoryError
import kube_loader
import obj_registry
import loader


class CommandRepositoryBase(object):
    def get_repository(self):
        try:
            r = RubiksRepository(cwd=self.global_args.base_directory)
        except RepositoryError as e:
            raise RuntimeException(str(e))
        obj_registry.init(r.is_openshift)
        return r


class LoaderBase(object):
    def loader_setup(self):
        if self.global_args.debug:
            loader.DEBUG = True
        elif self.global_args.verbose:
            loader.VERBOSE = True
