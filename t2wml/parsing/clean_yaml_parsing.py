from pathlib import Path
import pandas as pd
import numpy as np
from t2wml.parsing.region import YamlRegion
from t2wml.spreadsheets.sheet import Sheet
from t2wml.utils.t2wml_exceptions import InvalidYAMLFileException
from t2wml.parsing.cleaning_functions import cleaning_functions_dict
from t2wml.utils.bindings import update_bindings

def create_lambda(function_name, *args, **kwargs):
    function=cleaning_functions_dict[function_name]
    new_func= lambda input: function(input, *args, **kwargs)
    return new_func

def compose(*fs):
    def composition(x):
        for f in fs:
            x = f(x)
        return x
    return composition


def clean_sheet(cleaning_mappings, sheet):
    update_bindings(sheet=sheet)
    validate_cleaning_yaml(cleaning_mappings)
    parsing_instructions=[]
    for index, mapping in enumerate(cleaning_mappings):
        region=YamlRegion(mapping["region"])
        functions=mapping["functions"]
        parsed_funcs=[]
        for function in functions:
            if isinstance(function, dict):
                for function_name, kwargs in function.items():
                    break
            else:
                function_name=function
                kwargs={}
            parsed_func = create_lambda(function_name, **kwargs)
            parsed_funcs.append(parsed_func)
        final_func=compose(*parsed_funcs) 
        parsing_instructions.append({"region":region, "parsed_func":final_func})

    df=sheet.data.copy(deep=True)

    for instruction in parsing_instructions:
        region = instruction["region"]
        cells= set(region.index_pairs)
        parsed_func=instruction["parsed_func"]
        for col, row in region:
            col=col-1
            row=row-1
            new_val=parsed_func(df.iloc[row, col])
            df.iat[row, col]=new_val
            #output=df.apply(np.vectorize(my_func))
    
    cleaned_file_name=Path(sheet.data_file_name).stem +"_"+sheet.name + "_cleaned.csv"
    cleaned_file_folder=Path(sheet.data_file_path).parent / "cleaned"
    cleaned_file_folder.mkdir(exist_ok=True)
    cleaned_file_path=str(cleaned_file_folder / cleaned_file_name)
    df.to_csv(cleaned_file_path, header=False, index=False)
    cleaned_sheet=Sheet(data_file_path=cleaned_file_path, sheet_name=cleaned_file_name, data=df)
    return cleaned_sheet


base_yaml_string="""
statementMapping: ""
cleaningMapping:
       - region: range: D6:K20
         functions:
            - ftfy
            - strip_whitespace:
                char: null # default all whitespace, can also be " " or  "\t"
                where: start_and_end
            - replace_regex:
                to_replace: #required, no default
                replacement: #required, no default
            - remove_numbers:
                where: everywhere
            - remove_letters:
                where: everywhere
            - truncate:
                length: #required, no default
            - normalize_whitespace:
                tab: False
            - change_case:
                case: "sentence" #can also be "lower", "upper", and "title"
            - pad:
                length: #required, no default
                pad_text: #required, no default
                where: start # or "end". does not allow "everywhere" or "start_and_end"
            - make_numeric:
                decimal: "."
            - make_alphanumeric
            - make_ascii:
                translate: False
"""



def validate_cleaning_yaml(input):
    if not isinstance(input, list):
        raise InvalidYAMLFileException("cleaningMapping must contain a list")
    for entry in input:
        if not isinstance(entry, dict):
            raise InvalidYAMLFileException("each entry in cleaningMapping must be a dictionary")
        if set(entry.keys())!=set(["region", "functions"]):
            raise InvalidYAMLFileException("each entry must contain 2 keys, 'region' and 'functions'")
        if not isinstance(entry["functions"], list):
            raise InvalidYAMLFileException("functions entry must contain a list")




if False:
    df=pd.DataFrame([])
    with pd.ExcelWriter(filepath, engine='openpyxl', mode='a') as writer:
                workBook = writer.book
                try:
                    workBook.remove(workBook[first_sheet_name])
                except:
                    print("Worksheet does not exist")
                finally:
                    df.to_excel(writer, sheet_name=first_sheet_name, index=False, header=None)
                    writer.save()

