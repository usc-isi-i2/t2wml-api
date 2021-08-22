import os
import json
from uuid import uuid4
import pandas as pd
from t2wml.utils.bindings import update_bindings
from t2wml.wikification.utility_functions import get_provider, dict_to_kgtk, kgtk_to_dict, add_entities_from_file
from t2wml.utils.t2wml_exceptions import InvalidAnnotationException, ItemNotFoundException
import numpy as np
from munkres import Munkres
from t2wml.spreadsheets.conversions import cell_tuple_to_str, column_index_to_letter
from t2wml.mapping.datamart_edges import clean_id
from t2wml.utils.debug_logging import basic_debug
import math

try:
    from math import dist
except:
    def dist(point1, point2):
        (x1,y1) = point1
        (x2,y2) = point2
        distance = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        return distance

COST_MATRIX_DEFAULT = 10


def get_Qnode(project, item):
    return f"QCustomNode-{clean_id(item)}"
    #return f"Q{project.dataset_id}-{clean_id(item)}"
    
def get_Pnode(project, property):
    return f"PCustomNode-{clean_id(property)}"
    #return f"P{project.dataset_id}-{clean_id(property)}"


def rect_distance(rect1, rect2):
    ((x1, y1), (x1b, y1b)) = rect1
    ((x2, y2), (x2b, y2b)) = rect2
    left = x2b < x1
    right = x1b < x2
    bottom = y2b < y1
    top = y1b < y2
    if top and left:
        return dist((x1, y1b), (x2b, y2))
    elif left and bottom:
        return dist((x1, y1), (x2b, y2b))
    elif bottom and right:
        return dist((x1b, y1), (x2, y2b))
    elif right and top:
        return dist((x1b, y1b), (x2, y2))
    elif left:
        return x1 - x2b
    elif right:
        return x2 - x1b
    elif bottom:
        return y1 - y2b
    elif top:
        return y2 - y1b
    else:             # rectangles intersect
        return 0

def check_overlap(ann1, ann2):
    #NOTE selections must be normalized before sending to this function

    #get rectangles from annotations
    selection = ann1["selection"]
    rect1 = (selection["x1"]-1, selection["y1"]-1), (selection["x2"]-1, selection["y2"]-1)
    selection = ann2["selection"]
    rect2 = (selection["x1"]-1, selection["y1"]-1), (selection["x2"]-1, selection["y2"]-1)

    if rect_distance(rect1, rect2)==0:
        raise InvalidAnnotationException("Overlapping selections")

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
        {mainSubjectLine}
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
        self.matches = {} #a dictionary of "unit", "property", etc which links to other blocks
    
    def get_from_annotation(self, key, *args, **kwargs):
        val = self.annotation.get(key, None)
        try:
            return val["id"] #if its a node
        except:
            return val


    def create_link(self, linked_block):
        linked_block.matches[self.role] = self
        self.annotation["link"] = linked_block.id

    @property
    def cell_args(self):
        selection=self.selection
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
        if self.role=="dependentVar":
            return cell1 + ":" + cell2
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
        return self.range_str + "::" +  str(self.role)

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
            return rect_distance(self.cell_args, relative_args.cell_args)
        if self.get_alignment_orientation(relative_args)=="row":
            return rect_distance(self.cell_args, relative_args.cell_args)
        misaligned_penalty = 5
        val = misaligned_penalty * rect_distance(self.cell_args, relative_args.cell_args)
        return val
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

    def get_expression(self, relative_value_args, use_q=False, sheet=None):
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
        
        dollar_n=""
        if sheet:
            if not self.is_2D:
                (x1, y1), (x2, y2) = self.cell_args
                cells = sheet[y1:y2+1, x1:x2+1]
                cells = cells.flatten().tolist()
                sample_length = min(10, len(cells))
                empty=0
                for i in range(sample_length):
                    if not cells[i] and cells[i]!=0:
                        empty+=1
                if empty >= sample_length * 0.49:
                    dollar_n="-$n"




        row_var = f", $qrow{dollar_n}" if use_q else f", $row{dollar_n}"
        col_var = f"$qcol{dollar_n}," if use_q else f"$col{dollar_n}, "

        if self.get_alignment_orientation(relative_value_args) == "row":
            col = column_index_to_letter(self.cell_args[0][0])
            return return_string.format(indexer=col+row_var)

        elif self.get_alignment_orientation(relative_value_args) == "col":
            row = str(self.cell_args[0][1]+1)
            return return_string.format(indexer=col_var+row)
        elif not self.is_2D:
            if self.row_args[0]==self.row_args[1]: #align by column
                row = str(self.cell_args[0][1]+1)
                return return_string.format(indexer=col_var+row)
            if self.col_args[0]==self.col_args[1]: #align by row
                col = column_index_to_letter(self.cell_args[0][0])
                return return_string.format(indexer=col+row_var)
        else:
            return "#TODO: ????? -Don't know how to match with imperfect alignment yet"





