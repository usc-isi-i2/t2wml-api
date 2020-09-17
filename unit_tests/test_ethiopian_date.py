import unittest
from t2wml.utils.ethiopian_date import EthiopianDateConverter


class TestEthiopianCalendar(unittest.TestCase):      

    def test_gregorian_to_ethiopian(self):

        conv = EthiopianDateConverter.to_ethiopian
        self.assertEqual(conv(1982, 11, 21), (1975, 3, 12))
        self.assertEqual(conv(1941, 12, 7), (1934, 3, 28))
        self.assertEqual(conv(2010, 12, 22), (2003, 4, 13))

    def test_ethiopian_to_gregorian(self):

        conv = EthiopianDateConverter.to_gregorian
        self.assertEqual(conv(2003, 4, 11).strftime('%F'), '2010-12-20')
        self.assertEqual(conv(1975, 3, 12).strftime('%F'), '1982-11-21')


if __name__ == '__main__':
    unittest.main()