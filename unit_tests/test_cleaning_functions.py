import unittest
from t2wml.parsing.cleaning_functions import *

class TestScripts(unittest.TestCase):
    def test_ftfy(self):
        assert ftfy("schÃ¶n")=="schön"

    def test_strip_whitespace(self):
        whitespace="\t  \w Hel l o?\tworld \t  "
        #TODO: add asserts
        assert ("xx"+strip_whitespace(whitespace)+"xx")=='xx\w Hel l o?\tworldxx'
        assert ("xx"+strip_whitespace(whitespace, where="everywhere")+"xx")=='xx\wHello?worldxx'
        assert ("xx"+strip_whitespace(whitespace, char="\t", where="start")+"xx")=='xx  \\w Hel l o?\tworld \t  xx'
    
    def test_normalize_whitespace(self):
        space="Helo  you hi\t this"
        assert normalize_whitespace(space)=="Helo you hi this"
        assert normalize_whitespace(space, tab=True)=="Helo\tyou\thi\tthis"
    
    def test_remove_numbers(self):
        nums="123 hello1234hi 123"
        assert remove_numbers(nums) == " hellohi "
        assert remove_numbers(nums, where=start) == " hello1234hi 123"
    
    
    def test_change_case(self):
        case="tHe QUiCK brown fox"
        assert change_case(case)=="The quick brown fox"
        assert change_case(case, "lower")=="the quick brown fox"
        assert change_case(case, "upper")=="THE QUICK BROWN FOX"
        assert change_case(case, "title")=="The Quick Brown Fox"
    
    def test_truncate(self):
        long_str="QWERTYUIOPASDFGHJKLZXCVBNMQWERTYUIOPASDFGHJKLZXCVBNM"
        assert truncate(long_str, 50) == "QWERTYUIOPASDFGHJKLZXCVBNMQWERTYUIOPASDFGHJKLZXCVB"
        assert truncate("Hello!", 50)=="Hello!"
    
    def test_padding(self):
        assert pad("שלום", 10, "ח") == "חחחחחחשלום"
        assert pad("My input", 12, "xx", where=end) == "My inputxxxx"
        #TODO: uneven padding
        
    def test_remove_symbols(self):
        uni="Thanks 😊! (<hello>) חחחחⒶ"


    def test_remove_unicode(self):
        uni="Thanks 😊! (<hello>) חחחחⒶ"
if __name__ == '__main__':
    unittest.main()
