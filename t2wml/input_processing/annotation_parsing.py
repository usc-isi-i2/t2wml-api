from collections import defaultdict
import os
import json
from uuid import uuid4
from t2wml.utils.t2wml_exceptions import InvalidAnnotationException
import numpy as np
from munkres import Munkres
from t2wml.spreadsheets.conversions import cell_tuple_to_str, column_index_to_letter
from t2wml.settings import t2wml_settings
from t2wml.mapping.datamart_edges import clean_id
from t2wml.wikification.country_wikifier_cache import countries
from t2wml.utils.date_utils import parse_datetime
from t2wml.parsing.cleaning_functions import make_numeric

COST_MATRIX_DEFAULT = 10


type_suggested_property_mapping={
    #"quantity": "P1114",
    "time": "P585",
    #"monolingualtext": "P2561",
}


def normalize_rectangle(annotation):
    selection = annotation["selection"]
    top=min(selection["y1"], selection["y2"])
    bottom=max(selection["y1"], selection["y2"])
    left=min(selection["x1"], selection["x2"])
    right=max(selection["x1"], selection["x2"])
    annotation["selection"]={"x1": left, "x2": right, "y1":top, "y2":bottom}



class YamlFormatter:
    # all the formatting and indentation in one convenient location
    @staticmethod
    def get_yaml_string(region, mainSubjectLine, propertyLine, dataLine, optionalsLines, qualifierLines):
        yaml = f"""#AUTO-GENERATED YAML\nstatementMapping:
    region:
        {region}
    template:
        subject: {mainSubjectLine}
        property: {propertyLine}
        value: {dataLine}\n{optionalsLines}
        {qualifierLines}"""
        return yaml

    @staticmethod
    def get_qualifier_region_string(left, right, top, bottom):
        region = f"""left: {left}
                right: {right}
                top: {top}
                bottom: {bottom}"""
        return region

    @staticmethod
    def get_qualifier_string(propertyLine, optionalsLines, valueLine, region=None):
        if region is not None:
            qualifier_string = f"""
            - region: 
                {region}
              property: {propertyLine}
              value: {valueLine}\n{optionalsLines}"""
        else:
            qualifier_string = f"""
            - property: {propertyLine}
              value: {valueLine}\n{optionalsLines}"""
        return qualifier_string

    @staticmethod
    def get_optionals_string(optional_line, use_q):  
        indent = 14 if use_q else 8
        return """{indentation}{optional_line}""".format(indentation=" "*indent, optional_line=optional_line)


