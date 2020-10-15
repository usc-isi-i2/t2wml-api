import unittest
from t2wml.parsing.cleaning_functions import *
import pandas as pd
import numpy as np

class TestScripts(unittest.TestCase):
    def test_ftfy(self):
        assert ftfy("schÃ¶n")=="schön"

    def test_strip_whitespace(self):
        whitespace="\t  \w Hel l o?\tworld \t  "
        assert ("xx"+strip_whitespace(whitespace)+"xx")=='xx\w Hel l o?\tworldxx'
        assert ("xx"+strip_whitespace(whitespace, where="everywhere")+"xx")=='xx\wHello?worldxx'
        assert ("xx"+strip_whitespace(whitespace, char="\t", where="start")+"xx")=='xx  \\w Hel l o?\tworld \t  xx'
    
    def test_normalize_whitespace(self):
        space="Helo  you hi\t this"
        assert normalize_whitespace(space)=="Helo you hi this"
        assert normalize_whitespace(space, tab=True)=="Helo\tyou\thi\tthis"
    
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

    def test_remove_numbers(self):
        nums="123 hello1234hi 123"
        assert remove_numbers(nums) == " hellohi "
        assert remove_numbers(nums, where=start) == " hello1234hi 123"

    def test_remove_letters(self):
        nums="hi123 hello1234hi 123"
        assert remove_letters(nums) == "1231234123"
        assert remove_letters(nums, where=start) == "123 hello1234hi 123"

    def test_padding(self):
        assert pad("שלום", 10, "ח") == "חחחחחחשלום"
        assert pad("My input", 12, "xo", where=end) == "My inputxoxo"
        assert pad("12345678", 11, "xo", where=start) == "xox12345678"
        assert pad("12345678", 11, "xo", where=end) == "12345678oxo"
        
    def test_make_ascii(self):
        uni="Thanks 😊! (<hello>) חחחחⒶ"
        assert make_ascii(uni) == "Thanks ! (<hello>) "
        assert make_ascii(uni, translate=True) == "Thanks ! (<hello>) khkhkhkh"


    def test_make_alphanumeric(self):
        uni="Thanks 😊! (<hello>) חחחחⒶ -1.2e10"
        assert make_alphanumeric(uni) == "Thankshelloחחחח12e10"
    
    def test_make_numeric(self):
        assert make_numeric("1.977$") == str(1.977)
        assert make_numeric("1.554.677,88€", decimal=",") == str(1554677.88)
        assert make_numeric("1.577E20") == "1.577e+20"
    
    def test_replace_regex(self):
        assert replace_regex("cats and dogs and cats", "cats", "turtles") == "turtles and dogs and turtles"
        assert replace_regex(" 30 456 e", "[^\d.-]", "") == "30456"
        assert replace_regex("123456790 ABC#%? .(朱惠英)", r'[^\x00-\x7f]', "") == "123456790 ABC#%? .()"
        assert replace_regex("dan dan dan", "dan", "bob", 1) == "bob dan dan"


def create_lambda(function, *args, **kwargs):
    new_func= lambda input: function(input, *args, **kwargs)
    return new_func

def compose(*fs):
    def composition(x):
        for f in fs:
            x = f(x)
        return x
    return composition

class TestDataFrame(unittest.TestCase):
    def test_ftfy_and_strip_whitespace(self):
        df=pd.DataFrame([["s\tc  hÃ¶n", "yogurt"],
                        ["loop", "loop"]])
        func_1=create_lambda(ftfy)
        func_2=create_lambda(strip_whitespace, where=everywhere)
        my_func=compose(func_1, func_2)
        output=df.apply(np.vectorize(my_func))
        assert output.iloc[0,0]=="schön"


    def test_normalize_whitespace(self):
        df= pd.DataFrame([["Helo  you hi\t this", "goruty"], ["Helo  you hi\t this", ""]])
        my_func=create_lambda(normalize_whitespace, tab=True)
        output=df.apply(np.vectorize(my_func))
        assert output.iloc[0,0]=="Helo\tyou\thi\tthis"
    
    def test_remove_numbers(self):
        df=pd.DataFrame([["123 hello1234hi 123", "yogurt"],
                        ["loop", "loop"]])
        my_func=create_lambda(remove_numbers, where=start)
        output=df.apply(np.vectorize(my_func))
        assert output.iloc[0,0]== " hello1234hi 123"
    
    
    def test_change_case(self):
        df=pd.DataFrame([
            ["Hello", "Yogurt"],
            ["Parsley", "Meep"]
        ])
        my_func=create_lambda(change_case, case='upper')
        output=df.apply(np.vectorize(my_func))
        assert output.iloc[0,0]=="HELLO"
    
    def test_truncate(self):
        df=pd.DataFrame([["QWERTYUIOPASDFGHJKLZXCVBNMQWERTYUIOPASDFGHJKLZXCVBNM", "yogurt"],
                        ["loop", "loop"]])
        my_func=create_lambda(truncate, 10)
        output=df.apply(np.vectorize(my_func))
        assert output.iloc[0,0]=="QWERTYUIOP"


    


if __name__ == '__main__':
    unittest.main()
