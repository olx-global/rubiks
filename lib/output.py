# (c) Copyright 2017-2018 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os
import sys
import weakref

import kube_objs
import var_types
from kube_obj import KubeObj
from kube_yaml import yaml_safe_dump, yaml_safe_dump_all, yaml_load
from util import mkdir_p
from user_error import UserError


class RubiksOutputError(Exception):
    pass


class OutputCollection(object):
    def __init__(self, loader, repository, content_check=None):
        self.repository = repository
        self.clusterless = {}
        self.clustered = {}
        self.content_check = content_check
        self.cluster_mode = (len(self.repository.get_clusters()) != 0)
        self.loader = weakref.ref(loader)
        self.set_confidentiality_mode()

    def set_confidentiality_mode(self):
        self.confidential = ConfidentialOutput
        if hasattr(self.repository, 'confidentiality_mode') and self.repository.confidentiality_mode is not None:
            c_mode = self.repository.confidentiality_mode.lower()
            if c_mode not in ('gitignore', 'git-crypt', 'gitcrypt', 'no', 'none', 'hide', 'hidden',
                              'one-gitignore', 'single-gitignore', 'singlegitignore', 'gitignore-single',
                              'one-gitcrypt', 'single-gitcrypt', 'singlegitcrypt', 'git-crypt-single', 'gitcrypt-single'
                              ):
                print("WARNING: invalid repository configuration {}, ".format(repository.confidentiality_mode),
                      "should be one of 'gitignore(-single)', 'git-crypt(-single)', 'none', 'hidden'", file=sys.stderr)

            elif c_mode in ('git-crypt', 'gitcrypt'):
                self.confidential = ConfidentialOutputGitCrypt

            elif c_mode in ('one-gitcrypt', 'single-gitcrypt', 'singlegitcrypt', 'git-crypt-single', 'gitcrypt-single'):
                self.confidential = ConfidentialOutputSingleGitCrypt

            elif c_mode in ('gitignore',):
                self.confidential = ConfidentialOutputGitIgnore

            elif c_mode in ('one-gitignore', 'single-gitignore', 'singlegitignore', 'gitignore-single'):
                self.confidential = ConfidentialOutputSingleGitIgnore

            elif c_mode in ('hide', 'hidden'):
                self.confidential = ConfidentialOutputHidden
        self.debug(2, 'Set confidentiality mode to {}'.format(self.confidential.__name__))

    def debug(self, *args, **kwargs):
        self.loader().debug(*args, **kwargs)

    def add_output(self, kobj):
        if not isinstance(kobj, KubeObj):
            raise TypeError("argument to output should be a KubeObj derivative")

        cluster = None
        if self.cluster_mode:
            if kobj._in_cluster is not None:
                cluster = kobj._in_cluster.name

        op = OutputMember(self, kobj, cluster, content_check=self.content_check)
        if not op.is_namespace:
            self.add_output(op.kobj.namespace)

        if cluster is not None and cluster not in self.clustered:
            self.clustered[cluster] = {}

        if cluster is None:
            outputs = self.clusterless
        else:
            outputs = self.clustered[cluster]

        if op.namespace_name not in outputs:
            outputs[op.namespace_name] = {}
        outputs = outputs[op.namespace_name]

        self.check_for_dupes(op)

        if op.identifier not in outputs:
            outputs[op.identifier] = op

        outputs[op.identifier].render()

    def write_output(self):
        self.base = os.path.join(self.repository.basepath, self.repository.outputs)
        self.debug(2, "writing output to {}".format(self.base))
        if self.cluster_mode:
            return self._write_output_clustered()
        return self._write_output_clusterless()

    def _write_output_clustered(self):
        changed = []
        with self.confidential(self.base) as confidential:
            for c in self.repository.get_clusters():
                path = os.path.join(self.base, c)
                is_openshift = self.repository.is_openshift or self.repository.get_cluster_info(c).is_openshift
                uses_policybinding = self.repository.output_policybinding or \
                    self.repository.get_cluster_info(c).output_policybinding
                mkdir_p(path)

                ns_done = set()
                for ns in self.clusterless:
                    ns_done.add(ns)
                    outputs = []
                    outputs.extend(self.clusterless[ns].values())
                    if c in self.clustered and ns in self.clustered[c]:
                        outputs.extend(self.clustered[c][ns].values())

                    changed.extend(self._write_namespace(outputs, path, confidential,
                                                         is_openshift=is_openshift,
                                                         uses_policybinding=uses_policybinding,
                                                         ))

                if not c in self.clustered:
                    continue

                for ns in self.clustered[c]:
                    if ns in ns_done:
                        continue

                    changed.extend(self._write_namespace(self.clustered[c][ns].values(), path, confidential,
                                                         is_openshift=is_openshift,
                                                         uses_policybinding=uses_policybinding,
                                                         ))
        return changed

    def _write_output_clusterless(self):
        changed = []
        mkdir_p(self.base)
        with self.confidential(self.base) as confidential:
            for ns in self.clusterless:
                changed.extend(self._write_namespace(self.clusterless[ns].values(), self.base,
                                                     confidential, 
                                                     is_openshift=self.repository.is_openshift,
                                                     uses_policybinding=self.repository.output_policybinding,
                                                     ))
        return changed

    def _write_namespace(self, outputs, path, confidential, is_openshift=False, uses_policybinding=False):
        changed = []

        outputs_ns = tuple(filter(lambda x: x.uses_namespace, outputs))
        outputs_nons = tuple(filter(lambda x: not x.uses_namespace, outputs))

        if any(map(lambda x: x.has_data() and not x.is_namespace, outputs_ns)):
            stage_1 = []
            first = True
            for op in outputs_ns:
                if is_openshift and op.is_namespace:
                    if first:
                        stage_1.extend(self._get_openshift_objs(op))
                    first = False
                else:
                    stage_1.append(op)

            stage_2 = []
            rolebindings = []
            for op in stage_1:
                if uses_policybinding and isinstance(op.kobj, kube_objs.RoleBinding) and \
                        op.cached_obj.get('roleRef', {}).get('namespace', None) is not None:
                    rolebindings.append(op)
                else:
                    stage_2.append(op)

            if len(rolebindings) != 0:
                op = OutputMember(self, kube_objs.PolicyBinding(
                                      rolebindings[0].namespace.name + ':default',
                                      roleBindings=list(map(lambda x: x.kobj, rolebindings)),
                                      ),
                                  None, content_check=self.content_check,
                                  )
                op.kobj.set_namespace(rolebindings[0].namespace.name)
                op.namespace_name = rolebindings[0].namespace.name
                op.render()
                stage_2.append(op)

            for op in stage_2:
                p = op.write_file(path)
                if p is not None:
                    changed.append(p)
                confidential.add_file(op)

        for op in outputs_nons:
            if op.is_namespace:
                continue
            p = op.write_file(path)
            if p is not None:
                changed.append(p)
            confidential.add_file(op)

        return changed

    def _get_openshift_objs(self, ns_op):
        new_op = [ns_op]

        Project = kube_objs.Project
        RoleBinding = kube_objs.RoleBinding
        RoleSubject = kube_objs.RoleSubject

        # project
        op = OutputMember(self, Project.clone_from_ns(ns_op.kobj), None,
                          content_check=self.content_check)
        op.render()
        new_op.append(op)

        # image-pullers rolebinding
        op = OutputMember(
            self, RoleBinding('system:image-pullers', roleRef='system:image-puller',
                              subjects=[RoleSubject(kind='SystemGroup',
                                                    name='system:serviceaccounts:' + ns_op.kobj.name)]),
            None, content_check=self.content_check,
            )
        op.kobj.set_namespace(ns_op.kobj.name)
        op.namespace_name = ns_op.kobj.name
        op.render()
        new_op.append(op)

        # image-builders rolebinding
        op = OutputMember(
            self, RoleBinding('system:image-builders', roleRef='system:image-builder',
                              subjects=[RoleSubject(kind='ServiceAccount', name='builder')]),
            None, content_check=self.content_check,
            )
        op.kobj.set_namespace(ns_op.kobj.name)
        op.namespace_name = ns_op.kobj.name
        op.render()
        new_op.append(op)

        # deployer rolebinding
        op = OutputMember(
            self, RoleBinding('system:deployers', roleRef='system:deployer',
                              subjects=[RoleSubject(kind='ServiceAccount', name='deployer')]),
            None, content_check=self.content_check,
            )
        op.kobj.set_namespace(ns_op.kobj.name)
        op.namespace_name = ns_op.kobj.name
        op.render()
        new_op.append(op)

        return new_op

    def check_for_dupes(self, op):
        ret = self._check_for_dupes(op)
        if ret is None:
            return

        new_obj = op.namespace_name + '/' + op.identifier
        orig_obj = new_obj
        if op.cluster is None:
            new_obj = "<all clusters>:" + new_obj
        else:
            new_obj = op.cluster + ":" + new_obj

        if ret[0] is None:
            orig_obj = "<all clusters>:" + orig_obj
        else:
            orig_obj = ret[0] + ":" + orig_obj

        raise UserError(RubiksOutputError("Duplicate (different) objects found: (orig) {}, (added) {}".format(orig_obj, new_obj)))

    def _check_for_dupes(self, op):
        if op.cluster is None:
            nobj = None
            try:
                nobj = self.clusterless[op.namespace_name][op.identifier]
            except KeyError:
                pass
            if nobj is not None and not op.is_compatible(nobj):
                return (None,)

            for c in self.clustered:
                nobj = None
                try:
                    nobj = self.clustered[c][op.namespace_name][op.identifier]
                except KeyError:
                    pass
                if nobj is not None and not op.is_compatible(nobj):
                    return (c,)
        else:
            nobj = None
            try:
                nobj = self.clustered[op.cluster][op.namespace_name][op.identifier]
            except KeyError:
                pass
            if nobj is not None and not op.is_compatible(nobj):
                return (op.cluster,)

            nobj = None
            try:
                nobj = self.clusterless[op.namespace_name][op.identifier]
            except KeyError:
                pass
            if nobj is not None and not op.is_compatible(nobj):
                return (None,)

        return None


