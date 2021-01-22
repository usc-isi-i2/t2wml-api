import json
from t2wml.utils.t2wml_exceptions import InvalidAnnotationException
import numpy as np
from munkres import Munkres
from t2wml.spreadsheets.conversions import cell_tuple_to_str, column_index_to_letter
from t2wml.utils.bindings import bindings
from t2wml.settings import t2wml_settings

COST_MATRIX_DEFAULT = 10


type_suggested_property_mapping={
    #"quantity": "P1114",
    "time": "P585",
    #"monolingualtext": "P2561",
}

class YamlFormatter:
    # all the formatting and indentation in one convenient location
    @staticmethod
    def get_yaml_string(region, mainSubjectLine, propertyLine, optionalsLines, qualifierLines):
        yaml = """#AUTO-GENERATED YAML\nstatementMapping:
    region:
        {region}
    template:
        subject: {mainSubjectLine}
        property: {propertyLine}
        value: =value[$col, $row]\n{optionalsLines}
        {qualifierLines}""".format(region=region, mainSubjectLine=mainSubjectLine, propertyLine=propertyLine, optionalsLines=optionalsLines, qualifierLines=qualifierLines)
        return yaml

    @staticmethod
    def get_qualifier_region_string(left, right, top, bottom):
        region = """left: {left}
                right: {right}
                top: {top}
                bottom: {bottom}""".format(left=left, right=right, top=top, bottom=bottom)
        return region

    @staticmethod
    def get_qualifier_string(propertyLine, optionalsLines, valueLine, region=None):
        if region is not None:
            qualifier_string = """
            - region: 
                {region}
              property: {propertyLine}
              value: {valueLine}\n{optionalsLines}""".format(region=region, propertyLine=propertyLine, valueLine=valueLine, optionalsLines=optionalsLines)
        else:
            qualifier_string = """
            - property: {propertyLine}
              value: {valueLine}\n{optionalsLines}""".format(propertyLine=propertyLine, valueLine=valueLine, optionalsLines=optionalsLines)
        return qualifier_string

    @staticmethod
    def get_optionals_string(optional_line, use_q):  
        indent = 14 if use_q else 8
        return """{indentation}{optional_line}""".format(indentation=" "*indent, optional_line=optional_line)


