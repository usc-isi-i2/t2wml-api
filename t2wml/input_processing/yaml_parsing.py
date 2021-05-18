import yaml
import t2wml.utils.t2wml_exceptions as T2WMLExceptions
from t2wml.parsing.t2wml_parsing import T2WMLCode
from t2wml.utils.debug_logging import basic_debug


class ForwardSlashEscape(Exception):  # used for a little hack down below
    def __init__(self, new_str):
        self.new_str = new_str


class CodeParser:
    def fix_code_string(self, e_str):
        # we made various compromises between valid code from the get-go and easy for the user code.
        # this function transforms user code into python-acceptable code
        e_str = str(e_str)
        # deal with sheet-dependent reserved variables
        e_str = e_str.replace("$end", "t_var_sheet_end()")
        e_str = e_str.replace("$sheet", "t_var_sheet_name()")
        e_str = e_str.replace("$filename", "t_var_sheet_file_name()")
        # replace $row, $col, and $n with t_var_ equivalents ($ isn't valid python name but visually distinct for users)
        e_str = e_str.replace("$", "t_var_")
        # "condition and result" is equivalent to "if condition, result"
        e_str = e_str.replace("->", " and ")
        return e_str[1:]  # get rid of starting equal sign

    def is_code_string(self, statement):
        statement = str(statement)
        if statement[0] == "=":
            return True
        if statement[0] != "/":  # everything but the edge case
            return False

        # deal with edge cases involving escaping an initial equal sign
        # small hack: we use a forward slash escape error to avoid needing to return True/False
        # and instead catch and deal with it separately
        if "/=" not in statement:  # it just happens to start with a forward slash, nothing is being escaped
            return False
        else:
            i = 0
            while statement[i] == "/":
                i += 1
            # it has x number of forward slashes followed by an equal sign
            if statement[i] == "=":
                raise ForwardSlashEscape(statement[1:])
            # it happens to have /= somewhere in the string, but NOT in the beginning, eg ///hello /=you, return the whole thing
            return False


class TemplateParser(CodeParser):
    def __init__(self, template):
        self.template = template
        self.eval_template = self.create_eval_template(self.template)

    def get_code_replacement(self, input_str):
        try:
            if self.is_code_string(input_str):
                try:
                    fixed = self.fix_code_string(input_str)
                    compiled_statement = compile(fixed, "<string>", "eval")
                    return T2WMLCode(compiled_statement, fixed, input_str)
                except Exception as e:
                    raise T2WMLExceptions.ErrorInYAMLFileException(
                        "Invalid expression: "+str(input_str))
            else:
                return input_str
        except ForwardSlashEscape as e:
            return e.new_str
    
    def recursive_get_code_replacement(self, input):
            if isinstance(input, dict):
                for key in input:
                    input[key]=self.recursive_get_code_replacement(input[key])
                return input
            elif isinstance(input, list):
                for index, thing in enumerate(input):
                    input[index]=self.recursive_get_code_replacement(thing)
                return input
            else:
                return self.get_code_replacement(input)

    def create_eval_template(self, template):
        new_template = dict(template)
        self.recursive_get_code_replacement(new_template)
        return new_template


class Template:
    @basic_debug
    def __init__(self, dict_template, eval_template):
        self.dict_template = dict_template
        self.eval_template = eval_template

    @staticmethod
    def create_from_yaml(yaml_data):
        template = dict(yaml_data)
        template_parser = TemplateParser(template)
        eval_template = template_parser.eval_template
        return Template(template, eval_template)


