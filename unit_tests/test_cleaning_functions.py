import os
import unittest
import yaml
from pathlib import Path
from t2wml.spreadsheets.sheet import SpreadsheetFile
from t2wml.parsing.cleaning_functions import *
from t2wml.mapping.datamart_edges import clean_id
from t2wml.input_processing.clean_yaml_parsing import get_cleaned_dataframe
from t2wml.settings import t2wml_settings

t2wml_settings.cache_data_files_folder=None

class TestScripts(unittest.TestCase):
    def test_Clean_id(self):
        assert clean_id("My very happy LOVELY... yoga class? לחדגילדחג") == "my_very_happy_lovely_yoga_class"
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
        assert float(make_numeric("1.577E20")) == 1.577e+20
    
    def test_replace_regex(self):
        assert replace_regex("cats and dogs and cats", "cats", "turtles") == "turtles and dogs and turtles"
        assert replace_regex(" 30 456 e", r"[^\d.-]", "") == "30456"
        assert replace_regex("123456790 ABC#%? .(朱惠英)", r'[^\x00-\x7f]', "") == "123456790 ABC#%? .()"
        assert replace_regex("dan dan dan", "dan", "bob", 1) == "bob dan dan"

    def test_fill_empty(self):
        assert fill_empty("  ", "dog") == "dog"
        assert fill_empty("", "cat") == "cat"
        assert fill_empty("\t\t  \t", "mouse") == "mouse"




class TestDataFrame(unittest.TestCase):
    def test_yaml(self):
        t2wml_settings.cache_data_files_folder=None
        repo_folder = Path(__file__).parents[2]
        test_folder = os.path.join(
            repo_folder, "t2wml-api", "unit_tests", "ground_truth", "cleaning")
        yaml_file=os.path.join(test_folder, "cleaning.yaml")
        with open(yaml_file, 'r') as f:
            test= yaml.safe_load(f.read())

        filepath=os.path.join(test_folder, "cleaning.xlsx")
        sf = SpreadsheetFile(filepath)
        first_sheet_name=sf.sheet_names[0]
        first_sheet=sf[first_sheet_name]
        cleaned = get_cleaned_dataframe(first_sheet, test["cleaningMapping"])
        assert cleaned.iloc[0, 0]=="schön"
        assert cleaned.iloc[2, 8]=="QWERTYUIOP"
        assert cleaned.iloc[3, 4]=="00forpadding"



    


if __name__ == '__main__':
    unittest.main()
