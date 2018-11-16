# (c) Copyright 2017-2018 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import sys

from user_error import UserError
from var_types import VarEntity


class KubeObjValidationError(Exception):
    def __init__(self, obj, msg):
        self.obj = obj
        self.msg = msg

    def __str__(self):
        return "KubeObj validation failed for object {}: {}: got {}".format(self.obj.__class__.__name__,
                                                                            self.msg, repr(self.obj))


class KubeTypeValidationError(Exception):
    def __init__(self, obj, vstr, path, msg):
        self.obj = obj
        self.path = path
        self.vstr = vstr
        self.msg = msg

    def __str__(self):
        path = self.path
        if path is None:
            path = 'self'
        return "KubeType Validation failed for {}: expected {}, got {} ({}): {}".format(path, self.vstr,
                                                                                   self.obj.__class__.__name__,
                                                                                   repr(self.obj),
                                                                                   self.msg)


class KubeType(object):
    wrapper = False

    def __init__(self, *args):
        if self.wrapper:
            if len(args) != 1:
                raise TypeError("Expected 2 arguments for {}, got {:d}".format(self.__class__.__name__, len(args) + 1))
            self.wrap = self.__class__.construct_arg(args[0])
        else:
            if len(args) != 0:
                raise TypeError("Expected 1 argument for {}, got {:d}".format(self.__class__.__name__, len(args) + 1))

    @classmethod
    def construct_arg(cls, arg):
        if isinstance(arg, type):
            ret = arg()
        else:
            ret = arg

        if not isinstance(ret, KubeType):
            ret = Object(ret.__class__)

        return ret

    def original_type(self):
        if self.wrapper:
            return self.wrap.original_type()
        return None

    def name(self, render=None):
        if render is None:
            render = lambda x: x
        if self.wrapper:
            return '{}<{}>'.format(render(self.__class__.__name__), self.wrap.name(render=render))
        return render(self.__class__.__name__)

    def check_wrap(self, value, path):
        if self.wrapper:
            return self.wrap.check(value, path=path)
        return True

    def do_check(self, value, path):
        return False

    def check(self, value, path=None):
        if isinstance(value, VarEntity):
            ret = self.do_check(value.validation_value(), path=path)
        else:
            ret = self.do_check(value, path=path)

        if not ret and hasattr(self, 'validation_text'):
            raise UserError(KubeTypeValidationError(value, self.name(), path, self.validation_text))
        elif not ret:
            raise UserError(KubeTypeValidationError(value, self.name(), path, 'Validation failed'))

        return ret


class Object(KubeType):
    def __init__(self, cls):
        self.cls = cls

    def original_type(self):
        return self.cls

    def name(self, render=None):
        if render is None:
            render = lambda x: x
        return render(self.cls.__name__)

    def do_check(self, value, path):
        self.validation_text = "Not the right object type"
        if not isinstance(value, self.cls):
            return False
        self.validation_text = "Validation call failed"
        if hasattr(value, 'validate'):
            return value.validate(path)
        return True


class Nullable(KubeType):
    validation_text = "Expected type or None"
    wrapper = True

    def do_check(self, value, path):
        if value is None:
            return True
        return self.check_wrap(value, path)


class Boolean(KubeType):
    validation_text = "Expected boolean"

    def do_check(self, value, path):
        return value is True or value is False


class Enum(KubeType):
    def __init__(self, *args):
        self.enums = args

    def name(self, render=None):
        if render is None:
            render = lambda x: x

        def fake_repr(x):
            ret = repr(x)
            if ret.startswith("u'"):
                return render(ret[1:])
            return render(ret)

        return '{}({})'.format(render(self.__class__.__name__), ', '.join(map(fake_repr, self.enums)))

    def do_check(self, value, path):
        return value in self.enums


class Integer(KubeType):
    validation_text = "Expected integer"

    def do_check(self, value, path):
        if value is True or value is False:
            return False
        if sys.version_info[0] == 2:
            return isinstance(value, (int, long))
        return isinstance(value, int)