class OutputMember(object):
    def __init__(self, coll, kobj, cluster, content_check=None):
        self.kobj = kobj
        self.cluster = cluster
        self.content_check = content_check
        self.coll = weakref.ref(coll)

        self.is_namespace = isinstance(kobj, kube_objs.Namespace)
        self.is_confidential = False

        if self.is_namespace:
            self.namespace = kobj
        else:
            self.namespace = kobj.namespace

        self.namespace_name = self.namespace.name
        self.uses_namespace = kobj._uses_namespace

        self.identifier = str(kobj.kubectltype + '-' + getattr(kobj, kobj.identifier))

    def debug(self, *args, **kwargs):
        return self.coll().debug(*args, **kwargs)

    def is_compatible(self, obj):
        if obj.__class__ is not self.__class__:
            return False

        if obj.kobj.__class__ is not self.kobj.__class__:
            return False

        if self.kobj.__class__ is kube_objs.DockerCredentials:
            # we special case docker credentials because they're used as pull secrets
            # and this allows us to be cleverer about the pull secrets
            return self.kobj._data['dockers'] == obj.kobj._data['dockers']

        return self.kobj is obj.kobj

    def render(self):
        self.cached_obj = self.kobj.do_render()

    def has_data(self):
        if not hasattr(self, 'cached_obj'):
            self.render()
        return self.cached_obj is not None

    def yaml(self):
        if isinstance(self.cached_obj, list):
            self.cached_yaml = yaml_safe_dump_all(self.cached_obj, default_flow_style=False)
        else:
            self.cached_yaml = yaml_safe_dump(self.cached_obj, default_flow_style=False)

    def filename_conversion(self, filename):
        return filename.replace(':', '_')

    def write_file(self, path):
        if not hasattr(self, 'cached_obj') or self.kobj._always_regenerate:
            self.render()

        if self.cached_obj is None:
            return

        if not hasattr(self, 'cached_yaml'):
            self.yaml()

        if self.uses_namespace:
            path = os.path.join(path, self.namespace_name)
            mkdir_p(path)

        self.filedir = path
        self.filename = self.filename_conversion(self.identifier) + '.yaml'

        self.debug(3, "writing file {}/{}".format(self.filedir, self.filename))

        sav_context = var_types.VarContext.current_context
        var_types.VarContext.current_context = {'confidential': False}
        try:
            content = str(self.cached_yaml)
            self.is_confidential = var_types.VarContext.current_context['confidential']
        finally:
            var_types.VarContext.current_context = sav_context

        if self.is_confidential:
            self.debug(3, "  file {}/{} is confidential".format(self.filedir, self.filename))

        changed = False
        if self.content_check is not None and self.content_check in ('contents', 'yaml', 'exists'):
            try:
                with open(os.path.join(path, self.filename), 'rb') as f:
                    if self.content_check == 'contents':
                        if content != f.read().decode('utf8'):
                            changed = True
                    elif self.content_check == 'yaml':
                        if yaml_load(content) != yaml_load(f.read().decode('utf8')):
                            changed = True
            except:
                changed = True

        with open(os.path.join(path, '.' + self.identifier + '.tmp'), 'w') as f:
            f.write(content)
        os.rename(os.path.join(path, '.' + self.identifier + '.tmp'),
                  os.path.join(path, self.filename))

        if changed:
            return os.path.join(path, self.filename)
        return None


