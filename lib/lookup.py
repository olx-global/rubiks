# (c) Copyright 2017-2018 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import json
import sys

from kube_vartypes import Confidential
from kube_yaml import yaml_load
from loader import Path
from user_error import UserError


class InvalidKey(Exception):
    pass


class KeyNotExist(InvalidKey):
    pass


class KeyIsBranch(InvalidKey):
    pass


class Resolver(object):
    current_cluster = None

    def __init__(self, pth, non_exist_ok=True, git_crypt_ok=True, is_confidential=False, default=None,
                 assert_type=None, fail_ok=False):
        if not isinstance(pth, Path):
            raise TypeError("path is not of type Path, but actually {}".format(pth.__class__.__name__))

        self.is_confidential = is_confidential
        self.default = default
        self.assert_type = assert_type
        self.has_data = False
        self.path = pth
        data = None

        try:
            with open(pth.full_path, 'rb') as f:
                data = f.read()
        except:
            if not non_exist_ok:
                raise

        if data is None:
            return

        if b'GITCRYPT' in data[0:10]:
            if not git_crypt_ok:
                raise ValueError("file {} was git-crypt-ed and cannot be read".format(pth.repo_rel_path))
            return

        try:
            data = data.decode('utf8')
        except:
            if fail_ok:
                print("Can't parse {} as unicode, let alone JSON or YAML".format(pth.repo_rel_path),
                      file=sys.stderr)
                return
            raise

        try:
            if data.lstrip().startswith('{') and data.rstrip().endswith('}'):
                self.data = json.loads(data)
                self.has_data = True
            else:
                raise ValueError("not json")
        except ValueError:
            try:
                self.data = yaml_load(data)
                self.has_data = True
            except:
                if fail_ok:
                    print("Can't parse {} as JSON or YAML".format(pth.repo_rel_path), file=sys.stderr)
                else:
                    raise ValueError("Unparseable file " + pth.repo_rel_path)

    def get_branches(self, path):
        try:
            path = "" + path
        except:
            raise UserError(TypeError("Wrong type for path: expected str, got {}".format(
                path.__class__.__name__)))

        if len(path) == 0:
            raise UserError(ValueError("path should not be empty string - use '.' for root"))

        if not self.has_data:
            return ()

        if path == '.':
            return tuple(sorted(self.data.keys()))

        path_c = path.split('.')
        ctx = self.data

        i = 0
        while i < len(path_c):
            if not isinstance(ctx, dict) or not path_c[i] in ctx:
                raise UserError(KeyNotExist("branch {} ({}) doesn't exist in {}".format(
                    '.'.join(path_c[0:i]), path, self.path.repo_rel_path)))

            ctx = ctx[path_c[i]]
            i += 1

        if isinstance(ctx, dict):
            return tuple(sorted(ctx.keys()))

        return ()

    def get_key(self, *args):
        for p in range(0, len(args)):
            last = False
            if p == len(args) - 1:
                last = True
            path = self._resolve_path(args[p])

            try:
                if self.is_confidential:
                    return Confidential(str(self._get_key(path)))

                try:
                    ret = self._get_key(path)
                except InvalidKey as e:
                    if self.default is not None:
                        ret = self.default
                    else:
                        raise UserError(e)

                if self.assert_type is not None and not isinstance(ret, self.assert_type):
                    raise UserError(TypeError("return value of {} is not {}".format(path, self.assert_type)))

                return ret
            except Exception as e:
                if last:
                    if isinstance(e, UserError):
                        raise
                    raise UserError(e)

    def _resolve_path(self, path):
        if self.__class__.current_cluster is None:
            return path
        return path.format(cluster=self.__class__.current_cluster.name)

    def _get_key(self, path):
        if not self.has_data:
            if self.default is not None:
                return self.default
            return '<unknown "{}">'.format(path)

        path_c = path.split('.')
        ctx = self.data

        i = 0
        while i < len(path_c):
            if not isinstance(ctx, dict) or not path_c[i] in ctx:
                raise KeyNotExist("branch {} ({}) doesn't exist in {}".format(
                    '.'.join(path_c[0:i]), path, self.path.repo_rel_path))

            ctx = ctx[path_c[i]]
            i += 1

        if isinstance(ctx, dict):
            raise KeyIsBranch(
                "branch {} ({}) is not specific enough in {} (refers to branch not key)".format(
                    '.'.join(path_c), path, self.path.repo_rel_path))

        return ctx