class Block:
    def __init__(self, annotation):
        self.annotation=annotation
        self.role = annotation["role"]
        self.selection = annotation["selection"]
        self.type = annotation.get("type", "")
        self.id=annotation["id"]
        self.userlink=annotation.get("userlink", None)
        self.cell_args = self.get_cell_args(self.selection)
        self.matches = {} #a dictionary of "unit", "property", etc which links to other blocks
    
    def create_link(self, linked_block):
        linked_block.matches[self.role] = self
        self.annotation["link"] = linked_block.id

    def get_cell_args(self, selection):
        return (selection["x1"]-1, selection["y1"]-1), (selection["x2"]-1, selection["y2"]-1)

    @property
    def use_item(self):
        if self.type in ["wikibaseitem", "WikibaseItem", "qNode"]:
            return True
        if self.role in ["property", "mainSubject"]:
            return True
        return False


    @property
    def range_str(self):
        cell1 = cell_tuple_to_str(*self.cell_args[0])
        cell2 = cell_tuple_to_str(*self.cell_args[1])
        if cell1 == cell2:
            return cell1
        else:
            return cell1 + ":" + cell2

    @property
    def col_args(self):
        return (self.cell_args[0][0], self.cell_args[1][0])

    @property
    def row_args(self):
        return (self.cell_args[0][1], self.cell_args[1][1])

    @property
    def is_2D(self):
        if self.cell_args[0][0] == self.cell_args[1][0]:
            return False
        if self.cell_args[0][1] == self.cell_args[1][1]:
            return False
        return True

    def __repr__(self):
        return self.range_str + "::" + str(self.property_alignment)

    def __str__(self):
        return self.__repr__()

    def get_alignment_orientation(self, relative_args, require_precise=False):
        if require_precise or True:
            if self.row_args == relative_args.row_args:
                return "row"
            if self.col_args == relative_args.col_args:
                return "col"
            return False

        # TODO: add heuristics for imperfect alignments
        row_val = abs(self.row_args[0]-relative_args.row_args[0]) + abs(self.row_args[1]-relative_args.row_args[1])
        col_val = abs(self.col_args[0]-relative_args.col_args[0]) + abs(self.col_args[1]-relative_args.col_args[1])
        
        if row_val<col_val:
            return "row"
        if col_val<row_val:
            return "col"
        return False #??? when would they be equal?


    def get_alignment_value(self, relative_args):
        if self.get_alignment_orientation(relative_args)=="col":
            return 1
        if self.get_alignment_orientation(relative_args)=="row":
            return 2
        return COST_MATRIX_DEFAULT
        # TODO: add costs for imperfect alignments
        if self.get_alignment_orientation(relative_args)=="row":
            diff1 = abs(self.col_args[0] - relative_args.col_args[0])
            diff2 = abs(self.col_args[1] - relative_args.col_args[1])

            return min(diff1, diff2)
        if self.get_alignment_orientation(relative_args)=="col":
            diff1 = abs(self.row_args[0] - relative_args.row_args[0])
            diff2 = abs(self.row_args[1] - relative_args.row_args[1])
            return min(diff1, diff2)
        return COST_MATRIX_DEFAULT

    def get_expression(self, relative_value_args, use_q=False):
        if self.use_item:
            return_string = "=item[{indexer}]"
        else:
            if self.type=="quantity":
                return_string="=make_numeric(value[{indexer}])"
            else:
                return_string = "=value[{indexer}]"

        if self.cell_args[0] == self.cell_args[1]:  # single cell
            cell_str = column_index_to_letter(
                self.cell_args[0][0]) + ", " + str(self.cell_args[0][1]+1)
            return return_string.format(indexer=cell_str)

        row_var = ", $qrow-$n" if use_q else ", $row-$n"
        col_var = "$qcol-$n, " if use_q else "$col-$n, "

        if self.get_alignment_orientation(relative_value_args) == "row":
            col = column_index_to_letter(self.cell_args[0][0])
            return return_string.format(indexer=col+row_var)

        elif self.get_alignment_orientation(relative_value_args) == "col":
            row = str(self.cell_args[0][1]+1)
            return return_string.format(indexer=col_var+row)
        else:
            print("Don't know how to match with imperfect alignment yet" +
                  self.range_str + ","+relative_value_args.range_str)
            return "#TODO: ????? -Don't know how to match with imperfect alignment yet"