class ConfidentialOutput(object):
    def __init__(self, basedir):
        pass

    def add_file(self, output_file):
        pass

    def generate(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, etyp, evalue, etb):
        self.generate()
        return False


class ConfidentialOutputHidden(ConfidentialOutput):
    def __enter__(self):
        self.show_confidential = var_types.VarContext.show_confidential
        var_types.VarContext.show_confidential = False
        return self

    def __exit__(self, etyp, evalue, etb):
        var_types.VarContext.show_confidential = self.show_confidential
        self.generate()
        return False


class ConfidentialOutputGitMgmt(ConfidentialOutput):
    line = '# --- rubiks managed, do not edit below this line ---'
    single = False

    def __init__(self, basedir):
        self.gitmgmt = {}
        self.basedir = basedir

    def add_file(self, output_file):
        if output_file.is_confidential:
            if output_file.filedir not in self.gitmgmt:
                self.gitmgmt[output_file.filedir] = set()
            self.gitmgmt[output_file.filedir].add(output_file.filename)

    def gen_line(self, f):
        return f

    def generate(self):
        if not self.single:
            return generate_multi()

        try:
            with open(os.path.join(self.basedir, self.file)):
                lines = f.read().splitlines()
        except:
            lines = []

        try:
            lines = lines[:lines.index(self.line)]
        except ValueError:
            pass

        lines.append(self.line)

        for gmp in sorted(self.gitmgmt):
            relpath = os.path.relpath(gmp, self.basedir)
            assert not relpath.startswith('../')
            lines.extend(map(lambda x: self.gen_line('/' + relpath + '/' + x), sorted(self.gitmgmt[gmp])))

        with open(os.path.join(self.basedir, self.file + '.tmp'), 'w') as f:
            f.write('\n'.join(lines) + '\n')
        os.rename(os.path.join(self.basedir, self.file + '.tmp'), os.path.join(self.basedir, self.file))

    def generate_multi(self):
        for gmp in self.gitmgmt:
            try:
                with open(os.path.join(gmp, self.file)) as f:
                    lines = f.read().splitlines()
            except:
                lines = []

            try:
                lines = lines[:lines.index(self.line)]
            except ValueError:
                pass

            lines.append(self.line)
            lines.extend(map(lambda x: self.gen_line('/' + x), sorted(self.gitmgmt[gmp])))

            with open(os.path.join(gmp, self.file + '.tmp'), 'w') as f:
                f.write('\n'.join(lines) + '\n')
            os.rename(os.path.join(gmp, self.file + '.tmp'), os.path.join(gmp, self.file))


class ConfidentialOutputGitIgnore(ConfidentialOutputGitMgmt):
    file = '.gitignore'


class ConfidentialOutputSingleGitIgnore(ConfidentialOutputGitIgnore):
    single = True


class ConfidentialOutputGitCrypt(ConfidentialOutputGitMgmt):
    file = '.gitattributes'

    def gen_line(self, f):
        return f + ' diff=git-crypt filter=git-crypt'


class ConfidentialOutputSingleGitCrypt(ConfidentialOutputGitCrypt):
    single = True
