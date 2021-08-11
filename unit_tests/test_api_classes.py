import os
from t2wml.wikification.wikidata_provider import DictionaryProvider
import pandas as pd
from t2wml.api import Sheet
from t2wml.wikification.item_table import convert_old_wikifier_to_new
from t2wml.utils.t2wml_exceptions import FileNotPresentInProject
import unittest
from pathlib import Path

repo_folder = Path(__file__).parents[2]
dataset_folder = os.path.join(repo_folder, "Datasets")
unit_test_folder = os.path.join(
    repo_folder, "t2wml-api", "unit_tests", "ground_truth")


class ClassesTest(unittest.TestCase):
    def test_wikifier(self):
        import pandas as pd
        from t2wml.api import Wikifier, Sheet
        test_folder = os.path.join(unit_test_folder, "error-catching")
        wikifier_file = os.path.join(test_folder, "wikifier_1.csv")
        sheet = Sheet(os.path.join(test_folder, "input_1.csv"), "input_1.csv")
        #convert_old_wikifier_to_new(wikifier_file, sheet, wikifier_file)

        output_file = os.path.join(test_folder, "test_save_wf")

        wf = Wikifier()
        wf.add_file(wikifier_file)
        df = pd.DataFrame.from_dict({"column": ['0'], "row": ['5'],
                                     "value": 'Comoros', "item": ['Q99'], "context": [''], 
                                     "file":["input_1.csv"], "sheet":["input_1.csv"]})
        wf.add_dataframe(df)
        wf.save(output_file)
        new_wf = Wikifier.load(output_file)
        assert new_wf.item_table.get_item(0, 3, sheet=sheet) == "Q967"
        assert new_wf.item_table.get_item(0, 5, sheet=sheet) == "Q99"


    def test_custom_statement_mapper(self):
        from t2wml.mapping.statement_mapper import StatementMapper
        from t2wml.api import KnowledgeGraph, Wikifier, Sheet

        class SimpleSheetMapper(StatementMapper):
            def __init__(self, cols, rows):
                self.cols = cols
                self.rows = rows

            def iterator(self):
                for col in self.cols:
                    for row in self.rows:
                        yield(col, row)

            def get_cell_statement(self, sheet, wikifier, col, row, *args, **kwargs):
                error = {}
                statement = {}
                try:
                    item = wikifier.item_table.get_item(col-1, row, sheet=sheet)
                    statement["subject"] = item
                except Exception as e:
                    error["subject"] = str(e)

                try:
                    value = sheet[col, row]
                    statement["value"] = value
                except Exception as e:
                    error["value"] = str(e)

                statement["property"] = "P123"

                return statement, error

        test_folder = os.path.join(unit_test_folder, "custom_classes")
        data_file = os.path.join(test_folder, "Book1.xlsx")
        sheet_name = "Sheet1"
        wikifier_file = os.path.join(test_folder, "wikifier_1.csv")
        

        ym = SimpleSheetMapper([1, 3], [2, 3, 4, 5, 6, 7])
        sh = Sheet(data_file, sheet_name)
        #convert_old_wikifier_to_new(wikifier_file, sh, wikifier_file)
        wf = Wikifier()
        wf.add_file(wikifier_file)
        kg = KnowledgeGraph.generate(ym, sh, wf)

    def test_basic_imports(self):
        from t2wml.api import KnowledgeGraph, YamlMapper, Wikifier, Sheet, SpreadsheetFile
        test_folder = os.path.join(unit_test_folder, "error-catching")
        data_file = os.path.join(test_folder, "input_1.csv")
        yaml_file = os.path.join(test_folder, "error.yaml")
        w_file = os.path.join(test_folder, "wikifier_1.csv")

        sheet = Sheet(data_file, "input_1.csv")
        #convert_old_wikifier_to_new(w_file, sheet, w_file)
        ym = YamlMapper(yaml_file)
        wf = Wikifier()
        wf.add_file(w_file)
        kg = KnowledgeGraph.generate(ym, sheet, wf)

class ProjectTest(unittest.TestCase):
    def test_project_asingle(self):
        from t2wml.api import Project
        project_folder=os.path.join(unit_test_folder, "homicide")
        sp=Project(project_folder)
        sp.add_data_file("homicide_report_total_and_sex.xlsx")
        sp.add_entity_file("homicide_properties.tsv")
        wikifier_file = os.path.join(project_folder, "unit_wikifier_general.csv")
        sh = Sheet(os.path.join(project_folder, "homicide_report_total_and_sex.xlsx"), "table-1a")
        #convert_old_wikifier_to_new(wikifier_file, sh, wikifier_file)
        df = pd.read_csv(wikifier_file)
        sp.add_df_to_wikifier_file("homicide_report_total_and_sex.xlsx", df)
        yaml_file=sp.add_yaml_file(os.path.join("t2wml","table-1a.yaml"))
        sp.associate_yaml_with_sheet(yaml_file, "homicide_report_total_and_sex.xlsx", "table-1a")
        save_file=sp.save()

    
    def test_project_multi(self):
        import os
        from t2wml.api import Project, SpreadsheetFile

        #part one:
        project_folder=os.path.join(unit_test_folder, "homicide")
        yaml_folder = os.path.join(project_folder, "t2wml")

        sp=Project(project_folder)
        data_file1=sp.add_data_file("homicide_report_total_and_sex.xlsx")
        sp.add_entity_file("homicide_properties.tsv")
        wikifier_file = os.path.join(project_folder, "wikifier_general.csv")
        df = pd.read_csv(wikifier_file)
        sp.add_df_to_wikifier_file("homicide_report_total_and_sex.xlsx", df)
        for file_name in os.listdir(yaml_folder):
            yaml_file=os.path.join("t2wml", file_name)
            sheet_name=file_name.split(".")[0]
            try:
                sp.add_yaml_file(yaml_file, data_file1, sheet_name)
            except FileNotPresentInProject:
                pass #there are some yamls for sheets that dont exist    
        #part 2:
        test_folder = os.path.join(unit_test_folder, "loop")
        properties_file = os.path.join(test_folder, "kgtk_properties.tsv")
        sp.add_entity_file(properties_file, copy_from_elsewhere=True, overwrite=True)
        data_file2 = sp.add_data_file(os.path.join(test_folder, "oecd.xlsx"), copy_from_elsewhere=True, overwrite=True)
        yaml_filepath = sp.add_yaml_file(os.path.join(test_folder, "oecd.yaml"), copy_from_elsewhere=True, overwrite=True)
        spreadsheet_file=SpreadsheetFile(os.path.join(project_folder, "oecd.xlsx"))
        for sheet_name in spreadsheet_file:
            sp.associate_yaml_with_sheet(yaml_filepath, data_file2, sheet_name)

        save_file=sp.save()


        


        
if __name__ == '__main__':
    unittest.main()
