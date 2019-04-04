import unittest
from nose_parameterized import parameterized

from logistik.db import IDatabase
from logistik.db.manager import DatabaseManager


class ManagerHasInterfaceMethodsTest(unittest.TestCase):
    interface_methods = [key for key in IDatabase.__dict__.keys() if not key.startswith('_')]

    def setUp(self):
        self.manager_methods = set(
            [
                key for key in DatabaseManager.__dict__.keys()
                if not key.startswith('_') and callable(DatabaseManager.__dict__[key])
            ]
        )

    @parameterized.expand(interface_methods)
    def test_method_is_implemented(self, method):
        self.assertIn(method, self.manager_methods)


class ManagerHasOnlyInterfaceMethodsTest(unittest.TestCase):
    manager_methods = set(
        [
            key for key in DatabaseManager.__dict__.keys()
            if not key.startswith('_') and callable(DatabaseManager.__dict__[key])
        ]
    )

    def setUp(self):
        self.interface_methods = [key for key in IDatabase.__dict__.keys() if not key.startswith('_')]

    @parameterized.expand(manager_methods)
    def test_method_is_in_interface(self, method):
        self.assertIn(method, self.interface_methods)
