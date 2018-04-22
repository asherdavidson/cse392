import unittest
from bootstrap import ConsistentHashList

class TestConsistentHashList(unittest.TestCase):
    def setUp(self):
        self.list = ConsistentHashList(1000000)

    def test_add_client(self):
        self.list.add_client('192.168.1.1')
        self.list.add_client('192.168.1.35')
        self.list.add_client('192.168.1.61')
        self.list.add_client('192.168.1.11')
        self.list.add_client('192.168.1.6')
        self.list.add_client('192.168.1.21')
        self.list.add_client('192.168.1.4')
        self.list.add_client('192.168.1.71')
        print(self.list)

        self.assertEqual(len(self.list), 8, 'incorrect length')


if __name__ == "__main__":
    unittest.main()