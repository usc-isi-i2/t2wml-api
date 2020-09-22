import yaml
import os
from pathlib import Path
from shutil import copyfile
from t2wml.wikification.utility_functions import add_entities_from_file
from t2wml.wikification.item_table import Wikifier
from t2wml.spreadsheets.sheet import Sheet, SpreadsheetFile
from t2wml.mapping.statement_mapper import YamlMapper
from t2wml.knowledge_graph import KnowledgeGraph
from t2wml.utils.t2wml_exceptions import FileWithThatNameInProject
from t2wml.settings import DEFAULT_SPARQL_ENDPOINT


    

class Project:
    def __init__(self, directory, title=None, 
                    data_files=None, yaml_files=None, wikifier_files=None, entity_files=None,
                    yaml_sheet_associations=None, specific_wikifiers=None,
                    sparql_endpoint=DEFAULT_SPARQL_ENDPOINT, warn_for_empty_cells=False,
                    _saved_state=None    
                ):
        """
        Args:
            directory ([str, None]): Project directory. All project files must be contained in this directory or it's sub directories
            title ([str], optional): Project title. When None, defaults to name of folder at end of directory path
            data_files ([list], optional): Project's data files. When None, defaults to empty array. 
            yaml_files ([list], optional): Project's yaml files. When None, defaults to empty array. 
            wikifier_files ([list], optional): Project's wikifier files. When None, defaults to empty array. 
            entity_files ([list], optional): Project's entity files. When None, defaults to empty array. 
            yaml_sheet_associations ([dict], optional): [description]. When None, defaults to empty dictionary.
            sparql_endpoint ([str], optional): sparql endpoint for attempting to fetch entities not in entity files. Defaults to DEFAULT_SPARQL_ENDPOINT.
            warn_for_empty_cells (bool, optional): Project setting for whether empty cells in qualifier region are treated as an error. Defaults to False.

        Raises:
            ValueError: [description]
        """        
        if not os.path.isdir(directory):
            raise ValueError("Project must be created with a valid project directory")
        self.directory=directory
        if title is None:
            title=Path(directory).stem
        self.title=title
        if isinstance(data_files, list): #backwards compatibility
            self.data_files={}
            for file_path in data_files:
                full_file_path=os.path.join(self.directory, file_path)
                sf = SpreadsheetFile(full_file_path)
                self.data_files[file_path]=sf.sheet_names
        else:
            self.data_files=data_files or {}
        self.yaml_files=yaml_files or []
        self.wikifier_files=wikifier_files or []
        self.entity_files=entity_files or []
        self.yaml_sheet_associations=yaml_sheet_associations or {}
        if specific_wikifiers:
            raise NotImplementedError("Specific wikifiers are not currently supported")
        self.sparql_endpoint=sparql_endpoint
        self.warn_for_empty_cells=warn_for_empty_cells
        if _saved_state is None:
            self.get_default_saved_state()
        else:
            self._saved_state=_saved_state
    
    def get_default_saved_state(self):
        self._saved_state={}
        if self.data_files:
            self.current_data_file=list(self.data_files.keys())[-1] #default to most recently added file
            self.current_sheet=self.data_files[self.current_data_file][0] #default to first sheet
            try:
                self.current_yaml=self.yaml_sheet_associations[self.current_data_file][self.current_sheet][0]
            except KeyError:
                self._saved_state["current_yaml"]=None
        else:
            self._saved_state=dict(current_data_file=None, current_sheet=None, current_yaml=None)
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
            self.current_sheet=self.data_files[new_value][0] #default to first sheet
        else:
            raise ValueError("Can't set current data file to file not present in project")
    
    @property
    def current_sheet(self):
        return self._saved_state["current_sheet"]
    
    @current_sheet.setter
    def current_sheet(self, new_value):
        if new_value in self.data_files[self.current_data_file]:
            self._saved_state["current_sheet"]=new_value
        else:
            raise ValueError("Can't set current sheet to sheet not present in current data file")

        #reset yaml
        self.current_yaml=None

        try:
            self.current_yaml=self.yaml_sheet_associations[self.current_data_file][self.current_sheet][-1]
        except (KeyError, IndexError):
            pass
    @property
    def current_yaml(self):
        return self._saved_state["current_yaml"]
    
    @current_yaml.setter
    def current_yaml(self, new_value):
        if new_value is None:
            self._saved_state["current_yaml"]=None
            return
        if new_value in self.yaml_sheet_associations[self.current_data_file][self.current_sheet]:
            self._saved_state["current_yaml"]=new_value
        else:
            raise ValueError("Can't set current yaml to a yaml not associated with the current sheet")
    
    @property
    def current_wikifiers(self):
        return self._saved_state["current_wikifiers"]
    
    @current_wikifiers.setter
    def current_wikifiers(self, new_value):
        for value in new_value:
            if value not in self.wikifier_files:
                raise ValueError("Current wikifiers must only contain wikifiers added to the project")
        self._saved_state["current_wikifiers"]=new_value
    
    def normalize_path(self, file_path):
        root=Path(self.directory)
        full_path=Path(file_path)
        in_proj_dir=root in full_path.parents
        if in_proj_dir:
            file_path=full_path.relative_to(root)
        return file_path.as_posix()

    def update_saved_state(self, current_data_file=None, current_sheet=None, current_yaml=None, current_wikifiers=None):
        if current_data_file:
            self.current_data_file=self.normalize_path(current_data_file)

        if current_sheet:
            self.current_sheet=current_sheet
                
        if current_yaml:
            self.current_yaml=self.normalize_path(current_yaml)
        
        if current_wikifiers:
            self.current_wikifiers=[self.normalize_path(wf) for wf in current_wikifiers]

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
                raise ValueError("Could not find file:"+file_path)
            if not copy_from_elsewhere:
                raise ValueError("project files must be located in the project directory. did you mean to copy from elsewhere?")
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
            self.data_files[file_path]=sf.sheet_names
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
            raise ValueError("That data file has not been added to project yet")
        if yaml_path not in self.yaml_files:
            raise ValueError("That yaml file has not been added to project yet")
        if data_path in self.yaml_sheet_associations:
            try:
                if yaml_path in self.yaml_sheet_associations[data_path][sheet_name]:
                    print("that yaml association has already been added")
                else:
                    self.yaml_sheet_associations[data_path][sheet_name].append(yaml_path)
            except KeyError:
                self.yaml_sheet_associations[data_path][sheet_name]=[yaml_path]
        else:
            self.yaml_sheet_associations[data_path]={sheet_name:[yaml_path]}
    
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
            raise FileNotFoundError("Could not find project.t2wml file")
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


