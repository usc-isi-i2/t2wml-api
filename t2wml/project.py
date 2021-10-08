import json
from typing import DefaultDict
from t2wml.wikification.item_table import Wikifier, convert_old_df_to_dict, convert_old_wikifier_to_new
from t2wml.outputs.datamart_edges import clean_id
import yaml
import os
import warnings
from pathlib import Path
from shutil import copyfile
import pandas as pd
from t2wml.spreadsheets.sheet import SpreadsheetFile
from t2wml.utils.t2wml_exceptions import FileWithThatNameInProject, FileNotPresentInProject, InvalidProjectDirectory
from t2wml.settings import DEFAULT_SPARQL_ENDPOINT
from t2wml.utils.debug_logging import basic_debug



class Project:
    #@basic_debug
    def __init__(self, directory, title=None, description="", url="",
                    data_files=None, yaml_files=None, entity_files=None, wikifier_files=None,
                    yaml_sheet_associations=None, annotations=None,
                    sparql_endpoint=DEFAULT_SPARQL_ENDPOINT, warn_for_empty_cells=False, handle_calendar="leave",
                    cache_id=None,
                    **kwargs    
                ):
        if kwargs:
            warnings.warn("Passed unsupported arguments to Project, may be deprecated:"+str(kwargs.keys()), DeprecationWarning)
        if not os.path.isdir(directory):
            raise InvalidProjectDirectory("Project must be created with a valid project directory")
        self.directory=directory
        if title is None:
            title=Path(directory).stem
        self.title=title
        self.description=description
        self.url=url

        self.data_files=data_files or {}
        self.yaml_sheet_associations=yaml_sheet_associations or {}
        self.annotations=annotations or {}

        self.yaml_files=yaml_files or []
        self.entity_files=entity_files or []

        self.sparql_endpoint=sparql_endpoint
        self.warn_for_empty_cells=warn_for_empty_cells
        self.handle_calendar=handle_calendar

        self.cache_id=cache_id

        if not self.entity_file.exists():
            with open(self.entity_file, 'w') as f:
                f.write("{}")

        if not os.path.isdir(os.path.join(self.directory, "wikifiers")):
            os.mkdir(os.path.join(self.directory, "wikifiers"))
        
        #backwards compatibility 1 (<0.5.0)
        if wikifier_files:
            warnings.warn("wikifier files are being removed from project", DeprecationWarning)
            for wf in wikifier_files:
                #print(f"switching {wf} to compatible version")
                wf_path = self.get_full_path(wf)
                self.add_old_style_wikifier_to_project(wf_path)
            self.save()
        
        #backwards comptibility 2 (<0.6.3)
        wikifier_dir=os.path.join(self.directory, "wikifiers")
        if os.path.exists(wikifier_dir):
            expected_filenames_with_ext = set([clean_id(filename)+".json" for filename in self.data_files])
            expected_filenames_without_ext = {clean_id(filename):filename for filename in self.data_files}
            problem_filenames=[]
            for filename in os.listdir(wikifier_dir):
                if filename not in expected_filenames_with_ext:
                    problem_filenames.append(filename)
            
            corrected_filenames=DefaultDict(list)

            for problem in problem_filenames:
                for key in expected_filenames_without_ext:
                    if key in problem:
                        proper_name = expected_filenames_without_ext[key]
                        corrected_filenames[proper_name].append(problem)
            
            for actual_file_path in corrected_filenames:
                problem_arr=corrected_filenames[actual_file_path]
                wikifier_file_path, exists=self.get_wikifier_file(actual_file_path)
                wikifier = Wikifier(filepath=wikifier_file_path)
                for problem_file in problem_arr:
                    if Path(problem_file).suffix==".json":
                        with open(os.path.join(wikifier_dir, problem_file), 'r') as f:
                            wiki_dict=json.load(f)
                        wikifier.update_from_dict(wiki_dict)
                    elif Path(problem_file).suffix==".csv":
                        df = pd.read_csv(os.path.join(wikifier_dir, problem_file))
                        wiki_dict = convert_old_df_to_dict(df)
                        wikifier.update_from_dict(wiki_dict)

                    wikifier.save_to_file(wikifier_file_path)
            
            for problem_file in problem_filenames:
                try:
                    os.remove(os.path.join(wikifier_dir, problem_file))
                except Exception as e:
                    print(e)







    
    @property
    def autogen_dir(self):
        auto= os.path.join(self.directory, "annotations", f"autogen-files")
        if not os.path.exists(auto):
            os.makedirs(auto, exist_ok=True)
        return auto
    
    @property
    def entity_file(self):
        return Path(self.directory) / "project_entity_file.json"

    @property
    def dataset_id(self):
        return clean_id(self.title)

    #@basic_debug
    def _add_file(self, file_path, copy_from_elsewhere=False, overwrite=False, rename=False):
        if os.path.isabs(file_path):
            root=Path(self.directory)
            full_path=Path(file_path)
            in_proj_dir=root in full_path.parents
            if in_proj_dir:
                file_path=full_path.relative_to(root)
        else:
            full_path=os.path.join(self.directory, file_path)
            in_proj_dir=os.path.isfile(full_path)
        if not in_proj_dir:
            if not os.path.isfile(file_path):
                raise FileNotPresentInProject("Could not find file:"+file_path)
            if not copy_from_elsewhere:
                raise InvalidProjectDirectory("project files must be located in the project directory. did you mean to copy from elsewhere?")
            file_name=Path(file_path).name
            dst=os.path.join(self.directory, file_name)
            if os.path.isfile(dst):
                if overwrite:
                    pass
                elif rename:
                    index=0
                    while os.path.isfile(dst):
                        index+=1
                        file_name=Path(file_path).stem+"_"+str(index)+Path(file_path).suffix
                        dst=os.path.join(self.directory, file_name)
                    #print("renamed to: ", file_name)
                else:
                    raise FileWithThatNameInProject(str(dst))
            try:
                copyfile(file_path, dst)
                file_path=file_name
            except Exception as e:
                raise ValueError("Failed to copy provided file to project directory: "+str(e))
            
        return Path(file_path).as_posix() #save forward slash strings, windows anyway knows how to handle them 
    
    def add_data_file(self, file_path, copy_from_elsewhere=False, overwrite=False, rename=False):
        file_path=self._add_file(file_path, copy_from_elsewhere, overwrite, rename)
        if file_path in self.data_files:
            pass #print("This file is already present in the project's data files")
        else:
            full_file_path=Path(self.directory) /  file_path
            sf = SpreadsheetFile(full_file_path)
            self.data_files[file_path]=dict(val_arr=sf.sheet_names, selected=sf.sheet_names[0])
        return file_path
    
    def add_yaml_file(self, file_path, data_file=None, sheet_name=None, 
                        copy_from_elsewhere=False, overwrite=False, rename=False):
        file_path=self._add_file(file_path, copy_from_elsewhere, overwrite, rename)
        if file_path in self.yaml_files:
            pass #print("This file is already present in the project's yaml files")
        else:
            self.yaml_files.append(file_path)
        if data_file and sheet_name:
            self.associate_yaml_with_sheet(file_path, data_file, sheet_name)
        return file_path
    
    def validate_data_file_and_sheet_name(self, data_path, sheet_name):
        if data_path not in self.data_files:
            raise FileNotPresentInProject("That data file has not been added to project yet")
        if sheet_name not in self.data_files[data_path]['val_arr']:
            raise FileNotPresentInProject("That sheet name does not exist in the data file selected")

    def associate_yaml_with_sheet(self, yaml_path, data_path, sheet_name):
        data_path=self._normalize_path(data_path)
        yaml_path=self._normalize_path(yaml_path)

        self.validate_data_file_and_sheet_name(data_path, sheet_name)

        if yaml_path not in self.yaml_files:
            raise FileNotPresentInProject("That yaml file has not been added to project yet")
        if data_path in self.yaml_sheet_associations:
            try:
                if yaml_path in self.yaml_sheet_associations[data_path][sheet_name]["val_arr"]:
                    pass #print("that yaml association has already been added")
                else:
                    self.yaml_sheet_associations[data_path][sheet_name]["val_arr"].append(yaml_path)
            except KeyError:
                self.yaml_sheet_associations[data_path][sheet_name]=dict(val_arr=[yaml_path], selected=yaml_path)
        else:
            self.yaml_sheet_associations[data_path]={sheet_name:dict(val_arr=[yaml_path], selected=yaml_path)}
    
    def add_entity_file(self, file_path, copy_from_elsewhere=False, overwrite=False, rename=False, precedence=True):
        file_path=self._add_file(file_path, copy_from_elsewhere, overwrite, rename)
        if file_path in self.entity_files:
            pass #print("This file is already present in the project's entity files")
            self.entity_files.remove(file_path)
        if precedence:
            self.entity_files.append(file_path)
        else:
            self.entity_files= [file_path]+self.entity_files
        return file_path
    def add_annotation_file(self, annotation_path, data_path, sheet_name, copy_from_elsewhere=False, overwrite=False, rename=False):
        annotation_path=self._add_file(annotation_path, copy_from_elsewhere, overwrite, rename)
        data_path=self._normalize_path(data_path)
        self.validate_data_file_and_sheet_name(data_path, sheet_name)
        if data_path in self.annotations:
            try:
                if annotation_path in self.annotations[data_path][sheet_name]["val_arr"]:
                    pass #print("that yaml association has already been added")
                else:
                    self.annotations[data_path][sheet_name]["val_arr"].append(annotation_path)
            except KeyError:
                self.annotations[data_path][sheet_name]=dict(val_arr=[annotation_path], selected=annotation_path)
        else:
            self.annotations[data_path]={sheet_name:dict(val_arr=[annotation_path], selected=annotation_path)}
        return annotation_path

    #@basic_debug
    def _normalize_path(self, file_path):
        root=Path(self.directory)
        full_path=Path(file_path)
        in_proj_dir=root in full_path.parents
        if in_proj_dir:
            file_path=full_path.relative_to(root)
        return Path(file_path).as_posix()
    
    def get_full_path(self, file_path):
        normalized_path=self._normalize_path(file_path)
        return os.path.join(self.directory, normalized_path)
    
    def path_in_files(self, file_path):
        file_path = self._normalize_path(file_path)
        if file_path in self.data_files:
            return True
        if file_path in self.yaml_files:
            return True
        if file_path in self.entity_files:
            return True
        for key, data_file in self.annotations.items():
            for s_key, sheet in data_file.items():
                if file_path in sheet["val_arr"]:
                    return True
        return False
    
    def get_wikifier_file(self, file_path):
        data_file_path=self._normalize_path(file_path)
        wikifier_name=clean_id(data_file_path) + ".json"
        wikifier_file_path=os.path.join(self.directory, "wikifiers", wikifier_name)
        if os.path.exists(wikifier_file_path):
            return wikifier_file_path, True
        return wikifier_file_path, False
    
    def add_dict_to_wikifier_file(self, sheet, wiki_dict, overwrite_existing=True):
        wikifier_file_path, exists=self.get_wikifier_file(sheet.data_file_path)
        if exists:
            wikifier = Wikifier.load_from_file(wikifier_file_path)
        else:
            wikifier = Wikifier(filepath=wikifier_file_path)
        wikifier.update_from_dict(wiki_dict, overwrite_existing)
        wikifier.save_to_file(wikifier_file_path)
    
    def add_df_to_wikifier_file(self, sheet, df, overwrite_existing=True):
        wiki_dict = convert_old_df_to_dict(df)
        self.add_dict_to_wikifier_file(sheet, wiki_dict, overwrite_existing)

    #@basic_debug
    def delete_file_from_project(self, file_path, delete_from_fs=False):
        if not self.path_in_files(file_path):
            raise ValueError("The file you are trying to delete does not exist in project")
            
        del_val=self._normalize_path(file_path)
        wikifier_file_path, wikifier_file_exists = "", False
        
        if del_val in self.data_files: #handle data files completely separately from everything else
            self.data_files.pop(del_val)
            self.annotations.pop(del_val, None)
            self.yaml_sheet_associations.pop(del_val, None)
            wikifier_file_path, wikifier_file_exists = self.get_wikifier_file(del_val)
        elif del_val in self.entity_files: 
            self.entity_files.remove(del_val)    
        else: #annotations and yamls
            if del_val in self.yaml_files: 
                self.yaml_files.remove(del_val)  

            for edit_dict in [self.annotations, self.yaml_sheet_associations]:
                for data_file in edit_dict:
                    sheets_to_pop=[]
                    for sheet_name in edit_dict[data_file]:
                        arr_sel_dict=edit_dict[data_file][sheet_name]
                        if del_val in arr_sel_dict["val_arr"]:
                            if len(arr_sel_dict["val_arr"])==1:
                                sheets_to_pop.append(sheet_name)
                            else:
                                arr_sel_dict["val_arr"].remove(del_val)
                                if arr_sel_dict["selected"]==del_val:
                                    if len(arr_sel_dict["val_arr"]):
                                        arr_sel_dict["selected"]=arr_sel_dict["val_arr"][0]
                    for sheet in sheets_to_pop:
                        edit_dict[data_file].pop(sheet)
                                

        if delete_from_fs:
            try:
                del_path=self.get_full_path(del_val)
                os.remove(del_path)
            except Exception as e:
                pass #print(e)
            if wikifier_file_exists:
                try:
                    os.remove(wikifier_file_path)
                except Exception as e:
                    pass #print(e)

                
    #@basic_debug
    def rename_file_in_project(self, old_name, new_name, rename_in_fs=False):
        old_name=self._normalize_path(old_name)
        new_name=self._normalize_path(new_name)

        if not self.path_in_files(old_name):
            raise ValueError("The file you are trying to rename does not exist in project")
        new_file_path=self.get_full_path(new_name)
        if os.path.isfile(new_file_path):
            raise ValueError("The new name you have provided already exists in the project directory")

        old_wikifier_file_path, wikifier_file_exists = "", False

        if old_name in self.data_files: #handle data files completely separately from everything else
            old_csv_name=Path(old_name).stem
            new_csv_name=Path(new_name).stem
            uses_csv_sheet_name=False
            if len(self.data_files[old_name]["val_arr"])==1 and self.data_files[old_name]["selected"]==old_csv_name: #it's a csv
                uses_csv_sheet_name=True
            for edit_dict in [self.annotations, self.data_files, self.yaml_sheet_associations]:
                for key in edit_dict:
                    if key==old_name:
                        edit_dict[new_name]=edit_dict.pop(old_name)
                        if uses_csv_sheet_name:
                            try:
                                edit_dict[new_name][new_csv_name]=edit_dict[new_name].pop(old_csv_name)
                            except KeyError: #.data_files
                                edit_dict[new_name]["selected"]=new_csv_name
                                edit_dict[new_name]["val_arr"]=[new_csv_name]
            old_wikifier_file_path, wikifier_file_exists = self.get_wikifier_file(old_name)
        
        else:
            self.entity_files=[new_name if x==old_name else x for x in self.entity_files]
            self.yaml_files=[new_name if x==old_name else x for x in self.yaml_files]

            for edit_dict in [self.annotations, self.yaml_sheet_associations]:
                for data_file in edit_dict:
                    for sheet_name in edit_dict[data_file]:
                        arr_sel_dict=edit_dict[data_file][sheet_name]
                        if old_name in arr_sel_dict["val_arr"]:
                            if arr_sel_dict["selected"]==old_name:
                                arr_sel_dict["selected"]=new_name
                            arr_sel_dict["val_arr"]= [new_name if x==old_name else x for x in arr_sel_dict["val_arr"]]

        
        if rename_in_fs:
            new_path=Path(new_file_path)
            full_folder_path=new_path.parent
            os.makedirs(full_folder_path, exist_ok=True)
            old_file_path=self.get_full_path(old_name)
            os.rename(old_file_path, new_file_path)
            if wikifier_file_exists:
                new_wikifier_file_path, exists = self.get_wikifier_file(new_file_path)
                os.rename(old_wikifier_file_path, new_wikifier_file_path)

        
    #@basic_debug
    def save(self):
        output_dict=dict(self.__dict__)
        output_dict.pop('directory')
        proj_file_text=(yaml.dump(output_dict))
        proj_file_path=os.path.join(self.directory, "project.t2wml")
        with open(proj_file_path, 'w', encoding="utf-8") as f:
            f.write(proj_file_text)
        return proj_file_path

    @classmethod
    #@basic_debug
    def load(cls, filepath):
        if os.path.isdir(filepath):
            filepath=os.path.join(filepath, "project.t2wml")
        if not os.path.isfile(filepath):
            raise FileNotPresentInProject("Could not find project.t2wml file")
        try:
            with open(filepath, 'r', encoding="utf-8") as f:
                proj_input=yaml.safe_load(f.read())
        except Exception as e:
            raise ValueError("Failed to read the project yaml file: "+str(e))
        proj_input["directory"]=str(Path(filepath).parent)
        try:
            proj= cls(**proj_input)
        except Exception as e:
            raise ValueError("Was not able to initialize project from the yaml file: "+str(e))
        return proj


    def add_old_style_wikifier_to_project(self, wikifier_file):
        for datafile in self.data_files:
            sf = SpreadsheetFile(self.get_full_path(datafile))
            for sheet_name in sf:
                sheet=sf[sheet_name]
                wiki_dict = convert_old_wikifier_to_new(wikifier_file, sheet)
                self.add_dict_to_wikifier_file(sheet, wiki_dict, overwrite_existing=True)