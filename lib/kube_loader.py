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
import obj_registry

# backlink types
for k in kube_obj.KubeBaseObj.get_subclasses(non_abstract=False, include_self=False, depth_first=True):
    if k is kube_obj.KubeBaseObj or k is kube_obj.KubeObj or k is kube_obj.KubeSubObj:
        continue
    k._parent_types = {}

for k in kube_obj.KubeBaseObj.get_subclasses(non_abstract=False, include_self=False, depth_first=True):
    if k is kube_obj.KubeBaseObj or k is kube_obj.KubeObj or k is kube_obj.KubeSubObj:
        continue
    name = k.__name__
    for ct in k.get_child_types().values():
        for cct in ct.get_subclasses(non_abstract=False, include_self=True):
            cct._parent_types[name] = k
