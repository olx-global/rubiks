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
from user_error import UserError, handle_user_error


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

        for p in pth:
            if not isinstance(p, Path):
                raise TypeError("path is not of type Path, but actually {}".format(pth.__class__.__name__))

        self.is_confidential = is_confidential
        self.default = default
        self.assert_type = assert_type
        self.has_data = False
        self.has_gitcrypt = False
        self.path = pth
        self.data = dict()
        self.non_exist_ok = non_exist_ok
        self.git_crypt_ok = git_crypt_ok
        self.fail_ok = fail_ok
        self._load_files()

    def _load_files(self):
        data = None
        for path in self.path:
            try:
                with open(path.full_path, 'rb') as f:
                    data = f.read()
            except:
                if not self.non_exist_ok:
                    raise

            if data is None:
                return

            if b'GITCRYPT' in data[0:10]:
                if self.has_data:
                    raise ValueError("Mixed crypt and notcrypt data in lookup files")

                if not self.git_crypt_ok:
                    raise ValueError("file {} was git-crypt-ed and cannot be read".format(path.repo_rel_path))
                self.has_gitcrypt = True
                continue

            if self.has_gitcrypt:
                raise ValueError("Mixed crypt and notcrypt data in lookup files")

            try:
                data = data.decode('utf8')
            except:
                if self.fail_ok:
                    print("Can't parse {} as unicode, let alone JSON or YAML".format(path.hrepo_rel_path),
                          file=sys.stderr)
                    return
                raise

            try:
                if data.lstrip().startswith('{') and data.rstrip().endswith('}'):
                    self.data.update(json.loads(data))
                    self.has_data = True
                else:
                    raise ValueError("not json")
            except ValueError:
                try:
                    self.data.update(yaml_load(data))
                    self.has_data = True
                except:
                    if self.fail_ok:
                        print("Can't parse {} as JSON or YAML".format(path.repo_rel_path), file=sys.stderr)
                    else:
                        raise ValueError("Unparseable file " + path.repo_rel_path)

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

        path_c = self._resolve_path(path).split('.')
        ctx = self.data

        i = 0
        while i < len(path_c):
            if not isinstance(ctx, dict) or not path_c[i] in ctx:
                raise UserError(KeyNotExist("branch {} ({}) doesn't exist in {}".format(
                    '.'.join(path_c[0:i]), path, self._get_repo_rel_path())))

            ctx = ctx[path_c[i]]
            i += 1

        if isinstance(ctx, dict):
            return tuple(sorted(ctx.keys()))

        return ()

    def get_key(self, *args):
        e_txt = None
        for p in range(0, len(args)):
            last = False
            if p == len(args) - 1:
                last = True
            path = self._resolve_path(args[p])

            try:
                if self.is_confidential:
                    return Confidential(str(self._get_key(path, e_txt)))

                try:
                    ret = self._get_key(path, e_txt)
                except InvalidKey as e:
                    handle_user_error(e)

                if self.assert_type is not None and not isinstance(ret, self.assert_type):
                    raise UserError(TypeError("return value of {} is not {}".format(path, self.assert_type)))

                return ret
            except Exception as e:
                e_txt = str(e)

                if last:
                    if self.default is not None:
                        if self.assert_type is not None and not isinstance(self.default, self.assert_type):
                            raise UserError(TypeError(
                                "return value of {} is not {}".format(path, self.assert_type)))
                        return self.default
                    handle_user_error(e)

    def _resolve_path(self, path):
        if self.__class__.current_cluster is None:
            return path
        return path.format(cluster=self.__class__.current_cluster.name)

    def _get_repo_rel_path(self):
        return ', '.join(map(lambda x: x.repo_rel_path, self.path))

    def _get_key(self, path, e_txt):
        if not self.has_data:
            if self.default is not None:
                return self.default
            return '<unknown "{}">'.format(path)

        path_c = path.split('.')
        ctx = self.data

        if e_txt is None:
            e_txt = ''
        else:
            e_txt += ', '
        i = 0
        while i < len(path_c):
            if not isinstance(ctx, dict) or not path_c[i] in ctx:
                raise KeyNotExist(e_txt + "branch {} ({}) doesn't exist in {}".format(
                    '.'.join(path_c[0:i + 1]), path, self._get_repo_rel_path()))

            ctx = ctx[path_c[i]]
            i += 1

        if isinstance(ctx, dict):
            raise KeyIsBranch(
                e_txt + "branch {} ({}) is not specific enough in {} (refers to branch not key)".format(
                    '.'.join(path_c), path, self._get_repo_rel_path()))

        return ctx
