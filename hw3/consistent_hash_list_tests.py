import unittest
from bootstrap import ConsistentHashManager
from utils.node import Node

class TestConsistentHashManager(unittest.TestCase):
    def setUp(self):
        self.list = ConsistentHashManager(1000000)

    def test_add_client(self):
        self.list.add_client(Node('192.168.1.21', 8080))    # 132091
        self.list.add_client(Node('192.168.1.4', 8080))     # 167735
        self.list.add_client(Node('192.168.1.6', 8080))     # 255802
        self.list.add_client(Node('192.168.1.11', 8080))    # 271062
        self.list.add_client(Node('192.168.1.35', 8080))    # 343889
        self.list.add_client(Node('192.168.1.71', 8080))    # 819644
        self.list.add_client(Node('192.168.1.1', 8080))     # 749440
        self.list.add_client(Node('192.168.1.61', 8080))    # 964953
        print(self.list)

        self.assertEqual(len(self.list), 8, 'incorrect length')

    def test_get_client(self):
        self.list.add_client(Node('192.168.1.21', 8080))    # 132091
        self.list.add_client(Node('192.168.1.4', 8080))     # 167735
        self.list.add_client(Node('192.168.1.71', 8080))    # 819644

        self.assertEqual(self.list.get_client(150000), Node('192.168.1.4', 8080), 'wrong client for hash')

    def test_get_client_end(self):
        # Test wrap around
        self.list.add_client(Node('192.168.1.11', 8080))    # 271062
        self.list.add_client(Node('192.168.1.35', 8080))    # 343889
        self.list.add_client(Node('192.168.1.71', 8080))    # 819644

        self.assertEqual(self.list.get_client(900000), Node('192.168.1.11', 8080), 'wrong client for hash')

    def test_get_client_start(self):
        self.list.add_client(Node('192.168.1.11', 8080))    # 271062
        self.list.add_client(Node('192.168.1.35', 8080))    # 343889
        self.list.add_client(Node('192.168.1.71', 8080))    # 819644

        self.assertEqual(self.list.get_client(20000), Node('192.168.1.11', 8080), 'wrong client for hash')


if __name__ == "__main__":
    unittest.main()