import yaml
import os
from pathlib import Path
from shutil import copyfile
from t2wml.wikification.utility_functions import add_properties_from_file
from t2wml.wikification.item_table import Wikifier
from t2wml.spreadsheets.sheet import Sheet, SpreadsheetFile
from t2wml.mapping.statement_mapper import YamlMapper
from t2wml.knowledge_graph import KnowledgeGraph


    

class Project:
    def __init__(self, directory, title="Untitled", data_files=None, yaml_files=None, wikifier_files=None, 
                       property_files=None, item_files=None,
                   yaml_sheet_associations=None, specific_wikifiers=None):
        if not os.path.isdir(directory):
            raise ValueError("Project must be created with a valid project directory")
        self.directory=directory
        self.title=title
        self.data_files=data_files or []
        self.yaml_files=yaml_files or []
        self.wikifier_files=wikifier_files or []
        self.property_files=property_files or []
        self.item_files=item_files or []
        self.yaml_sheet_associations=yaml_sheet_associations or {}
        self.specific_wikifiers=specific_wikifiers or {}
    
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
                    raise ValueError("A file with that name already exists in the project directory")
            try:
                copyfile(file_path, dst)
                file_path=file_name
            except Exception as e:
                raise ValueError("Failed to copy provided file to project directory: "+str(e))
            
        return Path(file_path).as_posix() #save forward slash strings, windows anyway knows how to handle them 
    
    def add_data_file(self, file_path, copy_from_elsewhere=False, overwrite=False, rename=False):
        file_path=self._add_file(file_path, copy_from_elsewhere, overwrite, rename)
        self.data_files.append(file_path)
        return file_path
    
    def add_yaml_file(self, file_path, data_file=None, sheet_name=None, 
                        copy_from_elsewhere=False, overwrite=False, rename=False):
        file_path=self._add_file(file_path, copy_from_elsewhere, overwrite, rename)
        self.yaml_files.append(file_path)
        if data_file and sheet_name:
            self.associate_yaml_with_sheet(file_path, data_file, sheet_name)
        return file_path

    def associate_yaml_with_sheet(self, yaml_path, data_path, sheet_name):
        if data_path not in self.data_files:
            raise ValueError("That data file has not been added to project yet")
        if yaml_path not in self.yaml_files:
            raise ValueError("That yaml file has not been added to project yet")
        if data_path in self.yaml_sheet_associations:
            try:
                self.yaml_sheet_associations[data_path][sheet_name].append(yaml_path)
            except KeyError:
                self.yaml_sheet_associations[data_path][sheet_name]=[yaml_path]
        else:
            self.yaml_sheet_associations[data_path]={sheet_name:[yaml_path]}
    
    def add_wikifier_file(self, file_path, copy_from_elsewhere=False, overwrite=False, rename=False):
        file_path=self._add_file(file_path, copy_from_elsewhere, overwrite, rename)
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
    
    def add_property_file(self, file_path, copy_from_elsewhere=False, overwrite=False, rename=False):
        file_path=self._add_file(file_path, copy_from_elsewhere, overwrite, rename)
        self.property_files.append(file_path)
        return file_path

    def add_item_file(self, file_path, copy_from_elsewhere=False, overwrite=False, rename=False):
        file_path=self._add_file(file_path, copy_from_elsewhere, overwrite, rename)
        self.item_files.append(file_path)
        return file_path
    
    def save(self):
        proj_file_text=(yaml.dump(self.__dict__))
        proj_file_path=os.path.join(self.directory, "t2wmlproj.yaml")
        with open(proj_file_path, 'w') as f:
            f.write(proj_file_text)
        return proj_file_path

    @classmethod
    def load(cls, filepath):
        if os.path.isdir(filepath):
            filepath=os.path.join(filepath, "t2wmlproj.yaml")
        if not os.path.isfile(filepath):
            raise FileNotFoundError("Could not find t2wmlproj.yaml file")
        try:
            with open(filepath, 'r') as f:
                input=yaml.safe_load(f.read())
        except Exception as e:
            raise ValueError("Failed to read the project yaml file: "+str(e))

        try:
            proj= cls(**input)
        except:
            raise ValueError("Was not able to initialize project from the yaml file")
        proj.directory=str(Path(filepath).parent)
        return proj


class ProjectRunner(Project):
    def add_properties_from_file(self, f):
        add_properties_from_file(os.path.join(self.directory, f))
    def add_file_to_wikifier(self, wikifier, f):
        wikifier.add_file(os.path.join(self.directory, f))
    def handle_specific_wikifiers(self, wikifier, data_file, sheet_name):
        if data_file in self.specific_wikifiers:
            wikifiers1=self.specific_wikifiers[data_file].get("NO_SHEET", [])
            wikifiers2=self.specific_wikifiers[data_file].get(sheet_name, [])
            for w in wikifiers1:
                self.add_file_to_wikifier(wikifier, w)
            for w in wikifiers2:
                self.add_file_to_wikifier(wikifier, w)
    def get_yaml_mapper(self, yf):
        return YamlMapper(os.path.join(self.directory, yf))

    def generate_old_style_single_file_knowledge_graph(self, sheet_name):
        return self.generate_single_knowledge_graph(self.data_files[-1], sheet_name, self.yaml_files[-1])
            
    def generate_single_knowledge_graph(self, data_file, sheet_name, yaml):
        for f in self.property_files:
            self.add_properties_from_file(f)
        wikifier=Wikifier()
        for w in self.wikifier_files:
            self.add_file_to_wikifier(wikifier, w)
        data_file=os.path.join(self.directory, data_file)
        self.handle_specific_wikifiers(wikifier, data_file, sheet_name)
        sheet=Sheet(data_file, sheet_name)
        yaml_mapper=self.get_yaml_mapper(yaml)
        kg=KnowledgeGraph.generate(yaml_mapper, sheet, wikifier)
        return kg
    
    def generate_all_knowledge_graphs(self):
        knowledge_graphs=[]
        for f in self.property_files:
            self.add_properties_from_file(f)

        for data_file in self.data_files:
            data_file=os.path.join(self.directory, data_file)
            spreadsheet=SpreadsheetFile(data_file)
            for sheet_name in spreadsheet:
                wikifier=Wikifier()
                for w in self.wikifier_files:
                    self.add_file_to_wikifier(wikifier, w)
                self.handle_specific_wikifiers(wikifier, data_file, sheet_name)
                sheet=spreadsheet[sheet_name]
                try:
                    yaml_files=self.yaml_sheet_associations[data_file][sheet_name]
                    for yf in yaml_files:
                        yaml_mapper=self.get_yaml_mapper(yf)
                        kg=KnowledgeGraph.generate(yaml_mapper, sheet, wikifier)
                        knowledge_graphs.append(kg)
                except:
                    continue
        return knowledge_graphs

