import unittest
import os
import json
from pathlib import Path
from t2wml.utils.ethiopian_date import EthiopianDateConverter
from t2wml.wikification.utility_functions import add_entities_from_file
from t2wml.settings import t2wml_settings
from t2wml.api import KnowledgeGraph


class TestEthiopianCalendarModule(unittest.TestCase):      

    def test_gregorian_to_ethiopian(self):
        conv = EthiopianDateConverter.to_ethiopian
        self.assertEqual(conv(1982, 11, 21), (1975, 3, 12))
        self.assertEqual(conv(1941, 12, 7), (1934, 3, 28))
        self.assertEqual(conv(2010, 12, 22), (2003, 4, 13))

    def test_ethiopian_to_gregorian(self):
        conv = EthiopianDateConverter.to_gregorian
        self.assertEqual(conv(2003, 4, 11).strftime('%F'), '2010-12-20')
        self.assertEqual(conv(1975, 3, 12).strftime('%F'), '1982-11-21')
    
    def test_isostring_to_gregorian(self):
        isostring = '2000-01-01T00:00:00'
        gregorian=EthiopianDateConverter.iso_to_gregorian_iso(isostring)
        assert gregorian == "2007-09-12"


class TestEthiopianCalendarStatements(unittest.TestCase):
    def setUp(self):
        repo_folder = Path(__file__).parents[2]
        unit_test_folder = os.path.join(
            repo_folder, "t2wml-api", "unit_tests", "ground_truth")
        add_entities_from_file(os.path.join(
            unit_test_folder, "homicide", "homicide_properties.tsv"))
        self.data_file = os.path.join(
            unit_test_folder, "belgium-regex", "Belgium.csv")
        self.wikifier_file = os.path.join(
            unit_test_folder, "belgium-regex", "wikifier.csv")
        self.yaml_file = os.path.join(
            unit_test_folder, "belgium-regex", "Belgium2-ethiopian.yaml")
        self.expected_result_dir = os.path.join(
            unit_test_folder, "belgium-regex")

    def get_result(self):
        yaml_file = self.yaml_file
        sheet_name = "Belgium.csv"
        kg = KnowledgeGraph.generate_from_files(
            self.data_file, sheet_name, yaml_file, self.wikifier_file)
        return kg

    def test_01_replace(self):
        t2wml_settings.handle_calendar='replace'
        kg=self.get_result()
        assert kg.statements[(3,5)]['qualifier'][0]['value']=='2018-09-11'
        assert len(kg.statements[(3,5)]['qualifier'])==1

    def test_02_add(self):
        t2wml_settings.handle_calendar='add'
        kg=self.get_result()
        assert kg.statements[(3,5)]['qualifier'][0]['value']=='2011-01-01T00:00:00'
        assert kg.statements[(3,5)]['qualifier'][1]['value']=='2018-09-11'

    def test_03_leave(self):
        t2wml_settings.handle_calendar='leave'
        kg=self.get_result()
        assert kg.statements[(3,5)]['qualifier'][0]['value']=='2011-01-01T00:00:00'
        assert len(kg.statements[(3,5)]['qualifier'])==1
    


if __name__ == '__main__':
    unittest.main()