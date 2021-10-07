
import json
from uuid import uuid4
from build.lib.t2wml.utils.date_utils import VALID_PROPERTY_TYPES
from t2wml.utils.t2wml_exceptions import InvalidAnnotationException
from t2wml.input_processing.utils import rect_distance, normalize_rectangle_selection
import numpy as np
from munkres import Munkres
from t2wml.spreadsheets.conversions import cell_tuple_to_str, column_index_to_letter
from t2wml.utils.debug_logging import basic_debug


COST_MATRIX_DEFAULT = 10

def check_overlap(ann_block1, ann_block2):
    """convenience function for validating that two annotation blocks do not overlap
    NOTE: selections must be normalized before sending to this function

    Args:
        ann_block1 (Block): first block to compare
        ann_block2 (Block): second block to compare

    Raises:
        InvalidAnnotationException: overlapping selections
    """
    #get rectangles from annotations
    selection = ann_block1["selection"]
    rect1 = (selection["x1"]-1, selection["y1"]-1), (selection["x2"]-1, selection["y2"]-1)
    selection = ann_block2["selection"]
    rect2 = (selection["x1"]-1, selection["y1"]-1), (selection["x2"]-1, selection["y2"]-1)

    if rect_distance(rect1, rect2)==0:
        raise InvalidAnnotationException("Overlapping selections")



