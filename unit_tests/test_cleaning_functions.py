import unittest
from t2wml.parsing.cleaning_functions import *

class TestScripts(unittest.TestCase):
    def test_strip_whitespace(self):
        whitespace="\t  \w Hel l o?\tworld \t  "
        #TODO: add asserts
        assert ("xx"+strip_whitespace(whitespace)+"xx")=='xx\w Hel l o?\tworldxx'
        assert ("xx"+strip_whitespace(whitespace, where="everywhere")+"xx")=='xx\wHello?worldxx'
        assert ("xx"+strip_whitespace(whitespace, char="\t", where="left")+"xx")=='xx  \\w Hel l o?\tworld \t  xx'

    def test_remove_symbols(self):
        uni="Thanks 😊! (<hello>) חחחחⒶ"


    def test_remove_unicode(self):
        uni="Thanks 😊! (<hello>) חחחחⒶ"

    
    def test_remove_numbers(self):
        nums="123 hello1234hi 123"
        assert remove_numbers(nums) == " hello1234hi 123"
        assert remove_numbers(nums, numbers=[123], where=left_and_right) == " hello1234hi "
        assert remove_numbers(nums, numbers=[3, 34], where=everywhere) =="12 hello12hi 12"
    
    def test_normalize_whitespace(self):
        space="Helo  you hi   this"
        assert normalize_whitespace(space)=="Helo you hi this"
    
    def test_change_case(self):
        case="tHe QUiCK brown fox"
        assert change_case(case)=="The quick brown fox"
        assert change_case(case, "lower")=="the quick brown fox"
        assert change_case(case, "upper")=="THE QUICK BROWN FOX"
        assert change_case(case, "title")=="The Quick Brown Fox"
    
    def test_remove_long(self):
        long_str="QWERTYUIOPASDFGHJKLZXCVBNMQWERTYUIOPASDFGHJKLZXCVBNM"
        assert remove_long(long_str, 50)==""
        assert remove_long("Hello!", 50)=="Hello!"


if __name__ == '__main__':
    unittest.main()
