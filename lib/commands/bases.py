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
    def get_repository(self, can_fail=False):
        r = None
        try:
            r = RubiksRepository(cwd=self.global_args.base_directory)
            modules = [x.get_module_path() for x in r.get_modules()]
        except RepositoryError as e:
            if not can_fail:
                raise RuntimeException(str(e))
        kube_loader.load(*modules)
        
        if r is not None:
            obj_registry.init(r.is_openshift)
        return r


class LoaderBase(object):
    def loader_setup(self):
        if self.global_args.debug:
            loader.DEBUG = True
        elif self.global_args.verbose:
            loader.VERBOSE = True
