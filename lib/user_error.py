# (c) Copyright 2017-2018 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os
import sys
import traceback

__all__ = ['paths', 'UserError', 'user_errors', 'user_originated']

paths = ()


class fake_traceback(object):
    def __init__(self, tb=None):
        if tb is None:
            self.tb_next = None
            return

        for t in dir(tb):
            if t.startswith('tb_'):
                setattr(self, t, getattr(tb, t))


class fake_frame(object):
    def __init__(self, frame):
        for f in dir(frame):
            if f.startswith('f_'):
                setattr(self, f, getattr(frame, f))


class fake_code(object):
    def __init__(self, code):
        for co in dir(code):
            if co.startswith('co_'):
                setattr(self, co, getattr(code, co))


class UserError(Exception):
    def __init__(self, real_exc, f_file=None, f_line=None, f_fn=None, tb=None):
        assert isinstance(real_exc, Exception)
        self.exc = real_exc
        self.f_file = f_file
        self.f_line = f_line
        self.f_fn = f_fn
        self.tb = self._clone_tb(tb)

    def prepend_tb(self, tb):
        if self.tb is None:
            return
        ret = self._clone_tb(tb)
        cur = ret
        while cur.tb_next is not None:
            cur = cur.tb_next
        cur.tb_next = self.tb
        self.tb.tb_frame.f_back = cur.tb_frame
        self.tb = ret

    def _clone_tb(self, tb):
        if tb is None:
            return None
        ret = fake_traceback(tb)
        ret.tb_frame = fake_frame(ret.tb_frame)
        cur = ret
        while cur.tb_next is not None:
            cur.tb_next = fake_traceback(cur.tb_next)
            cur.tb_next.tb_frame = fake_frame(cur.tb_next.tb_frame)
            cur.tb_next.tb_frame.f_back = cur.tb_frame
            cur = cur.tb_next
        return ret

    def __str__(self):
        if self.f_file is not None:
            return "In originating code: " + str(self.exc)
        return str(self.exc)

    def __repr__(self):
        return "{}({})".format(self.__class__.__name__, repr(self.exc))


class UserInternalError(UserError):
    def __str__(self):
        return "while trying to process user code found {} exception internally: {}". \
            format(self.exc.__class__.__name__, str(self.exc))


def frame_in_paths(t, caller_fn=None):
    if len(os.getenv('RUBIKS_DEBUG', '')) > 0:
        return True

    pth = t.tb_frame.f_code.co_filename

    if caller_fn is not None and pth == caller_fn:
        return True

    for p in paths:
        if pth.startswith(p + '/'):
            return True

    return False


def user_originated(tb):
    while tb.tb_next is not None:
        tb = tb.tb_next
    return not frame_in_paths(tb)


def _filter_traceback(tb, caller_fn=None, fake_start_frame=None):
    finished = False

    ret = fake_traceback()
    cur = ret

    prev_frame = None
    if fake_start_frame is not None:
        fr = fake_frame(tb.tb_frame)
        fr.f_code = fake_code(fr.f_code)
        fr.f_code.co_filename = fake_start_frame[0]
        fr.f_code.co_name = fake_start_frame[2]
        fr.f_back = prev_frame
        cur.tb_next = fake_traceback(tb)
        cur.tb_next.tb_frame = fr
        cur.tb_next.tb_lineno = fake_start_frame[1]
        cur = cur.tb_next
        cur.tb_next = None
        prev_frame = fr

    while tb is not None:
        if not frame_in_paths(tb, caller_fn):
            cur.tb_next = fake_traceback(tb)

            cur = cur.tb_next
            cur.tb_next = None

            cur.tb_frame = fake_frame(cur.tb_frame)
            cur.tb_frame.f_back = prev_frame
            prev_frame = cur.tb_frame

        tb = tb.tb_next

    return ret.tb_next


class user_errors(object):
    def __init__(self, ignore_this=False, dont_filter=False):
        if ignore_this:
            self.caller_fn = traceback.extract_stack(limit=2)[0][0]
        else:
            self.caller_fn = None
        self.dont_filter = dont_filter

    def __enter__(self):
        return self

    def __exit__(self, etyp, evalue, etb):
        if etyp is None:
            return False

        if self.dont_filter:
            return False

        delayed = False
        exc = None

        if isinstance(evalue, UserError):
            if evalue.tb is not None:
                # UserError stored traceback, use that
                tb = _filter_traceback(evalue.tb, self.caller_fn)

            elif evalue.f_file is not None:
                # delayed exception in an object where we know the creation location
                tb = _filter_traceback(etb, self.caller_fn, (evalue.f_file, evalue.f_line, evalue.f_fn))
                delayed = True

            else:
                tb = _filter_traceback(etb, self.caller_fn)

            if tb is not None:
                exc = (evalue.exc.__class__, evalue.exc, tb)
            else:
                if evalue.tb is not None:
                    exc = (UserInternalError, UserInternalError(evalue.exc), evalue.tb)
                else:
                    exc = (UserInternalError, UserInternalError(evalue.exc), etb)

        elif isinstance(evalue, SyntaxError):
            tb = _filter_traceback(etb, self.caller_fn)
            exc = (evalue.__class__, evalue, tb)

        else:
            # we leave internal (non-user) exceptions to be handled by the system
            return False

        assert exc is not None

        out = ''.join(traceback.format_exception(*exc)).rstrip()

        if delayed:
            out = '  ' + '\n  '.join(out.split('\n'))
            print("Delayed exception originating:\n" + out, file=sys.stderr)
        else:
            print(out, file=sys.stderr)

        sys.exit(1)


def handle_user_error(e):
    if len(os.getenv('RUBIKS_DEBUG', '')) > 0 or isinstance(e, UserError):
        raise
    else:
        raise UserError(e)