class Annotation():
    def __init__(self, annotation_blocks_array=None):
        self.annotations_array = self._preprocess_annotation(annotation_blocks_array or [])        
        self.data_annotations = []
        self.subject_annotations = []
        self.qualifier_annotations = []
        self.property_annotations = []
        self.unit_annotations = []
        self.comment_messages = ""
        for block in self.annotations_array:
                role = block.role
                if role == "dependentVar":
                    self.data_annotations.append(block)
                elif role == "mainSubject":
                    self.subject_annotations.append(block)
                elif role == "qualifier":
                    self.qualifier_annotations.append(block)
                elif role == "property":
                    self.property_annotations.append(block)
                elif role == "unit":
                    self.unit_annotations.append(block)
                elif role == "metadata":
                    pass
                else:
                    raise ValueError("unrecognized role type for annotation")
    
    @property
    def annotation_block_array(self):
        return [block.annotation for block in self.annotations_array]
    
    def _preprocess_annotation(self, annotations):
        if not isinstance(annotations, list):
            raise InvalidAnnotationException("Annotations must be a list")

        ids=set()
        
        for block in annotations:
            if not isinstance(block, dict):
                raise InvalidAnnotationException("Each annotation entry must be a dict")
            
            try:
                id=block["id"]
            except KeyError:
                id=block["id"]=str(uuid4())
            ids.add(id)


        for block in annotations:
            userlink=block.get("userlink")
            if userlink:
                if userlink not in ids: #remove links to deleted blocks
                    block.pop("userlink")
                else:
                    block["link"]=userlink

            try:
                role = block["role"]
                if role not in ["dependentVar", "mainSubject", "qualifier", "property", "unit", "metadata"]:
                    raise InvalidAnnotationException('Unrecognized value for role, must be from: "dependentVar", "mainSubject", "qualifier", "property", "unit", "metadata"')
                if role in ["dependentVar", "qualifier"]:
                    try:
                        block_type=block["type"]
                    except KeyError:
                        raise InvalidAnnotationException("dependentVar and qualifier blocks must specify type")
                    
            except KeyError:
                raise InvalidAnnotationException("Each annotation entry must contain a field 'role'")
            
            try:
                test=block["selection"]
            except KeyError:
                if "selections" in block:
                    block["selection"]=block["selections"][0]
                    block.pop("selections")
                    print("Deprecation warning: Switch from selections to selection")
                else:
                    raise InvalidAnnotationException("Each annotation entry must contain a field 'selection'")
            normalize_rectangle(block)

        annotations_arr = [Block(block) for block in annotations]

        #initialize userlinks
        self.annotations_dict={block.id: block for block in annotations_arr}
        for block in annotations_arr:
            if block.userlink:
                block.create_link(self.annotations_dict[block.userlink])

        return annotations_arr

    @property
    def potentially_enough_annotation_information(self):
        if self.data_annotations and self.subject_annotations:
            return True
        return False

    def _create_targets(self, role, targets_collection):
        match_targets = []
        for arr in targets_collection: #combine the arrays
            match_targets += arr

        for target in list(match_targets):
            #if we already linked them via userlink, no overriding
            if role in target.matches:
                match_targets.remove(target)

            # no assigning dynamic to what already has const
            const_role=target.annotation.get(role, False)
            if const_role:
                match_targets.remove(target)

            # no assigning unit to something not of type quantity
            elif role == "unit" and target.type != "quantity":
                match_targets.remove(target)

        return match_targets
    
    def _winnow_match_candidates(self, match_candidates):
        new_match_candidates=[]
        for cand in match_candidates:
            if not cand.userlink:
                new_match_candidates.append(cand)
        return new_match_candidates

    def _run_cost_matrix(self, match_candidates, targets_collection):
        '''
        match_candidates: eg property, unit
        targets_collection: array of arrays of qualifiers, dependent variables
        '''

        match_candidates=self._winnow_match_candidates(match_candidates)
        if not len(match_candidates):
            return
        match_targets = self._create_targets(
            match_candidates[0].role, targets_collection)

        if len(match_targets) < len(match_candidates):
            self.comment_messages += "# Too many matching candidates for " + \
                match_candidates[0].role+"\n"

        if not len(match_targets):
            return

        cost_matrix = np.empty(
            (len(match_candidates),
             len(match_targets)),
            dtype=int)
        cost_matrix.fill(COST_MATRIX_DEFAULT)
        for c_i, candidate in enumerate(match_candidates):
            for r_i, target in enumerate(match_targets):
                cost_matrix[c_i][r_i] = candidate.get_alignment_value(target)

        m = Munkres()
        try:
            indexes = m.compute(cost_matrix)
        except Exception as e:  # more candidates than targets
            square_mat = np.empty(
                (len(match_candidates),
                 len(match_candidates)),
                dtype=int)
            square_mat.fill(100)
            square_mat[0:len(match_candidates), 0:len(
                match_targets)] = cost_matrix
            square_indexes = m.compute(square_mat)
            indexes = []
            for (c_i, t_i) in square_indexes:
                if t_i < len(match_targets):  # only include in range
                    indexes.append((c_i, t_i))

        for (c_i, t_i) in indexes:
            match_can = match_candidates[c_i]
            match_targ = match_targets[t_i]
            match_can.create_link(match_targ)

    
    def initialize(self, sheet=None, item_table=None):
        self._run_cost_matrix(
            self.property_annotations, [self.data_annotations, self.qualifier_annotations])
        self._run_cost_matrix(self.unit_annotations, [self.data_annotations, self.qualifier_annotations])
        data_annotations=self.data_annotations[0] if self.data_annotations else []
        subject_annotations=self.subject_annotations[0] if self.subject_annotations else []
        return data_annotations, subject_annotations, self.qualifier_annotations

    def get_optionals_and_property(self, region, use_q):
        const_property=region.annotation.get("property", None)
        if const_property:
            propertyLine=str(const_property)
        else:
            property = region.matches.get("property", None)
            if property is None:
                propertyLine = "#TODO-- no property alignment found"
            else:
                propertyLine = property.get_expression(region, use_q)

        optionalsLines = ""
        unit = region.matches.get("unit", None)
        if unit is not None:
            optionalsLines += YamlFormatter.get_optionals_string(
                "unit: " + unit.get_expression(region, use_q)+"\n", use_q)
        for key in region.annotation:
            if key in ["changed", "id", "title"]: 
                continue
            if key not in ["role", "selection", "type", "property"]:
                try:
                    optionalsLines += YamlFormatter.get_optionals_string(
                        key+": "+region.annotation[key]+"\n", use_q)
                except Exception as e:
                    optionalsLines +=YamlFormatter.get_optionals_string(
                        "# error parsing annotation for key: "+key+" : "+str(e), use_q)


        return propertyLine, optionalsLines

    def _get_qualifier_yaml(self, qualifier_region, data_region):
        propertyLine, optionalsLines = self.get_optionals_and_property(
            qualifier_region, use_q=True)
        region = None

        if qualifier_region.is_2D:
            if qualifier_region.use_item:
                valueLine = "=item[$qcol, $qrow]"
            else:
                if qualifier_region.type=="quantity":
                    valueLine="=make_numeric(value[$qcol, $qrow])"
                valueLine = "=value[$qcol, $qrow]"

            alignment = qualifier_region.get_alignment_orientation(data_region, require_precise=True)
            if alignment == False:
                region = "range: "+qualifier_region.range_str
            else:
                if alignment == "col":
                    left = right = "=$col"
                    top, bottom = qualifier_region.row_args
                    top += 1
                    bottom += 1

                else:  # alignment == "row":
                    top = bottom = "=$row"
                    left, right = qualifier_region.col_args
                    left, right = column_index_to_letter(
                        left), column_index_to_letter(right)

                region = YamlFormatter.get_qualifier_region_string(
                    left, right, top, bottom)
        else:
            valueLine = qualifier_region.get_expression(data_region)

        qualifier_string = YamlFormatter.get_qualifier_string(
            propertyLine, optionalsLines, valueLine, region)

        return qualifier_string

    def generate_yaml(self, sheet=None, item_table=None):
        if not self.data_annotations:
            return ["# cannot create yaml without a dependent variable\n"]
        data_region, subject_region, qualifier_regions=self.initialize(sheet, item_table)

        if data_region.use_item:
            dataLine= "=item[$col, $row]"
        else:
            if data_region.type=="quantity":
                dataLine= "=make_numeric(value[$col, $row])"
            else:
                dataLine= "=value[$col, $row]"

        region = "range: {range_str}".format(range_str=data_region.range_str)
        if subject_region:
            mainSubjectLine = subject_region.get_expression(data_region)
        else: 
            mainSubjectLine = "# subject region not specified"

        propertyLine, optionalsLines = self.get_optionals_and_property(
            data_region, use_q=False)

        if len(qualifier_regions):
            qualifierLines = "qualifier:"
            for qualifier in qualifier_regions:
                qualifierLines += self._get_qualifier_yaml(
                    qualifier, data_region)
        else:
            qualifierLines = ""

        yaml = YamlFormatter.get_yaml_string(
            region, mainSubjectLine, propertyLine, dataLine, optionalsLines, qualifierLines)
        yaml = self.comment_messages + yaml
        return [yaml] #array for now... 
    
    def save(self, filepath):
        with open(filepath, 'w', encoding="utf-8") as f:
            f.write(json.dumps(self.annotation_block_array))

    @classmethod
    def load(cls, filepath):
        with open(filepath, 'r', encoding="utf-8") as f:
            annotations = json.load(f)
        instance = cls(annotations)
        return instance

