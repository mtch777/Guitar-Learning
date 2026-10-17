import unittest
from serve_private_review import byte_range


class RangeTests(unittest.TestCase):
    def test_closed_open_and_suffix_ranges(self):
        self.assertEqual(byte_range('bytes=10-19',100),(10,19))
        self.assertEqual(byte_range('bytes=10-',100),(10,99))
        self.assertEqual(byte_range('bytes=-10',100),(90,99))
        self.assertEqual(byte_range('bytes=0-500',100),(0,99))
    def test_invalid_and_multiple_ranges_rejected(self):
        for value in ('bytes=100-','bytes=9-1','bytes=-0','bytes=-','bytes=0-1,3-4','invalid'):
            with self.assertRaises(ValueError):byte_range(value,100)


if __name__=='__main__':unittest.main()
