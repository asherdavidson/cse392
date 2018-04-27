import unittest
from bootstrap import ConsistentHashManager

class TestConsistentHashManager(unittest.TestCase):
    def setUp(self):
        self.list = ConsistentHashManager(1000000)

    def test_add_client(self):
        self.list.add_client('192.168.1.1')     # 280952
        self.list.add_client('192.168.1.35')    # 957443
        self.list.add_client('192.168.1.61')    # 925877
        self.list.add_client('192.168.1.11')    # 187424
        self.list.add_client('192.168.1.6')     # 809407
        self.list.add_client('192.168.1.21')    # 788830
        self.list.add_client('192.168.1.4')     # 267522
        self.list.add_client('192.168.1.71')    #  30457
        print(self.list)

        self.assertEqual(len(self.list), 8, 'incorrect length')

    def test_get_client(self):
        self.list.add_client('192.168.1.21')    # 788830
        self.list.add_client('192.168.1.4')     # 267522
        self.list.add_client('192.168.1.71')    #  30457

        self.assertEqual(self.list.get_client(50252), '192.168.1.4', 'wrong client for hash')

    def test_get_client_end(self):
        # Test wrap around
        self.list.add_client('192.168.1.21')    # 788830
        self.list.add_client('192.168.1.4')     # 267522
        self.list.add_client('192.168.1.71')    #  30457

        self.assertEqual(self.list.get_client(800000), '192.168.1.71', 'wrong client for hash')

    def test_get_client_start(self):
        self.list.add_client('192.168.1.21')    # 788830
        self.list.add_client('192.168.1.4')     # 267522
        self.list.add_client('192.168.1.71')    #  30457

        self.assertEqual(self.list.get_client(20000), '192.168.1.71', 'wrong client for hash')


if __name__ == "__main__":
    unittest.main()