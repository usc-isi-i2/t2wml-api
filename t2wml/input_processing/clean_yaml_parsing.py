import os
from pathlib import Path
from hashlib import sha256
import pandas as pd
import numpy as np
from t2wml.spreadsheets.utilities import load_pickle
from t2wml.input_processing.region import YamlRegion
from t2wml.settings import t2wml_settings
from t2wml.utils.t2wml_exceptions import ErrorInYAMLFileException
from t2wml.parsing.cleaning_functions import cleaning_functions_dict
from t2wml.spreadsheets.caching import pickle_folder
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


class DFCleaner:
    def __init__(self, cleaning_mappings, sheet):
        self.sheet=sheet
        validate_cleaning_yaml(cleaning_mappings)
        instructions = self.get_instruction_sets(cleaning_mappings, sheet)
        self.df=self.clean_sheet(instructions, sheet)

    
    def get_instruction_sets(self, cleaning_mappings, sheet):
        update_bindings(sheet=sheet)
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
        return parsing_instructions


    def clean_sheet(self, parsing_instructions, sheet):
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
                #output=df.apply(np.vectorize(my_func)) #a possibly faster way, but needs fiddling
        return df


def get_cleaned_dataframe(sheet, yaml_instructions):
    if t2wml_settings.cache_data_files:
        yaml_hash = sha256(str(yaml_instructions).encode('utf-8'))
        pickle_dir=pickle_folder(sheet.data_file_path) / yaml_hash.hexdigest()
        pickle_file=pickle_dir / (Path(sheet.data_file_path).stem+"_"+sheet.name+"_cleaned.pkl")
        #1: check for fresh pickled version of df
        if os.path.isfile(pickle_file):
            if os.path.getmtime(pickle_file) > os.path.getmtime(sheet.data_file_path):
                df=load_pickle(pickle_file)
                return df
        else:
            sc=DFCleaner(yaml_instructions, sheet)
            Path.mkdir(pickle_dir, parents=True, exist_ok=True)
            sc.df.to_pickle(pickle_file)
            return sc.df
            
    sc=DFCleaner(yaml_instructions, sheet)
    return sc.df


def validate_cleaning_yaml(input):
    if not isinstance(input, list):
        raise ErrorInYAMLFileException("cleaningMapping must contain a list")
    for entry in input:
        if not isinstance(entry, dict):
            raise ErrorInYAMLFileException("each entry in cleaningMapping must be a dictionary")
        if set(entry.keys())!=set(["region", "functions"]):
            raise ErrorInYAMLFileException("each entry must contain 2 keys, 'region' and 'functions'")
        if not isinstance(entry["functions"], list):
            raise ErrorInYAMLFileException("functions entry must contain a list")


