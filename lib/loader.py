# (c) Copyright 2017-2018 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os
import sys

from user_error import UserError
from load_python_core import get_bare_module

DEV = True
VERBOSE = False
DEBUG = False


class LoaderBaseException(Exception):
    pass


class LoaderLoopException(LoaderBaseException):
    pass


class LoaderNotInSourcesException(LoaderBaseException):
    pass


class LoaderArgumentError(LoaderBaseException):
    pass


class LoaderFileNameError(LoaderBaseException):
    pass


class LoaderCompileException(LoaderBaseException):
    pass


class LoaderImportError(LoaderBaseException):
    pass


class Path(object):
    def __init__(self, path, repository=None, base=None):
        if repository is not None:
            self.repository = repository
            self.rootdir = repository.basepath
            self.srcsdir = os.path.join(repository.basepath, repository.sources)

        self.base = base
        self.full_path = os.path.realpath(path)
        if repository is not None:
            self.repo_rel_path = os.path.relpath(self.full_path, self.rootdir)
            self.src_rel_path = os.path.relpath(self.full_path, self.srcsdir)
            if not self.in_sources():
                raise LoaderNotInSourcesException('{} is not in sources directory {}'.format(
                                                  self.full_path, self.srcsdir))

        if self.base is not None:
            self.base_rel_path = os.path.relpath(self.full_path, self.base)

        self.full_dir = os.path.split(self.full_path)[0]
        if repository is not None:
            self.repo_rel_dir = os.path.split(self.repo_rel_path)[0]
            self.src_rel_dir = os.path.split(self.src_rel_path)[0]
        if self.base is not None:
            self.base_rel_dir = os.path.split(self.base_rel_path)[0]

        self.filename = os.path.split(self.full_path)[1]
        if '.' in self.filename:
            self.basename, self.extension = self.filename.rsplit('.', 1)
        else:
            self.basename = self.filename
            self.extension = None

    def in_sources(self):
        return not self.src_rel_path.startswith('..')

    def dot_path(self):
        if self.base is not None:
            return '.'.join(self.base_rel_dir.split(os.path.sep)) + '.' + self.basename
        return '.'.join(self.src_rel_dir.split(os.path.sep)) + '.' + self.basename

    def rel_path(self, path):
        assert not path.startswith('/')
        return self.__class__(os.path.join(self.full_dir, path), self.repository)

    def replace_extension(self, new_ext):
        return self.__class__(os.path.join(self.full_dir, self.basename + '.' + new_ext), self.repository)

    def exists(self):
        return os.path.exists(self.full_path)

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self.full_path == other.full_path

    def __repr__(self):
        return '<{}: {}>'.format(self.__class__.__name__, self.full_path)

    def __str__(self):
        return self.full_path