class AnnotationNodeGenerator:
    def __init__(self, annotation, project):
        self.annotation=annotation
        self.project=project
        if not os.path.isdir(self.autogen_dir):
            os.mkdir(self.autogen_dir)
    
    def _get_units(self, region):
        unit=region.matches.get("unit")
        if unit:
            units=set()
            for row in range(unit.row_args[0], unit.row_args[1]+1):
                    for col in range(unit.col_args[0], unit.col_args[1]+1):
                        units.add((row, col))
            return list(units)
        return []


    def _get_properties(self, region):
        #const_property=region.annotation.get("property")
        #if const_property:
        #    return [ (const_property, region.type)]
        #else:
            range_property = region.matches.get("property")
            if range_property:
                range_properties=set()
                for row in range(range_property.row_args[0], range_property.row_args[1]+1):
                    for col in range(range_property.col_args[0], range_property.col_args[1]+1):
                        range_properties.add((row, col, region.type))
                return list(range_properties)
            return []

    def get_custom_properties_and_qnodes(self):
        custom_properties=set()
        custom_items=set()

        data_region, subject_region, qualifier_regions=self.annotation.initialize()

        #check all properties
        custom_properties.update(self._get_properties(data_region))
        for qualifier_region in qualifier_regions:
            custom_properties.update(self._get_properties(qualifier_region))
        
        #check all units
        custom_items.update(self._get_units(data_region))
        for qualifier_region in qualifier_regions:
            custom_items.update(self._get_units(qualifier_region))

        #check all main subject
        for row in range(subject_region.row_args[0], subject_region.row_args[1]+1):
            for col in range(subject_region.col_args[0], subject_region.col_args[1]+1):
                custom_items.add((row, col))
        
        #check anything whose type is wikibaseitem
        for block in self.annotation.annotations_array:
            type=block.type
            if type in ["wikibaseitem", "WikibaseItem"]:
                for row in range(block.row_args[0], block.row_args[1]+1):
                    for col in range(block.col_args[0], block.col_args[1]+1):
                        custom_items.add((row, col))
        
        return list(custom_properties), list(custom_items)

    
    @property
    def autogen_dir(self):
        auto= os.path.join(self.project.directory, "annotations", f"autogen-files-{self.project.dataset_id}")
        if not os.path.exists(auto):
            os.makedirs(auto, exist_ok=True)
        return auto
    
    @property
    def project_id(self):
        return clean_id(self.project.title)
    
    def get_Qnode(self, item):
        return f"Q{self.project_id}-{clean_id(item)}"
    
    def get_Pnode(self, property):
        return f"P{self.project_id}-{clean_id(property)}"

    def preload(self, sheet, wikifier):
        import pandas as pd
        from t2wml.utils.bindings import update_bindings
        from t2wml.wikification.utility_functions import get_provider, dict_to_kgtk, kgtk_to_dict

        properties, items = self.get_custom_properties_and_qnodes()
    
       
        item_table=wikifier.item_table
        update_bindings(item_table=item_table, sheet=sheet)

        columns=['row', 'column', 'value', 'context', 'item', 'file', 'sheet']
        dataframe_rows=[]
        item_entities=set()

        #part one: wikification
        for (row, col) in items:
            item_string=sheet[row][col]
            if item_string:
                try:
                    exists = wikifier.item_table.get_item(col, row, sheet=sheet)                
                    if not exists:
                        raise ValueError
                except:
                    dataframe_rows.append([row, col, item_string, '', self.get_Qnode(item_string), sheet.data_file_name, sheet.name])
                    item_entities.add(item_string)
        
        for (row, col, data_type) in properties:
            property=sheet[row][col]
            if property:
                try:
                    exists = wikifier.item_table.get_item(col, row, sheet=sheet)
                    if not exists:
                        raise ValueError
                except:
                    pnode=self.get_Pnode(property)
                    dataframe_rows.append([row, col, property, '', pnode, sheet.data_file_name, sheet.name])


        if dataframe_rows:
            df=pd.DataFrame(dataframe_rows, columns=columns)
            filepath=os.path.join(self.autogen_dir, "wikifier_"+sheet.data_file_name+"_"+sheet.name+".csv")
            if os.path.isfile(filepath):
                #clear any clashes/duplicates
                org_df=pd.read_csv(filepath)
                if 'file' not in org_df:
                    org_df['file']=''
                if 'sheet' not in org_df:
                    org_df['sheet']=''

                df=pd.concat([org_df, df]).drop_duplicates(subset=['row', 'column', 'value', 'file', 'sheet'], keep='last').reset_index(drop=True)

            df.to_csv(filepath, index=False, escapechar="")
            wikifier.add_dataframe(df)
            self.project.add_wikifier_file(filepath, precedence=False)
                
        #part two: entity creation
        filepath=os.path.join(self.autogen_dir, "entities_"+sheet.data_file_name+"_"+sheet.name+".tsv")
        if os.path.isfile(filepath):
            custom_nodes=kgtk_to_dict(filepath)
        else:
            custom_nodes=defaultdict(dict)

        
        prov=get_provider()
        for item in item_entities:
            node_id=self.get_Qnode(item)
            if node_id not in custom_nodes: #only set to auto if creating fresh
                custom_nodes[node_id]["label"]=item
        for (row, col, data_type) in properties:
            property = sheet[row][col]
            if property:
                node_id = wikifier.item_table.get_item(col, row, sheet=sheet)
                if node_id==self.get_Pnode(property): #it's a custom property
                    if node_id in custom_nodes: #just update data type
                        custom_nodes[node_id]["data_type"]=data_type
                    else:
                        custom_nodes[node_id]=dict(data_type=data_type, 
                                    label=property, 
                                    description="")

                    prov.save_entry(node_id, from_file=True, **custom_nodes[node_id])
                
        dict_to_kgtk(custom_nodes, filepath)
        self.project.add_entity_file(filepath, precedence=False)    
        self.project.save()
    