class Annotation():
    @basic_debug
    def __init__(self, annotation_blocks_array=None):
        self.annotations_array = self._preprocess_annotation(annotation_blocks_array or [])        
        self.data_annotations = []
        self.subject_annotations = []
        self.qualifier_annotations = []
        self.property_annotations = []
        self.unit_annotations = []
        self.comment_messages = ""
        self.has_been_initialized=False
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
        for block in self.annotations_array: #add links
            block.annotation["links"]={key:block.matches[key].id for key in block.matches}
        return [block.annotation for block in self.annotations_array]
    
    def _preprocess_annotation(self, annotations):
        if not isinstance(annotations, list):
            raise InvalidAnnotationException("Annotations must be a list")

        ids=set()

        
        #basic validity checks and prep setting up IDs
        for block in annotations:
            if not isinstance(block, dict):
                raise InvalidAnnotationException("Each annotation entry must be a dict")
            
            try:
                id=block["id"]
            except KeyError:
                id=block["id"]=str(uuid4())
            ids.add(id)
            
            block.pop("selectedArea", None) #if we somehow got this, remove it

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
                    #print("Deprecation warning: Switch from selections to selection")
                else:
                    raise InvalidAnnotationException("Each annotation entry must contain a field 'selection'")
            normalize_rectangle(block)

        #check for overlaps
        for i, block in enumerate(annotations):
            for j in range(i+1, len(annotations)):
                check_overlap(annotations[i], annotations[j])


        #set up userlinks
        for block in annotations:
            block["link"]="" #reset all auto-generated links each time
            userlink=block.get("userlink")
            if userlink:
                if userlink not in ids: #remove links to deleted blocks
                    block.pop("userlink")
                else:
                    block["link"]=userlink


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
            const_role=target.get_from_annotation(role)
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
        if not self.has_been_initialized:
            self._run_cost_matrix(
                self.property_annotations, [self.data_annotations, self.qualifier_annotations])
            self._run_cost_matrix(self.unit_annotations, [self.data_annotations, self.qualifier_annotations])
            data_annotations=self.data_annotations[0] if self.data_annotations else []
            subject_annotations=self.subject_annotations[0] if self.subject_annotations else []
            if subject_annotations and not data_annotations.get_from_annotation("subject"):
                subject_annotations.create_link(data_annotations)
            self.has_been_initialized=True
            self.data_annotations=data_annotations
            self.subject_annotations=subject_annotations
            return data_annotations, subject_annotations, self.qualifier_annotations
        return self.data_annotations, self.subject_annotations, self.qualifier_annotations

    def get_optionals_and_property(self, region, use_q, sheet=None):
        const_property=region.get_from_annotation("property")
        if const_property:
            propertyLine=str(const_property)
        else:
            property = region.matches.get("property", None)
            if property is None:
                propertyLine = "#TODO-- no property alignment found"
            else:
                propertyLine = property.get_expression(region, use_q, sheet=sheet)

        optionalsLines = ""
        unit = region.matches.get("unit", None)
        if unit is not None:
            optionalsLines += YamlFormatter.get_optionals_string(
                "unit: " + unit.get_expression(region, use_q, sheet=sheet)+"\n", use_q)
        for key in region.annotation:
            if key in ["changed", "id", "title", "links", "link"]: 
                continue
            if key not in ["role", "selection", "type", "property"]:
                try:
                    optionalsLines += YamlFormatter.get_optionals_string(
                        key+": "+region.annotation[key]+"\n", use_q)
                except Exception as e:
                    optionalsLines +=YamlFormatter.get_optionals_string(
                        "# error parsing annotation for key: "+key+" : "+str(e), use_q)


        return propertyLine, optionalsLines

    def _get_qualifier_yaml(self, qualifier_region, data_region, sheet=None):
        propertyLine, optionalsLines = self.get_optionals_and_property(
            qualifier_region, use_q=True)
        region = None

        if qualifier_region.type=='time':
            if qualifier_region.is_2D:
                num_cols=abs(qualifier_region.col_args[1]-qualifier_region.col_args[0])+1
                if num_cols == 2 or num_cols == 3:
                    first_col = column_index_to_letter(qualifier_region.col_args[0])
                    middle_col = f"value[{column_index_to_letter(qualifier_region.col_args[0]+1)}, $row]," if num_cols==3 else ""
                    last_col = column_index_to_letter(qualifier_region.col_args[1])
                    valueLine = f"=concat(value[{first_col}, $row], {middle_col} value[{last_col}, $row], '/')"

                    qualifier_string = YamlFormatter.get_qualifier_string(propertyLine, optionalsLines, valueLine, region)
                    return qualifier_string



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
            valueLine = qualifier_region.get_expression(data_region, sheet=sheet)

        qualifier_string = YamlFormatter.get_qualifier_string(
            propertyLine, optionalsLines, valueLine, region)

        return qualifier_string

    @basic_debug
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
        if data_region.get_from_annotation("subject"):
            mainSubjectLine="" #no need to do anything, will be added when adding fields
        elif subject_region:
            mainSubjectLine = "subject: "+subject_region.get_expression(data_region, sheet=sheet)
        else: 
            mainSubjectLine = "subject: #subject region not specified"

        propertyLine, optionalsLines = self.get_optionals_and_property(
            data_region, use_q=False, sheet=sheet)

        if len(qualifier_regions):
            qualifierLines = "qualifier:"
            for qualifier in qualifier_regions:
                qualifierLines += self._get_qualifier_yaml(
                    qualifier, data_region, sheet=sheet)
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
        #const_property=region.annotation.get_from_annotation("property")
        #if const_property:
        #    return [ (const_property, region.type)]
        #else:
            range_property = region.matches.get("property")
            if range_property:
                range_properties=set()
                for row in range(range_property.row_args[0], range_property.row_args[1]+1):
                    for col in range(range_property.col_args[0], range_property.col_args[1]+1):
                        range_properties.add((row, col))
                return list(range_properties), region.type
            return [], None

    def get_custom_properties_and_qnodes(self):
        custom_properties=list()
        custom_items=set()

        data_region, subject_region, qualifier_regions=self.annotation.initialize()

        #check all properties
        custom_properties.append(self._get_properties(data_region))
        for qualifier_region in qualifier_regions:
            custom_properties.append(self._get_properties(qualifier_region))
        
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
        
        return custom_properties, list(custom_items)
        
    @basic_debug
    def preload(self, sheet, wikifier):
        properties, items = self.get_custom_properties_and_qnodes()
        create_nodes(items, self.project, sheet, wikifier)
        for property_indices, data_type in properties:
            if property_indices:
                create_nodes(property_indices, self.project, sheet, wikifier, True, data_type)
    

