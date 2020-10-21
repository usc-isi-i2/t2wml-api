from abc import ABC, abstractmethod
import t2wml.utils.t2wml_exceptions as T2WMLExceptions
from t2wml.mapping.statements import EvaluatedStatement
from t2wml.utils.bindings import update_bindings
from t2wml.parsing.yaml_parsing import validate_yaml, Template
from t2wml.parsing.region import YamlRegion
from t2wml.parsing.clean_yaml_parsing import get_cleaned_dataframe
from t2wml.spreadsheets.conversions import to_excel


class StatementMapper(ABC):
    """an abstract class for creating statementmapper classes. refer to the api documentation for more details.
    """
    @abstractmethod
    def get_cell_statement(self, sheet, wikifier, col, row, *args, **kwargs):
        raise NotImplementedError
    
    @abstractmethod
    def iterator(self):
        raise NotImplementedError

    def do_init(self, sheet, wikifier):
        pass

    def get_all_statements(self, sheet, wikifier):
        self.do_init(sheet, wikifier)
        statements = {}
        cell_errors = {}
        metadata = {
            "data_file": sheet.data_file_name,
            "sheet_name": sheet.name,
        }

        for col, row in self.iterator():
            cell = to_excel(col-1, row-1)
            try:
                statement, inner_errors = self.get_cell_statement(
                    sheet, wikifier, col, row, do_init=False)
                statements[cell] = statement
                if inner_errors:
                    cell_errors[cell] = inner_errors
            except T2WMLExceptions.TemplateDidNotApplyToInput as e:
                cell_errors[cell] = e.errors
            except Exception as e:
                cell_errors[cell] = str(e)

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
        

    def get_cell_statement(self, sheet, wikifier, col, row, do_init=True):
        if do_init:
            self.do_init(sheet, wikifier)
        context = {"t_var_row": row, "t_var_col": col}
        statement = EvaluatedStatement(
            context=context, **self.template.eval_template)
        return statement.serialize(), statement.errors

    def iterator(self):
        region=YamlRegion(self.yaml_data['statementMapping']['region'][0])
        for col, row in region:
            yield col, row

    @property
    def template(self):
        try:
            return self._template
        except:
            self._template = Template.create_from_yaml(
                self.yaml_data['statementMapping']['template'])
            return self._template