class YamlCreator:
    """
    A class to consolidate all the yaml formatting and indentation in one convenient location
    Because yamls are indent-sensitive, this should be touched only cautiously
    """
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
    """A class to represent an annotation block

    Args:
        block_dictionary (dict): The dictionary representing the block from a json

    Attributes:
        block_dictionary (dict): The dictionary representing the block from a json
        role (str): role, from dictionary. valid values: "dependentVar", "mainSubject", "qualifier", "property", "unit", "metadata")
        selection (dict, {x1, x2, y1, y2}, 1-indexed): block coordinate dictionary. taken from dictionary and then "normalized" (relabeled as necessary so that x1, y1 coordinates are upper left and x2, y2 lower right)
        type (str or None): type, from dictionary. required if role is dependentVar or qualifier, not used otherwise. \ 
                            valid values: VALID_PROPERTY_TYPES
        id (str): the block id, from dictionary. a string from a generated uuid
        userlink (str): the block id for another block, from dictionary. if the user specified a userlink, it will not be overriden by automatic link generation.
        matches(dict): a dictionary in the form {role: block instance} linking roles (unit, property, etc), with other blocks
        cell_args (tuple, ((x1, y1) (x2, y2)), 0-indexed): 0 indexed tuple representation of selection
        range_str (str): str representation of selection, eg "A2:D4"
        use_item (bool): represents if block is =item[] or =value[] in yaml form, based on role/type
        col_args (tuple, (x1, x2), 0-indexed): just the column arguments
        row_args (tuple, (y1, y2), 0-indexed): just the row arguments
        is_2d (bool): does the block have multiple rows AND multiple columns
         

    """
    def __init__(self, block_dictionary):
        self.block_dictionary=block_dictionary
        
        try:
            role = block_dictionary["role"]
            if role not in ["dependentVar", "mainSubject", "qualifier", "property", "unit", "metadata"]:
                raise InvalidAnnotationException('Unrecognized value for role, must be from: "dependentVar", "mainSubject", "qualifier", "property", "unit", "metadata"')
            if role in ["dependentVar", "qualifier"]:
                try:
                    block_type=block_dictionary["type"]
                except KeyError:
                    raise InvalidAnnotationException("dependentVar and qualifier blocks must specify type")
                if block_type not in VALID_PROPERTY_TYPES:
                    raise InvalidAnnotationException('Unrecognized value for type, must be from: "globecoordinate", "quantity", "time", "string", "monolingualtext","externalid", "wikibaseitem", "wikibaseproperty", "url"')
        except KeyError:
            raise InvalidAnnotationException("Each annotation entry must contain a field 'role'")
            
        self.role = role
        self.selection = normalize_rectangle_selection(block_dictionary["selection"])
        self.type = block_dictionary.get("type", "")
        self.id=block_dictionary["id"]
        self.userlink=block_dictionary.get("userlink", None) #a user-input hard-coded link (takes priority over generated ones)
        self.matches = {} #a dictionary of "unit", "property", etc which links to other blocks
        self.cell_args=(self.selection["x1"]-1, self.selection["y1"]-1), (self.selection["x2"]-1, self.selection["y2"]-1)
    
    def get(self, key):
        """get key from block_dictionary
        """
        return self.block_dictionary.get(key, None)


    def create_link(self, linked_block):
        """creates a link between 2 blocks, using the current block's role
        example: self is block of role "unit", and is linked to be another block's unit.
        updates linked_blocks matches field and self's link field

        Args:
            linked_block (Block): a dependent variable or qualifier block
        """
        linked_block.matches[self.role] = self
        self.block_dictionary["link"] = linked_block.id

    @property
    def use_item(self):
        if self.role in ["wikibaseitem", "property", "mainSubject"]:
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

    def get_alignment_orientation(self, relative_block):
        """get whether two blocks align according to their rows or according to their columns

        Args:
            relative_args (Block): Block to orient against

        Returns:
            bool or string: "row", "col", or False (not aligned)
        """

        if self.row_args == relative_block.row_args:
            return "row"
        if self.col_args == relative_block.col_args:
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

    def get_match_score(self, relative_block):
        """matched score is a score for how well matched two blocks are.
        It is calculated using the distance between the two rectangles as well as a penalty if the blocks aren't aligned

        Args:
            relative_args (Block): second block to check against

        Returns:
            float: match score
        """
        if self.get_alignment_orientation(relative_block)=="col":
            return rect_distance(self.cell_args, relative_block.cell_args)
        if self.get_alignment_orientation(relative_block)=="row":
            return rect_distance(self.cell_args, relative_block.cell_args)
        misaligned_penalty = 5
        val = misaligned_penalty * rect_distance(self.cell_args, relative_block.cell_args)
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

    def get_expression(self, relative_block, use_q=False, sheet=None):
        """generates t2wml string expression for the block
        eg: "=value[3, $col-$n]"

        Args:
            relative_block (Block): the block we are aligning against
            use_q (bool, optional): use $row/$col, or $qrow/$qval? Defaults to False.
            sheet (Sheet, optional): used for calculating if -$n should be used. Defaults to None (-> no -$n)

        Returns:
            str: t2wml string expression
        """

        if self.use_item:
            return_string = "=item[{indexer}]"
        else:
            if self.type=="quantity": #also apply numeric cleaning
                return_string="=make_numeric(value[{indexer}])"
            else:
                return_string = "=value[{indexer}]"

        #if block is a single cell:
        if self.cell_args[0] == self.cell_args[1]: 
            cell_str = column_index_to_letter(
                self.cell_args[0][0]) + ", " + str(self.cell_args[0][1]+1)
            return return_string.format(indexer=cell_str)
        
        #check whether empty cells should be skipped vs returned as empty value
        #heuristic: if more than half a sample of thirty cells is empty, assume skipping (ie headings)
        dollar_n=""
        if sheet:
            if not self.is_2D:
                (x1, y1), (x2, y2) = self.cell_args
                cells = sheet[y1:y2+1, x1:x2+1]
                cells = cells.flatten().tolist()
                sample_length = min(30, len(cells))
                empty=0
                for i in range(sample_length):
                    if not cells[i] and cells[i]!=0:
                        empty+=1
                if empty >= sample_length * 0.49:
                    dollar_n="-$n"


        row_var = f", $qrow{dollar_n}" if use_q else f", $row{dollar_n}"
        col_var = f"$qcol{dollar_n}," if use_q else f"$col{dollar_n}, "

        if self.get_alignment_orientation(relative_block) == "row":
            col = column_index_to_letter(self.cell_args[0][0])
            return return_string.format(indexer=col+row_var)

        elif self.get_alignment_orientation(relative_block) == "col":
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
    #@basic_debug
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
            block.block_dictionary["links"]={key:block.matches[key].id for key in block.matches}
        return [block.block_dictionary for block in self.annotations_array]
    
    def _preprocess_annotation(self, annotations):
        if not isinstance(annotations, list):
            raise InvalidAnnotationException("Annotations must be a list")

        ids=set()

        
        #basic validity checks, backwards compatibility, and and prep setting up IDs
        for block in annotations:
            if not isinstance(block, dict):
                raise InvalidAnnotationException("Each annotation entry must be a dict")
            
            try:
                id=block["id"]
            except KeyError:
                id=block["id"]=str(uuid4())
            ids.add(id)


            #backwards compatility conversions:

            block.pop("selectedArea", None) #if we somehow got this, remove it
            
            if block.get("type", None) in ["WikibaseItem", "qNode"]:
                block["type"]="wikibaseitem"

            try:
                test=block["selection"]
            except KeyError:
                if "selections" in block:
                    block["selection"]=block["selections"][0]
                    block.pop("selections")
                    #print("Deprecation warning: Switch from selections to selection")
                else:
                    raise InvalidAnnotationException("Each annotation entry must contain a field 'selection'")



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

        #initialize Block instances
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
            const_role=target.get(role)
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
            if subject_annotations and not data_annotations.get("subject"):
                subject_annotations.create_link(data_annotations)
            self.has_been_initialized=True
            self.data_annotations=data_annotations
            self.subject_annotations=subject_annotations
            return data_annotations, subject_annotations, self.qualifier_annotations
        return self.data_annotations, self.subject_annotations, self.qualifier_annotations

    def get_optionals_and_property(self, region:Block, use_q, sheet=None):
        const_property=region.get("property")
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
            optionalsLines += YamlCreator.get_optionals_string(
                "unit: " + unit.get_expression(region, use_q, sheet=sheet)+"\n", use_q)
        for key in region.annotation:
            if key in ["changed", "id", "title", "links", "link"]: 
                continue
            if key not in ["role", "selection", "type", "property"]:
                try:
                    optionalsLines += YamlCreator.get_optionals_string(
                        key+": "+region.annotation[key]+"\n", use_q)
                except Exception as e:
                    optionalsLines +=YamlCreator.get_optionals_string(
                        "# error parsing annotation for key: "+key+" : "+str(e), use_q)


        return propertyLine, optionalsLines

    def _get_qualifier_yaml(self, qualifier_region: Block, data_region: Block, sheet=None):
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

                    qualifier_string = YamlCreator.get_qualifier_string(propertyLine, optionalsLines, valueLine, region)
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

                region = YamlCreator.get_qualifier_region_string(
                    left, right, top, bottom)
        else:
            valueLine = qualifier_region.get_expression(data_region, sheet=sheet)

        qualifier_string = YamlCreator.get_qualifier_string(
            propertyLine, optionalsLines, valueLine, region)

        return qualifier_string

    #@basic_debug
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
        if data_region.get("subject"):
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

        yaml = YamlCreator.get_yaml_string(
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