def create_nodes(indices, project, sheet, wikifier, is_property=False, data_type=None):    
    item_table=wikifier.item_table
    update_bindings(item_table=item_table, sheet=sheet)
    
    columns=['row', 'column', 'value', 'context', 'item', 'file', 'sheet']
    created=set()

    #part one: wikification
    for (row, col) in indices:
        label=sheet[row, col]
        if label:
            try:
                exists = wikifier.item_table.get_item(col, row, sheet=sheet, value=label)                
                if not exists and label not in created:
                    raise KeyError
                if is_property:
                    if exists[0]!="P":
                        raise KeyError
                    int(exists[1:]) #will raise error for custom properties, which may need data_type updated
                if not is_property and exists[0]!="Q":
                    raise KeyError
            except:
                created.add((col, row, label))
    
    dataframe_rows=[]
    label_ids=dict()
    for (col, row, label) in created:
        try:
            id = label_ids[label]
        except KeyError:
            if is_property:
                id = get_Pnode(project, label)
            else:
                id = get_Qnode(project, label)
            label_ids[label]=id
        dataframe_rows.append([row, col, label, '', id, sheet.data_file_name, sheet.name])


    if dataframe_rows:
        df=pd.DataFrame(dataframe_rows, columns=columns)
        project.add_df_to_wikifier_file(sheet, df)
        wikifier.add_dataframe(df)
        wikifier.save_to_file()
        
    
    #part two: entity creation
    filepath=os.path.join(project.autogen_dir, "autogen_entities_"+sheet.data_file_name+".tsv")
    if os.path.isfile(filepath):
        custom_nodes=kgtk_to_dict(filepath)
    else:
        custom_nodes=dict()

    
    prov=get_provider()
    with prov as p:
        for col, row, label in created:
            node_id=label_ids[label]
            if not is_property:
                if node_id not in custom_nodes: #only set to auto if creating fresh
                    custom_nodes[node_id]={"label":label.strip()}
            else:
                for col, row, label in created:
                    if node_id in custom_nodes: #just update data type
                        custom_nodes[node_id]["data_type"]=data_type
                    else:
                        custom_nodes[node_id]=dict(data_type=data_type, 
                                    label=label, 
                                    description="")
    prov.update_cache(custom_nodes)
    
    if custom_nodes:
        dict_to_kgtk(custom_nodes, filepath)
        project.add_entity_file(filepath, precedence=False)    
    
    project.save()
    

def create_nodes_from_selection(selection, project, sheet, wikifier, is_property=False, data_type=None):
    #convenience function to create from selection
    indices=[]
    (col1, row1), (col2, row2) = selection
    for col in range(col1, col2+1):
        for row in range(row1, row2+1):
            indices.append((row, col))
    create_nodes(indices, project, sheet, wikifier, is_property=is_property, data_type=data_type)