class ProjectRunner():
    def __init__(self, project):
        self.project=project
    
    @classmethod
    def load(cls, filepath):
        p=Project.load(filepath)
        return cls(p)

    def _add_entities_from_file(self, f):
        add_entities_from_file(os.path.join(self.project.directory, f))
    def _add_file_to_wikifier(self, wikifier, f):
        wikifier.add_file(os.path.join(self.project.directory, f))

    def _get_yaml_mapper(self, yf):
        return YamlMapper(os.path.join(self.project.directory, yf))

    def generate_old_style_single_file_knowledge_graph(self, sheet_name):
        return self.generate_single_knowledge_graph(self.project.data_files[-1], sheet_name, self.project.yaml_files[-1], self.project.wikifier_files[-1])
            
    def generate_single_knowledge_graph(self, data_file, sheet_name, yaml, wikifier_file=None):
        for f in self.project.entity_files:
            self._add_entities_from_file(f)
        wikifier=Wikifier()
        if wikifier_file:
            self._add_file_to_wikifier(wikifier, wikifier_file)
        else:
            for w in self.project.wikifier_files:
                self._add_file_to_wikifier(wikifier, w)
        data_file=os.path.join(self.project.directory, data_file)
        sheet=Sheet(data_file, sheet_name)
        yaml_mapper=self._get_yaml_mapper(yaml)
        kg=KnowledgeGraph.generate(yaml_mapper, sheet, wikifier)
        return kg
    
    def generate_all_knowledge_graphs(self):
        knowledge_graphs=[]
        for f in self.project.entity_files:
            self._add_entities_from_file(f)

        for data_file in self.project.data_files:
            data_file=os.path.join(self.project.directory, data_file)
            spreadsheet=SpreadsheetFile(data_file)
            for sheet_name in spreadsheet:
                wikifier=Wikifier()
                for w in self.project.wikifier_files:
                    self._add_file_to_wikifier(wikifier, w)
                sheet=spreadsheet[sheet_name]
                try:
                    yaml_files=self.project.yaml_sheet_associations[data_file][sheet_name]
                    for yf in yaml_files:
                        yaml_mapper=self._get_yaml_mapper(yf)
                        kg=KnowledgeGraph.generate(yaml_mapper, sheet, wikifier)
                        knowledge_graphs.append(kg)
                except:
                    continue
        return knowledge_graphs


