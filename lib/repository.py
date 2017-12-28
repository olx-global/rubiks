# (c) Copyright 2017 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os
import subprocess

class RepositoryError(Exception):
    pass

class Repository(object):
    """object representing the repository in which the compiler is run"""
    def __init__(self):
        self.find_worktree()
        self.populate_status()
        self.sources = 'sources'
        self.outputs = 'generated'

    def find_worktree(self):
        p = subprocess.Popen(['git', 'worktree', 'list', '--porcelain'],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        (out, err) = p.communicate()

        if p.returncode != 0:
            raise RepositoryError("Git error: " + err.strip())

        for l in out.splitlines():
            if l.startswith(b'worktree '):
                self.basepath = l.split(b' ', 1)[1].decode('utf8')
                return

        raise RepositoryError("No working tree found by git")

    def populate_status(self):
        self.status = GitStatus(self.basepath)

class GitFile(object):
    @classmethod
    def parse_line(cls, line, base):
        if line.startswith(b'1 '):
            return GitModifiedFile(line, base)
        elif line.startswith(b'2 '):
            cr = line.split(b' ', 8)[8][0]
            assert CR in (b'C', b'R')
            if cr == b'C':
                return GitCopiedFile(line, base)
            else:
                return GitRenamedFile(line, base)
        elif line.startswith(b'u '):
            return GitUnmergedFile(line, base)
        elif line.startswith(b'? '):
            return GitUntrackedFile(line[2:], base)
        else:
            return None

    def get_head_object(self):
        return None

    def get_index_object(self):
        return None

    def get_tree_object(self):
        try:
            with open(os.path.join(self.base, self.path)) as f:
                return f.read()
        except:
            pass
        return None

class GitUntrackedFile(GitFile):
    def __init__(self, path, base):
        self.path = path
        self.base = base

class GitAlteredFile(GitFile):
    def parse_xy(self, XY):
        fields = {b'.': 'unmodified', b'M': 'modified', b'A': 'added', b'D': 'deleted',
                  b'R': 'renamed', b'C': 'copied', b'U': 'unmerged'}

        if XY[0] in fields:
            self.index_state = fields[XY[0]]
        else:
            self.index_state = 'unknown'

        if XY[1] in fields:
            self.tree_state = fields[XY[1]]
        else:
            self.tree_state = 'unknown'

        self.in_merge = XY in (b'DD', b'AU', b'UD', b'UA', b'DU', b'AA', b'UU')

    def parse_submodule(self, sub):
        self.is_sub = False
        self.sub_commit_changed = False
        self.sub_tracked_changes = False
        self.sub_untracked_changes = False

        if sub.startswith(b'N'):
            assert sub == b'N...'
            return

        assert sub.startswith(b'S')
        self.is_sub = True

        if sub[1] == b'C':
            self.sub_commit_changed = True
        if sub[2] == b'M':
            self.sub_tracked_changes = True
        if sub[3] == b'U':
            self.sub_untracked_changes = True

    def get_head_object(self):
        if not hasattr(self, 'head_obj'):
            return None

        p = subprocess.Popen(['git', 'show', self.head_obj], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (out, err) = p.communicate()

        return out

    def get_index_object(self):
        if not hasattr(self, 'index_obj'):
            return None

        p = subprocess.Popen(['git', 'show', self.index_obj], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (out, err) = p.communicate()

        return out

class GitMultiAlteredFile(GitAlteredFile):
    def parse_expecting(self, line, char):
        if not line.startswith(b'2 '):
            raise ValueError("wrong type called on line")
        ll = line.split(b' ', 9)
        paths = ll[9].split(b'\0', 1)
        self.path = ll[9][0]
        self.orig_path = ll[9][1]
        assert ll[8][0] == char
        self.parse_xy(ll[1])
        assert not self.in_merge
        self.parse_submodule(ll[2])
        self.head_mode = int(ll[3], 8)
        self.index_mode = int(ll[4], 8)
        self.tree_mode = int(ll[5], 8)
        self.head_obj = ll[6].decode('utf8')
        self.index_obj = ll[7].decode('utf8')
        self.score = int(ll[8][1:])

class GitModifiedFile(GitAlteredFile):
    def __init__(self, line, base):
        if not line.startswith(b'1 '):
            raise ValueError("wrong type called on line")
        ll = line.split(b' ', 8)
        self.path = ll[8]
        self.base = base
        self.parse_xy(ll[1])
        assert not self.in_merge
        self.parse_submodule(ll[2])
        self.head_mode = int(ll[3], 8)
        self.index_mode = int(ll[4], 8)
        self.tree_mode = int(ll[5], 8)
        self.head_obj = ll[6].decode('utf8')
        self.index_obj = ll[7].decode('utf8')

class GitUnmergedFile(GitAlteredFile):
    def __init__(self, line, base):
        if not line.startswith(b'u '):
            raise ValueError("wrong type called on line")
        ll = line.split(b' ', 10)
        self.path = ll[10]
        self.base = base
        self.parse_xy(ll[1])
        assert self.in_merge
        self.parse_submodule(ll[2])
        self.stage1_mode = int(ll[3], 8)
        self.stage2_mode = int(ll[4], 8)
        self.stage3_mode = int(ll[5], 8)
        self.tree_mode = int(ll[6], 8)

class GitRenamedFile(GitMultiAlteredFile):
    def __init__(self, line, base):
        self.parse_expecting(line, b'R')
        self.base = base

class GitCopiedFile(GitMultiAlteredFile):
    def __init__(self, line, base):
        self.parse_expecting(line, b'C')
        self.base = base

class GitStatus(object):
    def __init__(self, base):
        self.current_commit = None
        self.current_branch = None
        self.upstream = None
        self.upstream_diff_us = 0
        self.upstream_diff_them = 0

        self.modifications = {}

        p = subprocess.Popen(['git', '-c', 'status.relativePaths=false', 'status',
                              '--branch', '-z', '--porcelain=v2'],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (out, err) = p.communicate()

        for l in out.split(b'\0'):
            if l.startswith(b'# '):
                ll = l.strip().split()
                if ll[1] == b'branch.oid':
                    self.current_commit = ll[2].decode('utf8')
                if ll[1] == b'branch.head':
                    self.current_branch = ll[2].decode('utf8')
                if ll[1] == b'branch.upstream':
                    self.current_upstream = ll[2].decode('utf8')
                if ll[1] == b'branch.ab':
                    if ll[2].startswith(b'+'):
                        self.upstream_diff_us = int(ll[2][1:])
                    if ll[3].startswith(b'-'):
                        self.upstream_diff_them = int(ll[3][1:])
            else:
                p = GitFile.parse_line(l, base)
                if p is not None:
                    self.modifications[p.path] = p