class Loader(object):
    def __init__(self, repository):
        self.files = {}
        self.deps = {}
        self.repository = repository

    def root(self):
        return self.repository.basepath

    def sources(self):
        return self.repository.sources

    def debug(self, level, text):
        if VERBOSE:
            if level in (0, 1):
                print(text, file=sys.stderr)
        if DEBUG:
            indent = ' ' * level
            print('{}-> {}'.format(indent, text), file=sys.stderr)

    def finish(self):
        self.debug(3, 'calling finish()')
        for f in self.files.values():
            if hasattr(f, 'finish'):
                f.finish()
        if hasattr(self, 'finishers'):
            for sf in self.finishers:
                if hasattr(self, sf) and getattr(self, sf) is not None and hasattr(getattr(self, sf), 'finish'):
                    getattr(self, sf).finish()

    def import_check(self, py_context, name, valid_exts=None):
        try:
            npath = py_context.path.rel_path(name)
        except AssertionError as e:
            raise UserError(LoaderImportError('path imports must be relative {} -> {}'.format(
                                              py_context.path.src_rel_path, name)))
        if valid_exts is not None:
            if npath.extension not in valid_exts:
                raise UserError(LoaderImportError('expected file extension in ({}), got .{}'.format(
                                                  ', '.join(valid_exts), npath.extension)))

        if not npath.exists():
            raise UserError(LoaderImportError('file {} -> {} imported from {} does not exist'.format(
                                              npath.src_rel_path, npath.full_path, py_context.path.src_rel_path)))

        return npath

    def import_symbols(self, name, f_path, t_path, basename, f_ctx, t_module, exports, **kwargs):
        self.debug(2, 'importing {} ({}) into {}: {}'.format(f_path, name, t_path, repr(exports)))
        reserved_names = ()
        if '__reserved_names' in kwargs:
            reserved_names = kwargs['__reserved_names']
            del kwargs['__reserved_names']

        try:
            if len(exports) == 0:
                # import <f_ctx>
                curdict = t_module.__dict__
                pathcomp = basename.split('.')
                curpath = f_path.full_path.rsplit('/', len(pathcomp))[0]
                for p in pathcomp:
                    if p is pathcomp[-1]:
                        curdict[p] = f_ctx.get_module(**kwargs)
                    else:
                        curpath = os.path.join(curpath, p)
                        if p not in curdict:
                            curdict[p] = get_bare_module(p, curpath)
                        curdict = curdict[p].__dict__

            elif len(exports) == 1 and exports[0] == '*':
                # from <f_ctx> import *
                all = None
                imports = set()
                for sym in f_ctx.get_symnames(**kwargs):
                    if sym == '__all__':
                        # we simulate the __all__ in imported files
                        c_all = f_ctx.get_symbol(sym, **kwargs)
                        if isinstance(c_all, (list, tuple, set)):
                            all = c_all
                        continue
                    if sym in reserved_names:
                        # ignore imports of symbols that are inserted by us
                        continue
                    if sym.startswith('__') and sym.endswith('__'):
                        # ignore any internals
                        continue
                    imports.add(sym)

                for sym in imports:
                    if all is None or sym in all:
                        t_module.__dict__[sym] = f_ctx.get_symbol(sym, **kwargs)

            else:
                # from <f_ctx> import <foo>, <bar>
                for sym in exports:
                    assert sym != '*'
                    if isinstance(sym, tuple) and len(sym) == 2:
                        # <foo> as <f>
                        if sym[0] == '__builtins__' or sym[0] == '__all__' or sym[0] in reserved_names:
                            continue
                        t_module.__dict__[sym[1]] = f_ctx.get_symbol(sym[0], **kwargs)
                    else:
                        if sym == '__builtins__' or sym == '__all__' or sym in reserved_names:
                            continue
                        t_module.__dict__[sym] = f_ctx.get_symbol(sym, **kwargs)

        except AssertionError as e:
            if hasattr(f_path, 'src_rel_path') and hasattr(t_path, 'src_rel_path'):
                raise LoaderImportError("'*' is only allowed as the only export importing {} -> {} from {}".format(
                    name, f_path.src_rel_path, t_path.src_rel_path))
            raise LoaderImportError("'*' is only allowed as the only export importing {} -> {} from {}".format(
                name, f_path.full_path, t_path.full_path))

        except KeyError as e:
            if hasattr(f_path, 'src_rel_path') and hasattr(t_path, 'src_rel_path'):
                raise LoaderImportError('symbols not found importing {} -> {} from {}: {}'.format(
                    name, f_path.src_rel_path, t_path.src_rel_path, e))
            raise LoaderImportError('symbols not found importing {} -> {} from {}: {}'.format(
                name, f_path.full_path, t_path.full_path, e))

        except LoaderImportError as e:
            if hasattr(f_path, 'src_rel_path') and hasattr(t_path, 'src_rel_path'):
                raise LoaderImportError('problem importing {} -> {} from {}: {}'.format(
                    name, f_path.src_rel_path, t_path.src_rel_path, e))
            raise LoaderImportError('problem importing {} -> {} from {}: {}'.format(
                name, f_path.full_path, t_path.full_path, e))

    def add_dep(self, s_path, d_path=None):
        if hasattr(s_path, 'src_rel_path') and (d_path is None or hasattr(d_path, 'src_rel_path')):
            if s_path.src_rel_path not in self.deps:
                self.deps[s_path.src_rel_path] = set()
            if d_path is not None:
                self.debug(2, '{} depends on {}'.format(s_path, d_path))
                self.deps[s_path.src_rel_path].add(d_path.src_rel_path)
                self.check_deps()
        else:
            if s_path.full_path not in self.deps:
                self.deps[s_path.full_path] = set()
            if d_path is not None:
                self.debug(2, '{} depends on {}'.format(s_path, d_path))
                self.deps[s_path.full_path].add(d_path.full_path)
                self.check_deps()

    def get_or_add_file(self, f_path, comp_context_obj, args):
        if f_path.full_path in self.files:
            return self.files[f_path.full_path]
        self.add_dep(f_path)
        assert f_path.full_path not in self.files
        self.files[f_path.full_path] = comp_context_obj(*args)
        return self.files[f_path.full_path]

    def check_deps(self):
        checked = set()

        def _rec_check_deps(k, prev):
            if prev is None:
                prev = set()
            if k not in self.deps:
                return
            for nk in self.deps[k]:
                if nk in prev:
                    raise LoaderLoopException('Loop detected: {} imports {}'.format(nk, k))
                nprev = set((nk,))
                nprev.update(prev)
                _rec_check_deps(nk, nprev)
                checked.add(nk)

        for k in self.deps:
            if k not in checked:
                _rec_check_deps(k, None)