def get_types(cell_content):
    cell_content=str(cell_content)
    is_country = cell_content in countries or cell_content.lower() in countries
    if make_numeric(cell_content) != "" and cell_content[0] not in ["P", "Q"]:
        is_numeric=True
    else:
        is_numeric=False
    
    try:
        parse_datetime(cell_content)
        is_date=True
    except:
        is_date=False
    return is_country, is_numeric, is_date


        

def annotation_suggester(sheet, selection, annotation_blocks_array):
    already_has_subject=False
    already_has_var=False
    for block in annotation_blocks_array:
        if block["role"]=="mainSubject":
            already_has_subject=True
        if block["role"]=="dependentVar":
            already_has_var=True

    (x1, y1), (x2, y2) = (selection["x1"]-1, selection["y1"]-1), (selection["x2"]-1, selection["y2"]-1)
    first_cell=sheet[y1, x1]
    is_country, is_numeric, is_date=get_types(first_cell)

    children={}

    if is_country:
        roles=[]
        if not already_has_subject:
            roles.append("mainSubject")
        roles.append("qualifier")
        if not already_has_var:
            roles.append("dependentVar")
        
        types=["string", "wikibaseitem"]
        if is_numeric:
            types.append("quantity")
    
    elif is_date:
        roles=["qualifier"]
        if not already_has_var:
            roles.append("dependentVar")
        types=["time"]
        if is_numeric:
            types.append("quantity")
        types.append("string")
        children["property"]="P585"
    
    elif is_numeric:
        roles=["qualifier"]
        if not already_has_var:
            roles.insert(0, "dependentVar")
        types=["quantity", "string"]

    else:
        if x1==x2 and y1==y2: #single cell selection, default to property
            roles= ["property", "qualifier", "dependentVar", "mainSubject", "unit"]
        else: #all else, default to qualifier
            roles= ["qualifier", "property", "dependentVar", "mainSubject", "unit"]
        if already_has_var:
            roles.remove("dependentVar")
        if already_has_subject:
            roles.remove("mainSubject")
        types= ["string", "wikibaseitem"]

    
    response= { 
        "roles": roles,
        "types": types,
        "children": children
    }

    return response



