import yaml
import os
import warnings
from pathlib import Path
from shutil import copyfile
from t2wml.wikification.utility_functions import add_entities_from_file
from t2wml.wikification.item_table import Wikifier
from t2wml.spreadsheets.sheet import Sheet, SpreadsheetFile
from t2wml.mapping.statement_mapper import YamlMapper
from t2wml.knowledge_graph import KnowledgeGraph
from t2wml.utils.t2wml_exceptions import FileWithThatNameInProject, FileNotPresentInProject, InvalidProjectDirectory
from t2wml.settings import DEFAULT_SPARQL_ENDPOINT


    

class Project:
    def __init__(self, directory, title=None, 
                    data_files=None, yaml_files=None, wikifier_files=None, entity_files=None,
                    yaml_sheet_associations=None,
                    sparql_endpoint=DEFAULT_SPARQL_ENDPOINT, warn_for_empty_cells=False, handle_calendar="leave",
                    _saved_state=None, cache_id=None,
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
        self._load_data_files_from_project(data_files)
        self._load_val_arr_from_project(yaml_sheet_associations)

        self.yaml_files=yaml_files or []
        self.wikifier_files=wikifier_files or []
        self.entity_files=entity_files or []

        self.sparql_endpoint=sparql_endpoint
        self.warn_for_empty_cells=warn_for_empty_cells
        self.handle_calendar=handle_calendar

        self.cache_id=cache_id
        if _saved_state is None or _saved_state["current_data_file"] is None:
            self.get_default_saved_state()
        else:
            self._saved_state=_saved_state
    
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

                
    
    def _load_val_arr_from_project(self, yaml_sheet_associations):
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
    def current_wikifiers(self):
        return self._saved_state["current_wikifiers"]
    
    @current_wikifiers.setter
    def current_wikifiers(self, new_value):
        for value in new_value:
            if value not in self.wikifier_files:
                raise FileNotPresentInProject("Current wikifiers must only contain wikifiers added to the project")
        self._saved_state["current_wikifiers"]=new_value
    
    def normalize_path(self, file_path):
        root=Path(self.directory)
        full_path=Path(file_path)
        in_proj_dir=root in full_path.parents
        if in_proj_dir:
            file_path=full_path.relative_to(root)
        return Path(file_path).as_posix()

    def update_current_saved_state(self):
        self._saved_state=dict(
            current_data_file=self.current_data_file,
            current_sheet=self.current_sheet,
            current_yaml=self.current_yaml,
            current_wikifiers=self.current_wikifiers
        )

    def update_saved_state(self, current_data_file=None, current_sheet=None, current_yaml=None, current_wikifiers=None):
        if current_data_file:
            self.current_data_file=self.normalize_path(current_data_file)

        if current_sheet:
            self.current_sheet=current_sheet
                
        if current_yaml:
            self.current_yaml=self.normalize_path(current_yaml)
        
        if current_wikifiers:
            self.current_wikifiers=[self.normalize_path(wf) for wf in current_wikifiers]
        
        self.update_current_saved_state()

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

    def associate_yaml_with_sheet(self, yaml_path, data_path, sheet_name):
        data_path=Path(data_path).as_posix()
        yaml_path=Path(yaml_path).as_posix()
        if data_path not in self.data_files:
            raise FileNotPresentInProject("That data file has not been added to project yet")
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




