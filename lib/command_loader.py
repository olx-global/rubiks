# (c) Copyright 2017-2018 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import sys

import command
if sys.version_info[0] == 2:
    import commands
else:
    import commands.__init__
commands._loader()