def basic_block_finder(sheet):
    data=np.ones((sheet.row_len, sheet.col_len))
    for row in range(sheet.row_len):
        for col in range(sheet.col_len):
            content = sheet[row][col]
            if content.strip()=="":
                data[row, col]=0
                continue
            is_country, is_numeric, is_date=get_types(content)
            if is_country:
                data[row, col]=5
                if is_numeric: #for now override "numeric" countries
                    data[row, col]=2
            elif is_date:
                data[row, col]=3
                if is_numeric:
                    data[row, col]=6
            elif is_numeric:
                data[row, col]=2
    annotations=[]
    c_selection=get_selection(data, *np.where(data%5 == 0))
    d_selection=get_selection(data, *np.where(data%3==0))
    selection=get_selection(data, *np.where(data%2==0), two_d=True, overlaps=[c_selection, d_selection])
    
    c_selection=normalize_to_selection(selection, c_selection)
    d_selection=normalize_to_selection(selection, d_selection)
        
    if c_selection:
        (x1, y1, x2, y2)=c_selection
        annotations.append({
                "selection":dict(x1=int(x1)+1, y1=int(y1)+1, x2= int(x2)+1, y2=int(y2)+1),
                "role":"mainSubject",
                "type": "wikibaseitem",
        })

    if d_selection:
        (x1, y1, x2, y2)=d_selection
        annotations.append({
                "selection":dict(x1=int(x1)+1, y1=int(y1)+1, x2= int(x2)+1, y2=int(y2)+1),
                "role":"qualifier",
                "type": "time",
                "property": "P585"
        })
    if selection:
        (x1, y1, x2, y2)=selection
        annotations.append({
                "selection":dict(x1=int(x1)+1, y1=int(y1)+1, x2= int(x2)+1, y2=int(y2)+1),
                "role":"dependentVar",
                "type": "quantity",
                "property":"P1114"
        })

    return annotations