class Number(KubeType):
    validation_text = "Expected number"

    def do_check(self, value, path):
        if value is True or value is False:
            return False
        if sys.version_info[0] == 2:
            return isinstance(value, (int, long, float))
        return isinstance(value, (int, float))


class Positive(KubeType):
    validation_text = "Expected positive"
    wrapper = True

    def do_check(self, value, path):
        return self.check_wrap(value, path) and value >= 0


class NonZero(KubeType):
    validation_text = "Expected non-zero"
    wrapper = True

    def do_check(self, value, path):
        return self.check_wrap(value, path) and value != 0


class String(KubeType):
    validation_text = "Expected string"

    def do_check(self, value, path):
        if sys.version_info[0] == 2:
            return isinstance(value, basestring)
        return isinstance(value, str)


class SurgeSpec(KubeType):
    validation_text = "Expected surge/unavailable type ie integer or percent"

    def do_check(self, value, path):
        if value is None:
            return True

        if String().do_check(value, path):
            if len(value) < 2:
                return False
            if value.endswith('%') and value[:-1].isdigit() and int(value[:-1]) < 100:
                return True
            return False
        else:
            return Positive(Integer).do_check(value, path)


class SurgeError(Exception):
    pass


class SurgeCheck(object):
    @classmethod
    def validate(cls, surge, unavailable):
        def check_zero(v):
            if v is None:
                return True

            return (String().do_check(v, None) and int(v[:-1]) == 0) or (v == 0)

        if check_zero(surge) and check_zero(unavailable):
            raise UserError(SurgeError("maxSurge and maxUnavailable cannot both be zero"))

        return True


class IPv4(String):
    validation_text = "Expected an IPv4 address"

    def do_check(self, value, path):
        if not String.do_check(self, value, path):
            return False
        ip = value.split('.')
        if len(ip) != 4:
            return False
        def comp_ok(x):
            if x == '' or not x.isdigit():
                return False
            if x == '0':
                return True
            if x.startswith('0'):
                return False
            return int(x) <= 255
        if not all(map(comp_ok, ip)):
            return False
        if int(ip[0]) == 0 or int(ip[0]) == 127:
            return False
        return True


class IP(String):
    validation_text = "Expected an IP address"

    def do_check(self, value, path):
        return IPv4().do_check(value, path)  # or IPv6().do_check(value, path)


class Domain(String):
    validation_text = "Expected a domain name"

    def do_check(self, value, path):
        if not String.do_check(self, value, path):
            return False
        if IPv4().do_check(value, path):
            return True
        if value == 'localhost':
            return True
        dm = value.split('.')
        if len(dm) < 2:
            return False
        if all(map(lambda x: x.isdigit(), dm)):
            return False
        def comp_ok(x):
            if x == '' or x.strip('abcdefghijklmnopqrstuvwxyz-0123456789') != '':
                return False
            if x.startswith('-') or x.endswith('-'):
                return False
            return True
        return all(map(comp_ok, dm))


class WildcardDomain(Domain):
    validation_text = "Expected a domain name, with possible starting wildcard"

    def do_check(self, value, path):
        if not String.do_check(self, value, path):
            return False
        if IPv4().do_check(value, path):
            return True
        if value == 'localhost':
            return True
        if Domain.do_check(self, value, path):
            return True
        if value.startswith('*.') and not IPv4().do_check(value, path) and value[2:] != 'localhost' and \
                Domain.do_check(self, value[2:], path):
            return True
        return False


class Identifier(String):
    validation_text = "Identifiers should be <253 chars and lc alphanum or . or -"

    def do_check(self, value, path):
        if not String.do_check(self, value, path):
            return False
        id_chars = 'abcdefghijklmnopqrstuvwxyz0123456789.-'
        if len(value) == 0 or len(value) > 253:
            return False
        for v in value:
            if v not in id_chars:
                return False
        return True


