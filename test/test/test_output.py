# (c) Copyright 2018 OLX

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os
import subprocess
import tempfile
import unittest
import weakref

import python_path

import kube_objs
import loader
import output
import rubiks_repository

def mkdir_p(path):
    pass

output.mkdir_p = mkdir_p


class FakeOutputMember(object):
    def __init__(self, collection, identifier, cluster=None):
        self.is_confidential = False
        self.coll = weakref.ref(collection)
        self.kobj = None
        self.cluster = cluster
        self.content_check = None
        self.is_namespace = False
        self.namespace_name = 'testns'
        self.uses_namespace = True
        self.identifier = identifier
        self._has_data = True

    def has_data(self):
        return self._has_data

    def filename_conversion(self, filename):
        return filename.replace(':', '_')

    def write_file(self, path):
        if self.uses_namespace:
            path = os.path.join(path, self.namespace_name)
        self.coll().written.append(os.path.join(path, self.filename_conversion(self.identifier) + '.yaml'))


class BaseOutputTest(unittest.TestCase):
    def setUp(self):
        self.repo = rubiks_repository.RubiksRepository()
        self.collection = output.OutputCollection(loader.Loader(self.repo), self.repo)
        self.collection.confidential = output.ConfidentialOutput
        self.collection.written = []

        self.collection.clusterless['testns'] = {'namespace-testns': FakeOutputMember(self.collection, 'namespace-testns')}
        self.collection.clusterless['testns']['namespace-testns'].kobj = kube_objs.Namespace('testns')
        self.collection.clusterless['testns']['namespace-testns'].is_namespace = True
        self.collection.clusterless['testns']['namespace-testns'].cluster = None


class EasyClusterOutput(BaseOutputTest):
    def setUp(self):
        BaseOutputTest.setUp(self)

        self.collection.clustered['staging'] = {
            'testns': {
                'serviceaccount-deployer': FakeOutputMember(self.collection, 'serviceaccount-deployer', 'staging'),
                'rolebinding-deployer': FakeOutputMember(self.collection, 'rolebinding-deployer', 'staging'),
                'deployment-test1': FakeOutputMember(self.collection, 'deployment-test1', 'staging'),
                'deployment-test2': FakeOutputMember(self.collection, 'deployment-test2', 'staging'),
                'service-test1': FakeOutputMember(self.collection, 'service-test1', 'staging'),
                'secret-docker-pull': FakeOutputMember(self.collection, 'secret-docker-pull', 'staging'),
                }
            }

    def test_all_written(self):
        self.collection.base = 'projtest'
        self.collection._write_output_clustered()
        base = 'projtest/staging/testns/'
        self.assertEqual(sorted(self.collection.written), sorted([
            base + 'namespace-testns.yaml',
            base + 'serviceaccount-deployer.yaml',
            base + 'rolebinding-deployer.yaml',
            base + 'deployment-test1.yaml',
            base + 'deployment-test2.yaml',
            base + 'service-test1.yaml',
            base + 'secret-docker-pull.yaml',
            ]))
