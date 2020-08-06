import os
import unittest
from pathlib import Path

repo_folder = Path(__file__).parents[2]
dataset_folder = os.path.join(repo_folder, "Datasets")
unit_test_folder = os.path.join(
    repo_folder, "t2wml-api", "unit_tests", "ground_truth")


class ClassesTest(unittest.TestCase):
    def test_wikifier(self):
        import pandas as pd
        from t2wml.api import Wikifier
        test_folder = os.path.join(unit_test_folder, "error-catching")
        wikifier_file = os.path.join(test_folder, "wikifier_1.csv")
        output_file = os.path.join(test_folder, "test_save_wf")

        wf = Wikifier()
        wf.add_file(wikifier_file)
        df = pd.DataFrame.from_dict({"column": [''], "row": [''],
                                     "value": 'Burundi', "item": ['Q99'], "context": ['']})
        wf.add_dataframe(df)
        wf.save(output_file)
        new_wf = Wikifier.load(output_file)
        item = new_wf.item_table.get_item_by_string('Burundi')
        new_wf.print_data()

    def test_wikifier_service(self):
        from t2wml.api import Wikifier, WikifierService, Sheet
        test_folder = os.path.join(unit_test_folder, "error-catching")
        data_file = os.path.join(test_folder, "input_1.csv")
        region = "A4:C8"
        sheet = Sheet(data_file, "input_1.csv")
        ws = WikifierService()
        df, problem_cells = ws.wikify_region(region, sheet)
        wf = Wikifier()
        wf.add_dataframe(df)
        wf.item_table.get_item(0, 5, sheet=sheet)

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
                    item = wikifier.item_table.get_item(col-1, row)
                    statement["item"] = item
                except Exception as e:
                    error["item"] = str(e)

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
        ym = YamlMapper(yaml_file)
        wf = Wikifier()
        wf.add_file(w_file)
        kg = KnowledgeGraph.generate(ym, sheet, wf)

class ProjectTest(unittest.TestCase):
    def test_project_single(self):
        from t2wml.api import ProjectRunner
        project_folder=os.path.join(unit_test_folder, "homicide")
        property_file=(os.path.join(
            unit_test_folder, "property_type_map.json"))
        sp=ProjectRunner(project_folder)
        sp.add_data_file("homicide_report_total_and_sex.xlsx")
        sp.add_property_file(property_file, copy_from_elsewhere=True, overwrite=True)
        sp.add_wikifier_file("wikifier_general.csv")
        sp.add_yaml_file(os.path.join("t2mwl","table-1a.yaml"))
        sp.associate_yaml_with_sheet(os.path.join("t2mwl","table-1a.yaml"), "homicide_report_total_and_sex.xlsx", "table-1a")
        save_file=sp.save()
        sp2=ProjectRunner.load(save_file)
        kg=sp2.generate_old_style_single_file_knowledge_graph("table-1a")
    
    def test_project_multi(self):
        import os
        from t2wml.api import ProjectRunner, SpreadsheetFile

        #part one:
        project_folder=os.path.join(unit_test_folder, "homicide")
        yaml_folder = os.path.join(project_folder, "t2mwl")
        property_file=(os.path.join(
            unit_test_folder, "property_type_map.json"))
        sp=ProjectRunner(project_folder)
        data_file1=sp.add_data_file("homicide_report_total_and_sex.xlsx")
        sp.add_property_file(property_file, copy_from_elsewhere=True, overwrite=True)
        sp.add_wikifier_file("wikifier_general.csv")
        for file_name in os.listdir(yaml_folder):
            yaml_file=os.path.join("t2mwl", file_name)
            sheet_name=file_name.split(".")[0]
            sp.add_yaml_file(yaml_file, data_file1, sheet_name)
        
        #part 2:
        test_folder = os.path.join(unit_test_folder, "loop")
        properties_file = os.path.join(test_folder, "kgtk_properties.tsv")
        sp.add_property_file(properties_file, copy_from_elsewhere=True, overwrite=True)
        data_file2 = sp.add_data_file(os.path.join(test_folder, "oecd.xlsx"), copy_from_elsewhere=True, overwrite=True)
        wikifier_filepath1 = os.path.join(test_folder, "country-wikifier.csv")
        sp.add_specific_wikifier_file(wikifier_filepath1, data_file2, copy_from_elsewhere=True, overwrite=True)
        yaml_filepath = sp.add_yaml_file(os.path.join(test_folder, "oecd.yaml"), copy_from_elsewhere=True, overwrite=True)
        spreadsheet_file=SpreadsheetFile(os.path.join(project_folder, "oecd.xlsx"))
        for sheet_name in spreadsheet_file:
            sp.associate_yaml_with_sheet(yaml_filepath, data_file2, sheet_name)

        save_file=sp.save()
        sp2=ProjectRunner.load(save_file)
        kgs=sp2.generate_all_knowledge_graphs()

        
        

        
if __name__ == '__main__':
    unittest.main()
