from t2wml.mapping.datamart_edges import clean_id
import yaml
import os
import warnings
from pathlib import Path
from shutil import copyfile
from t2wml.spreadsheets.sheet import SpreadsheetFile
from t2wml.utils.t2wml_exceptions import FileWithThatNameInProject, FileNotPresentInProject, InvalidProjectDirectory
from t2wml.settings import DEFAULT_SPARQL_ENDPOINT



class Project:
    def __init__(self, directory, title=None, description="", url="",
                    data_files=None, yaml_files=None, wikifier_files=None, entity_files=None,
                    yaml_sheet_associations=None, annotations=None,
                    sparql_endpoint=DEFAULT_SPARQL_ENDPOINT, warn_for_empty_cells=False, handle_calendar="leave",
                    cache_id=None, 
                    _saved_state=None, #deprecated but i don't want a trillion warnings
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

        self._load_data_files_from_project(data_files)
        self._load_yaml_sheet_associations(yaml_sheet_associations)
        self.annotations=annotations or {}

        self.yaml_files=yaml_files or []
        self.wikifier_files=wikifier_files or []
        self.entity_files=entity_files or []

        self.sparql_endpoint=sparql_endpoint
        self.warn_for_empty_cells=warn_for_empty_cells
        self.handle_calendar=handle_calendar

        self.cache_id=cache_id

    @property
    def dataset_id(self):
        return clean_id(self.title)
    
    def _load_data_files_from_project(self, data_files):
        self.data_files=data_files or {}

        if isinstance(data_files, list): #backwards compatibility version 0.0.13 and earlier
            warnings.warn("Using a project file from version 0.0.13 or earlier, updating to match more recent formats. Support for version 0.0.13 and earlier files may be deprecated in the future", DeprecationWarning)
            for file_path in data_files:
                full_file_path=os.path.join(self.directory, file_path)
                sf = SpreadsheetFile(full_file_path)
                self.data_files[file_path]=dict(val_arr= sf.sheet_names,
                                                selected=sf.sheet_names[0])
        else: 
            if data_files:
                #backwards compatibility 0.0.16 and earlier
                if isinstance(list(data_files.values())[0], list):
                    #warnings.warn("Using a project file from version 0.0.16 or earlier, updating to match more recent formats", DeprecationWarning)
                    for data_file_name, sheet_names in data_files.items():
                        self.data_files[data_file_name]=dict(val_arr= sheet_names,
                                                    selected= sheet_names[0])
 
    def _load_yaml_sheet_associations(self, yaml_sheet_associations):
        self.yaml_sheet_associations=yaml_sheet_associations or {}
        #backwards compatibility 0.0.16 and earlier
        if yaml_sheet_associations:
            #there must be some less horrifyingly ugly way of writing the next line, but it's one line...
            is_version_16_or_lower = isinstance(list(list(yaml_sheet_associations.values())[0].values())[0], list)
            if is_version_16_or_lower:
                new_style_yaml_associations={}
                #warnings.warn("Using a project file from version 0.0.16 or earlier, updating to match more recent formats", DeprecationWarning)
                for file_key in yaml_sheet_associations:
                    new_style_yaml_associations[file_key]={}
                    for sheet_key in yaml_sheet_associations[file_key]:
                        val_arr=yaml_sheet_associations[file_key][sheet_key]
                        new_style_yaml_associations[file_key][sheet_key]=dict(
                            val_arr=val_arr,
                            selected=val_arr[-1]
                        )
                self.yaml_sheet_associations=new_style_yaml_associations
    
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
                    print("renamed to: ", file_name)
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
            print("This file is already present in the project's data files")
        else:
            full_file_path=Path(self.directory) /  file_path
            sf = SpreadsheetFile(full_file_path)
            self.data_files[file_path]=dict(val_arr=sf.sheet_names, selected=sf.sheet_names[0])
        return file_path
    
    def add_yaml_file(self, file_path, data_file=None, sheet_name=None, 
                        copy_from_elsewhere=False, overwrite=False, rename=False):
        file_path=self._add_file(file_path, copy_from_elsewhere, overwrite, rename)
        if file_path in self.yaml_files:
            print("This file is already present in the project's yaml files")
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
                    print("that yaml association has already been added")
                else:
                    self.yaml_sheet_associations[data_path][sheet_name]["val_arr"].append(yaml_path)
            except KeyError:
                self.yaml_sheet_associations[data_path][sheet_name]=dict(val_arr=[yaml_path], selected=yaml_path)
        else:
            self.yaml_sheet_associations[data_path]={sheet_name:dict(val_arr=[yaml_path], selected=yaml_path)}
    
    def add_wikifier_file(self, file_path, copy_from_elsewhere=False, overwrite=False, rename=False):
        file_path=self._add_file(file_path, copy_from_elsewhere, overwrite, rename)
        if file_path in self.wikifier_files:
            print("This file is already present in the project's wikifier files")
            self.wikifier_files.remove(file_path)
            self.wikifier_files.append(file_path)
        else:
            self.wikifier_files.append(file_path)
        return file_path
    
    def add_specific_wikifier_file(self, wiki_path, data_path, sheet_name="NO_SHEET", 
                                   copy_from_elsewhere=False, overwrite=False, rename=False):
        raise NotImplementedError("Specific wikifiers are not currently supported")

    def add_entity_file(self, file_path, copy_from_elsewhere=False, overwrite=False, rename=False):
        file_path=self._add_file(file_path, copy_from_elsewhere, overwrite, rename)
        if file_path in self.entity_files:
            print("This file is already present in the project's entity files")
        else:
            self.entity_files.append(file_path)
        return file_path
    
    def add_annotation_file(self, annotation_path, data_path, sheet_name, copy_from_elsewhere=False, overwrite=False, rename=False):
        annotation_path=self._add_file(annotation_path, copy_from_elsewhere, overwrite, rename)
        data_path=self._normalize_path(data_path)
        self.validate_data_file_and_sheet_name(data_path, sheet_name)
        if data_path in self.annotations:
            try:
                if annotation_path in self.annotations[data_path][sheet_name]["val_arr"]:
                    print("that yaml association has already been added")
                else:
                    self.annotations[data_path][sheet_name]["val_arr"].append(annotation_path)
            except KeyError:
                self.annotations[data_path][sheet_name]=dict(val_arr=[annotation_path], selected=annotation_path)
        else:
            self.annotations[data_path]={sheet_name:dict(val_arr=[annotation_path], selected=annotation_path)}
        return annotation_path

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
        if file_path in self.wikifier_files:
            return True
        if file_path in self.entity_files:
            return True
        for key, data_file in self.annotations.items():
            for s_key, sheet in data_file.items():
                if file_path in sheet["val_arr"]:
                    return True
        return False
    
    def delete_file_from_project(self, file_path, delete_from_fs=False):
        if not self.path_in_files(file_path):
            raise ValueError("The file you are trying to delete does not exist in project")
            
        del_val=self._normalize_path(file_path)
        

        if del_val in self.data_files: #handle data files completely separately from everything else
            for edit_dict in [self.annotations, self.data_files, self.yaml_sheet_associations]:
                for key in edit_dict:
                    if key==del_val:
                        edit_dict.pop(del_val)
        
        elif del_val in self.entity_files: 
            self.entity_files.remove(del_val)    
        elif del_val in self.wikifier_files: 
            self.wikifier_files.remove(del_val)  
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
                print(e)
                



        

    def rename_file_in_project(self, old_name, new_name, rename_in_fs=False):
        old_name=self._normalize_path(old_name)
        new_name=self._normalize_path(new_name)

        if not self.path_in_files(old_name):
            raise ValueError("The file you are trying to rename does not exist in project")
        new_file_path=self.get_full_path(new_name)
        if os.path.isfile(new_file_path):
            raise ValueError("The new name you have provided already exists in the project directory")
            
        if old_name in self.data_files: #handle data files completely separately from everything else
            is_csv=False
            old_csv_name=Path(old_name).stem
            new_csv_name=Path(new_name).stem
            if len(self.data_files[old_name]["val_arr"])==1 and self.data_files[old_name]["selected"]==old_csv_name: #it's a csv
                is_csv=True
            for edit_dict in [self.annotations, self.data_files, self.yaml_sheet_associations]:
                for key in edit_dict:
                    if key==old_name:
                        edit_dict[new_name]=edit_dict.pop(old_name)
                        if is_csv:
                            try:
                                edit_dict[new_name][new_csv_name]=edit_dict[new_name].pop(old_csv_name)
                            except KeyError: #.data_files
                                edit_dict[new_name]["selected"]=new_csv_name
                                edit_dict[new_name]["val_arr"]=[new_csv_name]
        
        else:
            self.entity_files=[new_name if x==old_name else x for x in self.entity_files]
            self.wikifier_files=[new_name if x==old_name else x for x in self.wikifier_files]
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
        

    


    def save(self):
        output_dict=dict(self.__dict__)
        output_dict.pop('directory')
        proj_file_text=(yaml.dump(output_dict))
        proj_file_path=os.path.join(self.directory, "project.t2wml")
        with open(proj_file_path, 'w', encoding="utf-8") as f:
            f.write(proj_file_text)
        return proj_file_path

    @classmethod
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



class ProjectWithSavedState(Project):
    def __init__(self, directory, _saved_state=None, **kwargs):
        super().__init__(directory, **kwargs)
        if _saved_state is None or _saved_state["current_data_file"] is None:
            self.get_default_saved_state()
        else:
            self._saved_state=_saved_state
            
    @property
    def current_data_file(self):
        return self._saved_state["current_data_file"]
    
    @current_data_file.setter
    def current_data_file(self, new_value):
        if new_value in self.data_files:
            self._saved_state["current_data_file"]=new_value
        else:
            raise FileNotPresentInProject("Can't set current data file to file not present in project")
    
    @property
    def current_sheet(self):
        return self.data_files[self.current_data_file]["selected"]
    
    @current_sheet.setter
    def current_sheet(self, new_value):
        if new_value in self.data_files[self.current_data_file]["val_arr"]:
            self.data_files[self.current_data_file]["selected"]=new_value
        else:
            raise FileNotPresentInProject("Can't set current sheet to sheet not present in current data file")

        try:
            self.current_yaml=self.yaml_sheet_associations[self.current_data_file][self.current_sheet][-1]
        except (KeyError, IndexError):
            self.current_yaml=None

    @property
    def current_yaml(self):
        try:
            current_yaml = self.yaml_sheet_associations[self.current_data_file][self.current_sheet].get("selected", None)
        except:
            return None
        if not current_yaml:
            try:
                current_yaml=self.yaml_sheet_associations[self.current_data_file][self.current_sheet][-1]
            except IndexError:
                current_yaml=None
        return current_yaml
    
    @current_yaml.setter
    def current_yaml(self, new_value):
        if new_value is None:
            return
        if new_value in self.yaml_sheet_associations[self.current_data_file][self.current_sheet]["val_arr"]:
            self.yaml_sheet_associations[self.current_data_file][self.current_sheet]["selected"]=new_value
        else:
            raise FileNotPresentInProject("Can't set current yaml to a yaml not associated with the current sheet")
    
    @property
    def current_annotation(self):
        try:
            current_annotation = self.annotations[self.current_data_file][self.current_sheet].get("selected", None)
        except:
            return None
        if not current_annotation:
            try:
                current_annotation=self.yaml_sheet_associations[self.current_data_file][self.current_sheet][-1]
            except IndexError:
                current_annotation=None
        return current_annotation
    
    @current_annotation.setter
    def current_annotation(self, new_value):
        if new_value is None:
            return
        if new_value in self.annotations[self.current_data_file][self.current_sheet]["val_arr"]:
            self.annotations[self.current_data_file][self.current_sheet]["selected"]=new_value
        else:
            raise FileNotPresentInProject("Can't set current yaml to a yaml not associated with the current sheet")
    

    @property
    def current_wikifiers(self):
        return self._saved_state["current_wikifiers"]
    
    @current_wikifiers.setter
    def current_wikifiers(self, new_value):
        for value in new_value:
            if value not in self.wikifier_files:
                raise FileNotPresentInProject("Current wikifiers must only contain wikifiers added to the project")
        self._saved_state["current_wikifiers"]=new_value
    
    def get_default_saved_state(self):
        self._saved_state={}
        if self.data_files:
            self.current_data_file=list(self.data_files.keys())[-1] #default to most recently added file 
        else:
            self._saved_state=dict(current_data_file=None, current_yaml=None)
        if self.wikifier_files:
            self.current_wikifiers=[self.wikifier_files[-1]] #for now, default to last
        else:
            self._saved_state["current_wikifiers"]=None
    
    def update_saved_state(self, current_data_file=None, current_sheet=None, current_yaml=None, current_wikifiers=None, current_annotation=None):
        if current_data_file:
            self.current_data_file=self._normalize_path(current_data_file)

        if current_sheet:
            self.current_sheet=current_sheet
                
        if current_yaml:
            self.current_yaml=self._normalize_path(current_yaml)
        
        if current_annotation:
            self.current_annotation=self._normalize_path(current_annotation)
        
        if current_wikifiers:
            self.current_wikifiers=[self._normalize_path(wf) for wf in current_wikifiers]
        
        self.update_current_saved_state()
    
    def update_current_saved_state(self):
        self._saved_state=dict(
            current_data_file=self.current_data_file,
            current_sheet=self.current_sheet,
            current_yaml=self.current_yaml,
            current_annotation=self.current_annotation,
            current_wikifiers=self.current_wikifiers
        )