class ValueArgs:
    def __init__(self, annotation):
        self.annotation = annotation
        self.role = annotation["role"]
        self.type = annotation.get("type", "")
        self.selection = annotation["selections"][0]
        self.cell_args = self.get_cell_args(self.selection)
        self.matches = {}
        self.matched_to=None

    def get_cell_args(self, selection):
        return (selection["x1"]-1, selection["y1"]-1), (selection["x2"]-1, selection["y2"]-1)

    @property
    def use_item(self):
        if self.type == "wikibaseitem":
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
        return tuple(sorted([self.cell_args[0][0], self.cell_args[1][0]]))

    @property
    def row_args(self):
        return tuple(sorted([self.cell_args[0][1], self.cell_args[1][1]]))

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
        if self.get_alignment_orientation(relative_args):
            return 1
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
    def get_custom_properties_and_qnodes(self, sheet, item_table):
        custom_properties=set()
        custom_items=set()
        data_region, subject_region, qualifier_regions=self.initialize(sheet, item_table)

        #check all properties
        #check all main subject
        
        #check anything whose type is wikidataitem
        for block in self.annotation_blocks_array:
            type=block.type
            if type=="wikidataitem":
                pass

    def __init__(self, annotation_blocks_array=None):
        self.annotation_block_array = annotation_blocks_array or []
        self._validate_annotation(self.annotation_block_array)
        self.data_annotations = []
        self.subject_annotations = []
        self.qualifier_annotations = []
        self.property_annotations = []
        self.unit_annotations = []
        self.comment_messages = ""
        if annotation_blocks_array is not None:
            for block in annotation_blocks_array:
                role = block["role"]
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
    
    
    def _validate_annotation(self, annotations):
        if not isinstance(annotations, list):
            raise InvalidAnnotationException("Annotations must be a list")

        subject_count=0
        var_count=0
        
        for block in annotations:
            if not isinstance(block, dict):
                raise InvalidAnnotationException("Each annotation entry must be a dict")
            try:
                role = block["role"]

                if role == "dependentVar":
                    var_count+=1 
                elif role == "mainSubject":
                    subject_count+=1
                
            except KeyError:
                raise InvalidAnnotationException("Each annotation entry must contain a field 'role'")
            try:
                test=block["selections"][0]
            except KeyError:
                raise InvalidAnnotationException("Each annotation entry must contain a field 'selections'")
            except: 
                raise InvalidAnnotationException("Each annotation entry must contain a field 'selections' with at least one entry")

        if subject_count>1 or var_count>1: 
            raise InvalidAnnotationException("Each annotation can contain only one region for main subject and one region for dependent variable")

    @property
    def potentially_enough_annotation_information(self):
        if self.data_annotations and self.subject_annotations:
            return True
        return False

    def _create_targets(self, role, targets_collection):
        match_targets = []
        for arr in targets_collection:
            match_targets += arr

        for target in list(match_targets):
            # no assigning dynamic to what already has const
            if role in target.annotation:
                match_targets.remove(target)

            # no assigning unit to something not of type quantity
            elif role == "unit" and target.type != "quantity":
                match_targets.remove(target)

        return match_targets

    def _run_cost_matrix(self, match_candidates, targets_collection):
        if not len(match_candidates):
            return
        match_targets = self._create_targets(
            match_candidates[0].role, targets_collection)

        if len(match_targets) < len(match_candidates):
            self.comment_messages += "# Too many matching candidates for " + \
                match_candidates[0].role+"\n"

        if len(match_targets)<1:
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
            match_vector = match_candidates[c_i].role
            match_targets[t_i].matches[match_vector] = match_candidates[c_i]
            match_candidates[c_i].matched_to = match_targets[t_i]

    def get_optionals_and_property(self, region, use_q):
        const_property=region.annotation.get("property", None)
        if const_property:
            propertyLine=str(const_property)
        else:
            property = region.matches.get("property", None)
            if property is None:
                propertyLine = "#TODO-- no property alignment found"
                if not t2wml_settings.no_wikification:
                    suggested_property=type_suggested_property_mapping.get(region.type, "")
                    if suggested_property:
                        propertyLine = suggested_property + " #(auto-suggestion) " + propertyLine
                
            else:
                propertyLine = property.get_expression(region, use_q)

        optionalsLines = ""
        unit = region.matches.get("unit", None)
        if unit is not None:
            optionalsLines += YamlFormatter.get_optionals_string(
                "unit: " + unit.get_expression(region, use_q)+"\n", use_q)
        for key in region.annotation:
            if key not in ["role", "selections", "type", "property"]:
                optionalsLines += YamlFormatter.get_optionals_string(
                    key+": "+region.annotation[key]+"\n", use_q)

        return propertyLine, optionalsLines

    def _get_qualifier_yaml(self, qualifier_region, data_region):
        propertyLine, optionalsLines = self.get_optionals_and_property(
            qualifier_region, use_q=True)
        region = None

        if qualifier_region.is_2D:
            if qualifier_region.use_item:
                valueLine = "=item[$qcol, $qrow]"
            else:
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

        region = "range: {range_str}".format(range_str=data_region.range_str)
        if subject_region is not None:
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
            region, mainSubjectLine, propertyLine, optionalsLines, qualifierLines)
        yaml = self.comment_messages + yaml
        return [yaml] #array for now... 
    
    def initialize(self, sheet=None, item_table=None):
        data_regions = [ValueArgs(d) for d in self.data_annotations]
        if not self.subject_annotations:
            subject_regions=[None]
        else:
            subject_regions = [ValueArgs(s) for s in self.subject_annotations]
        qualifier_regions = [ValueArgs(q) for q in self.qualifier_annotations]

        property_regions = [ValueArgs(p) for p in self.property_annotations]
        unit_regions = [ValueArgs(m) for m in self.unit_annotations]
        self._run_cost_matrix(
            property_regions, [data_regions, qualifier_regions])
        self._run_cost_matrix(unit_regions, [data_regions, qualifier_regions])
        return data_regions[0], subject_regions[0], qualifier_regions
    
    def save(self, filepath):
        with open(filepath, 'w', encoding="utf-8") as f:
            f.write(json.dumps(self.annotation_block_array))

    @classmethod
    def load(cls, filepath):
        with open(filepath, 'r', encoding="utf-8") as f:
            annotations = json.load(f)
        instance = cls(annotations)
        return instance