def validate_yaml(yaml_file_path):
    with open(yaml_file_path, 'r', encoding="utf-8") as stream:
        try:
            yaml_file_data = yaml.safe_load(stream)
        except Exception as e:
            raise T2WMLExceptions.InvalidYAMLFileException(
                "Could not load Yaml File: "+str(e))

    with open(yaml_file_path, 'r', encoding="utf-8") as f:
        # some real quick security validation, lazy style
        content = f.read()
        if "import" in content:  # includes __import__ which is the real evil here
            raise T2WMLExceptions.InvalidYAMLFileException(
                "Could not load Yaml File: invalid T2wml code")

    errors = ""
    
    if 'statementMapping' not in yaml_file_data:
        errors += "Key 'statementMapping' not found\n"
    else:
        for key in yaml_file_data['statementMapping'].keys():
            if key not in {'region', 'template', 'created_by'}:
                errors += "Unrecognized key '" + key + \
                    "' (statementMapping -> " + key + ") found\n"

        if 'region' not in yaml_file_data['statementMapping']:
            errors += "Key 'region' (statementMapping -> X) not found\n"
        else:
            if yaml_file_data['statementMapping']['region']:
                yaml_region = yaml_file_data['statementMapping']['region']
                if isinstance(yaml_region, list):
                    yaml_file_data['statementMapping']['region']=yaml_region[0]
                    yaml_region=yaml_file_data['statementMapping']['region']
                    print("Deprecation Warning: region should no longer contain a list")
                        
                else:
                    for key in yaml_region.keys():
                            if key not in {'range', 'left', 'right', 'top', 'bottom', 'skip_rows', 'skip_columns', 'skip_cells', 'columns', 'rows', 'cells'}:
                                errors += "Unrecognized key '" + key + \
                                    "' (statementMapping -> region -> " + key + ") found\n"

                    for optional_list_key in ['skip_rows', 'skip_columns', 'skip_cells', 'columns', 'rows', 'cells']:
                        if optional_list_key in yaml_region:
                            if not isinstance(yaml_region[optional_list_key], list):
                                errors += "Value of key '"+optional_list_key+" should be a list.\n"
                    
            else:
                errors += "Value of key 'region' (statementMapping -> region) cannot be empty\n"

        if 'template' not in yaml_file_data['statementMapping']:
            errors += "Key 'template' (statementMapping -> X) not found\n"
        else:
            allowed_keys = {'subject', 'property', 'value', 'qualifier', 'reference',
                            'unit', 'lower-bound', 'upper-bound',  # Quantity
                            # Coordinate (+precision below)
                            'longitude', 'latitude', 'globe',
                            'calendar', 'precision', 'time_zone', 'format',  # Time
                            'lang',  # change to language? #Text
                            'region'
                            }
            yaml_template = yaml_file_data['statementMapping']['template']
            if isinstance(yaml_template, dict):
                try:
                    #backwards compatibility for versions before 0.0.18
                    subject= yaml_template.pop("item")
                    print("DeprecationWarning: using item key instead of subject key")
                    yaml_template["subject"]=subject
                except KeyError:
                    pass

                for key in yaml_template.keys():
                    if key not in allowed_keys:
                        errors += "Unrecognized key '" + key + \
                            "' (statementMapping -> template -> " + key + ") found\n"

                for required_key in ['subject', 'property', 'value']:
                    if required_key not in yaml_template:
                        errors += "Key '" + required_key + \
                            "' (statementMapping -> template -> X) not found\n"

                attributes = ['qualifier', 'reference']
                for attribute in attributes:
                    if attribute in yaml_template:
                        if yaml_template[attribute]:
                            if isinstance(yaml_template[attribute], list):
                                attributes = yaml_template[attribute]
                                for i in range(len(attributes)):
                                    obj = attributes[i]
                                    if obj and isinstance(obj, dict):
                                        for key in obj.keys():
                                            if key not in allowed_keys:
                                                errors += "Unrecognized key '" + key + \
                                                    "' (statementMapping -> template -> " + attribute + \
                                                    "[" + str(i) + "] -> " + \
                                                    key + ") found"
                                    else:
                                        errors += "Value of  key '" + attribute + "[" + str(i) + "]' (statementMapping -> template -> " + attribute + "[" + str(i) + "]) \
                                                must be a dictionary\n"

                            else:
                                errors += "Value of  key '" + attribute + \
                                    "' (statementMapping -> template -> " + \
                                    attribute + ") must be a list\n"
                        else:
                            errors += "Value of key '" + attribute + \
                                "' (statementMapping -> template -> " + \
                                attribute + ") cannot be empty\n"
            else:
                errors += "Value of  key 'template' (statementMapping -> template) must be a dictionary\n"

    if errors:
        raise T2WMLExceptions.ErrorInYAMLFileException(errors)

    return yaml_file_data
