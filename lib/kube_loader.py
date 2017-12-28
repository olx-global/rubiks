# (c) Copyright 2017 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import sys

import kube_obj
if sys.version_info[0] == 2:
    import kube_objs
else:
    import kube_objs.__init__
kube_objs._loader()