def normalize_to_selection(selection, selection_to_norm):
    if not selection or not selection_to_norm:
        return selection_to_norm
    (n_x1, n_y1, n_x2, n_y2)=selection

    (x1, y1, x2, y2)=selection_to_norm
    if x1==x2 and y1!=y2: #row
        return (x1, n_y1, x2, n_y2)
    if y1==y2 and x1!=x2: #column
        return (n_x1, y1, n_x2, y2)
    return selection_to_norm


def check_overlap(row, col, overlaps):
    for selection in overlaps:
        if selection:
            (x1, y1, x2, y2)=selection
            if row>=y1 and row <= y2 and col>=x1 and col<=x2:
                return True
    return False

def get_selection(sheet_data, rows, columns, two_d=False, overlaps=None):
    overlaps=overlaps or []
    indices=[(row, col) for row, col in zip(rows, columns)]
    candidates={}

    for start_row, start_col in indices:
        if sheet_data[start_row][start_col]==0 or check_overlap(start_row, start_col, overlaps):
            continue
        
        #search for row
        col=start_col
        while (start_row, col) in indices and not check_overlap(start_row, col, overlaps):
            col+=1
        col-=1

        row=start_row
        if two_d:
            while(row, col) in indices and not check_overlap(row, col, overlaps):
                row+=1
            row-=1

        candidates[(start_row, row, start_col, col)]=0

        #search for column:
        row=start_row
        while (row, start_col) in indices and not check_overlap(row, start_col, overlaps):
            row+=1
        row-=1

        col=start_col
        if two_d:
            while(row, col) in indices and not check_overlap(row, col, overlaps):
                col+=1
            col-=1
        
        candidates[(start_row, row, start_col, col)]=0
    
    actual_candidates={}
    for candidate in candidates:
        try:
            #trim zeros:
            (y1, y2, x1, x2) = candidate
            data=sheet_data[y1:y2+1, x1:x2+1]
            zero_rows= np.where(~data.any(axis=1))[0]
            zero_columns=np.where(~data.any(axis=0))[0]
            num_rows, num_columns = data.shape
            num_rows-=1
            num_columns-=1
            while num_rows in zero_rows:
                num_rows-=1
            
            while num_columns in zero_columns:
                num_columns-=1
            #data=data[:num_rows, :num_columns]
            actual_candidates[(x1, y1, num_columns+x1, num_rows+y1)]=num_rows+1*num_columns+1
        except Exception as e:
            print(e)

    max_index = max(actual_candidates, key=lambda k: actual_candidates[k]) if actual_candidates else None
    return max_index



        
        

    
        
    
    


