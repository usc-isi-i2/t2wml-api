from abc import ABC, abstractmethod
import json
import yaml
import multiprocessing as mp
import t2wml.utils.t2wml_exceptions as T2WMLExceptions
from t2wml.mapping.statements import EvaluatedStatement, PartialStatement, StatementError
from t2wml.utils.bindings import update_bindings, bindings
from t2wml.input_processing.yaml_parsing import validate_yaml, Template
from t2wml.input_processing.region import YamlRegion
from t2wml.input_processing.clean_yaml_parsing import get_cleaned_dataframe
from t2wml.input_processing.annotation_parsing import Annotation
from t2wml.input_processing.utils import string_is_valid
from t2wml.utils.debug_logging import basic_debug

class StatementMapper(ABC):
    """an abstract class for creating statementmapper classes. refer to the api documentation for more details.
    """
    @abstractmethod
    def get_cell_statement(self, col, row, do_init=False, sheet=None, wikifier=None, *args, **kwargs):
        raise NotImplementedError
    
    @abstractmethod
    def iterator(self, start_index=0, end_index=None):
        raise NotImplementedError

    def do_init(self, sheet, wikifier):
        pass

    #@basic_debug
    def get_statements(self, sheet, wikifier, start_index=0, end_index=None, count=None):
        self.do_init(sheet, wikifier)
        statements = {}
        cell_errors = {}
        metadata = {
            "data_file": sheet.data_file_name,
            "sheet_name": sheet.name,
        }

        i=0
        for col, row in self.iterator(start_index, end_index):
            errors=[]
            cell = (col-1, row-1)
            if string_is_valid(str(bindings.excel_sheet[row-1, col-1])):
                try:
                    statement, inner_errors = self.get_cell_statement(col, row, do_init=False)
                    if "value" in statement: #exclude empty statements
                        statements[cell] = statement
                    if inner_errors:
                        errors = inner_errors
                except T2WMLExceptions.TemplateDidNotApplyToInput as e:
                    errors = e.errors
                except Exception as e:
                    errors = [StatementError(message=str(e),
                                                       field="fatal",
                                                       level="Major")]
                if errors:
                    cell_errors[cell] = [error.__dict__ if isinstance(error, StatementError) else error for error in errors ]
            if i == count:
                break
            i+=1
        return statements, cell_errors, metadata


class YamlMapper(StatementMapper):
    """A StatementMapper class that uses a yaml file to create a template and region for processing data
    """
    def __init__(self, file_path):
        self.file_path = file_path
        self.yaml_data = validate_yaml(file_path)

    def do_init(self, sheet, wikifier):
        if self.yaml_data.get("cleaningMapping"):
            new_df=get_cleaned_dataframe(sheet, self.yaml_data["cleaningMapping"])
            sheet.cleaned_data=new_df
        update_bindings(item_table=wikifier.item_table, sheet=sheet)
        

    def get_cell_statement(self, col, row, do_init=False, sheet=None, wikifier=None):
        if do_init:
            self.do_init(sheet, wikifier)
        context = {"t_var_row": row, "t_var_col": col}
        statement = EvaluatedStatement(
            context=context, **self.template.eval_template)
        return statement.serialize(), statement.errors

    def iterator(self, start_index=0, end_index=None):
        region=YamlRegion(self.yaml_data['statementMapping']['region'])
        if end_index is None:
            end_index=max(region.index_dict)-1
        for row in range(start_index+1, end_index+2): #switch to 1-indexed...
            if row in region.index_dict:
                for col in region.index_dict[row]:
                    yield col, row

    @property
    def template(self):
        try:
            return self._template
        except:
            self._template = Template.create_from_yaml(
                self.yaml_data['statementMapping']['template'])
            return self._template

class AnnotationMapper(YamlMapper):
    """A StatementMapper class that uses an annotation file to create a yaml text 
    """
    def __init__(self, file_path):
        self.init_annotation(file_path)
        if not self.annotation.potentially_enough_annotation_information:
            self.get_statements=self.empty_get_statements #override get_statements to not return anything
    
    def init_annotation(self, file_path):
        self.file_path = file_path
        with open(file_path, 'r') as f:
            annotation_blocks_arr=json.load(f)
        self.annotation=Annotation(annotation_blocks_arr)


    def do_init(self, sheet, wikifier):
        item_table=wikifier.item_table
        update_bindings(item_table=item_table, sheet=sheet)
        yamlContent=self.annotation.generate_yaml(sheet=sheet, item_table=item_table)[0]
        self.yaml_data = yaml.safe_load(yamlContent)

    
    def empty_get_statements(self, sheet, wikifier, *args, **kwargs):
        statements = {}
        cell_errors = []
        metadata = {
            "data_file": sheet.data_file_name,
            "sheet_name": sheet.name,
        }
        return statements, cell_errors, metadata

class PartialAnnotationMapper(AnnotationMapper):
    def __init__(self, file_path):
        self.init_annotation(file_path)
        if not self.annotation.data_annotations:
            self.get_statements=self.empty_get_statements

    def get_cell_statement(self, col, row, do_init=False, sheet=None, wikifier=None):
        if do_init:
            self.do_init(sheet, wikifier)
        context = {"t_var_row": row, "t_var_col": col}
        statement = PartialStatement(context=context, **self.template.eval_template)
        serialized_statement=statement.serialize()
        if "value" not in serialized_statement: #circumvent the check against empty values
            serialized_statement["value"]=""
        return serialized_statement, statement.errors
    

