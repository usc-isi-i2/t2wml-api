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
    def __init__(self, directory, title="Untitled", data_files=None, yaml_files=None, wikifier_files=None, 
                       entity_files=None,
                   yaml_sheet_associations=None, specific_wikifiers=None,
                   sparql_endpoint=DEFAULT_SPARQL_ENDPOINT, warn_for_empty_cells=False):
        if not os.path.isdir(directory):
            raise ValueError("Project must be created with a valid project directory")
        self.directory=directory
        self.title=title
        self.data_files=data_files or []
        self.yaml_files=yaml_files or []
        self.wikifier_files=wikifier_files or []
        self.entity_files=entity_files or []
        self.yaml_sheet_associations=yaml_sheet_associations or {}
        self.specific_wikifiers=specific_wikifiers or {}
        self.sparql_endpoint=sparql_endpoint
        self.warn_for_empty_cells=warn_for_empty_cells
    
    def _add_file(self, file_path, copy_from_elsewhere=False, overwrite=False, rename=False):
        if os.path.isabs(file_path): #absolute paths behave differently when joining
            root=Path(self.directory)
            full_path=Path(file_path)
            in_proj_dir=root in full_path.parents
            if in_proj_dir:
                file_path=file_path.replace(self.directory, "")
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
            self.data_files.append(file_path)
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
        file_path=wiki_path
        file_path=self._add_file(file_path, copy_from_elsewhere, overwrite, rename)
        if data_path in self.specific_wikifiers:
            try:
                self.specific_wikifiers[data_path][sheet_name].append(file_path)
            except KeyError:
                self.specific_wikifiers[data_path][sheet_name]=[file_path]
        else:
            self.specific_wikifiers[data_path]={sheet_name:[file_path]}  
        return file_path
    
    def add_entity_file(self, file_path, copy_from_elsewhere=False, overwrite=False, rename=False):
        file_path=self._add_file(file_path, copy_from_elsewhere, overwrite, rename)
        if file_path in self.entity_files:
            print("This file is already present in the project's entity files")
        else:
            self.entity_files.append(file_path)
        return file_path
    
    def save(self):
        proj_file_text=(yaml.dump(self.__dict__))
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
    def _handle_specific_wikifiers(self, wikifier, data_file, sheet_name):
        if data_file in self.project.specific_wikifiers:
            wikifiers1=self.project.specific_wikifiers[data_file].get("NO_SHEET", [])
            wikifiers2=self.project.specific_wikifiers[data_file].get(sheet_name, [])
            for w in wikifiers1:
                self._add_file_to_wikifier(wikifier, w)
            for w in wikifiers2:
                self._add_file_to_wikifier(wikifier, w)
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
        self._handle_specific_wikifiers(wikifier, data_file, sheet_name)
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
                self._handle_specific_wikifiers(wikifier, data_file, sheet_name)
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