class CaseIdentifier(Identifier):
    validation_text = "Identifiers should be <253 chars and alphanum or . or -"

    def do_check(self, value, path):
        if not String.do_check(self, value, path):
            return False
        id_chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.-'
        if len(value) == 0 or len(value) > 253:
            return False
        for v in value:
            if v not in id_chars:
                return False
        return True


class SystemIdentifier(Identifier):
    validation_text = "Identifiers should be <253 chars and lc alphanum or . or - or :"

    def do_check(self, value, path):
        if not String.do_check(self, value, path):
            return False

        if value.startswith('system:'):
            id_chars = 'abcdefghijklmnopqrstuvwxyz0123456789.-:'
        else:
            id_chars = 'abcdefghijklmnopqrstuvwxyz0123456789.-'

        if len(value) == 0 or len(value) > 253:
            return False
        for v in value:
            if v not in id_chars:
                return False
        return True


class ColonIdentifier(Identifier):
    validation_text = "Identifiers should be <253 chars and lc alphanum or . or - and a :"

    def do_check(self, value, path):
        if not String.do_check(self, value, path):
            return False

        if len(value.split(':')) != 2:
            return False

        id_chars = 'abcdefghijklmnopqrstuvwxyz0123456789.-:'

        if len(value) == 0 or len(value) > 253:
            return False
        for v in value:
            if v not in id_chars:
                return False
        return True


class ARN(String):
    validation_text = "Amazon ARNs start with arn:aws:..."

    def do_check(self, value, path):
        if not String.do_check(self, value, path):
            return False
        if not value.startswith('arn:aws:') and not value.startswith('arn:aws-'):
            return False
        return True


class Path(String):
    validation_text = "Expecting a fully qualified path"

    def do_check(self, value, path):
        if not String.do_check(self, value, path):
            return False
        return value == '' or value.startswith('/')


class NonEmpty(KubeType):
    validation_text = "Expecting non-empty"

    wrapper = True

    def do_check(self, value, path):
        return self.check_wrap(value, path) and len(value) != 0


class OneOf(KubeType):
    def __init__(self, *types):
        assert len(types) > 1
        self.types = list(map(self.__class__.construct_arg, types))

    def name(self, render=None):
        if render is None:
            render = lambda x: x
        return render(self.__class__.__name__) + '<' + ', '.join(map(lambda x: x.name(render=render), self.types)) + '>'

    def original_type(self):
        # XXX this becomes complicated to do - for the moment assume none
        return None

    def check(self, value, path=None):
        if path is None:
            path = 'self'

        for t in self.types:
            try:
                if t.check(value, path):
                    return True
            except UserError as e:
                if not isinstance(e.exc, KubeTypeValidationError):
                    raise
            except KubeTypeValidationError:
                pass
        raise UserError(KubeTypeValidationError(value, self.name(), path,
                                                "couldn't match any possible types"))


class List(KubeType):
    validation_text = "Expecting list"

    wrapper = True

    def original_type(self):
        t = self.wrap.original_type()
        if t is not None:
            return [t]
        return None

    def do_check(self, value, path):
        if not isinstance(value, (list, tuple)):
            return False

        count = 0
        for v in value:
            if not self.check_wrap(v, path="{}[{:d}]".format(path, count)):
                return False
            count += 1

        return True


class Map(KubeType):
    def __init__(self, key, value):
        self.key = self.__class__.construct_arg(key)
        self.value = self.__class__.construct_arg(value)

    def name(self, render=None):
        if render is None:
            render = lambda x: x
        return '{}<{}, {}>'.format(render(self.__class__.__name__), self.key.name(render=render), self.value.name(render=render))

    def original_type(self):
        t = self.value.original_type()
        if t is not None:
            return {'value': t}
        return None

    def check(self, value, path=None):
        if not isinstance(value, dict):
            raise UserError(KubeTypeValidationError(value, self.name(), path, "not a dictionary"))

        if path is None:
            path = 'self'

        for k in value.keys():
            self.key.check(k, path='{}[{}] (key)'.format(path, k))
            self.value.check(value[k], path='{}[{}]'.format(path, k))

        return True
