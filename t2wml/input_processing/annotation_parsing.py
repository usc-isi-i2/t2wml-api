import json
import numpy as np
from munkres import Munkres
from t2wml.spreadsheets.conversions import cell_tuple_to_str, column_index_to_letter
COST_MATRIX_DEFAULT = 10


class YamlFormatter:
    # all the formatting and indentation in one convenient location
    @staticmethod
    def get_yaml_string(region, mainSubjectLine, propertyLine, optionalsLines, qualifierLines):
        yaml = """#AUTO-GENERATED YAML
statementMapping:
    region:
        {region}
    template:
        subject: {mainSubjectLine}
        property: {propertyLine}
        value: =value[$col, $row]
{optionalsLines}
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
              value: {valueLine}
{optionalsLines}""".format(region=region, propertyLine=propertyLine, valueLine=valueLine, optionalsLines=optionalsLines)
        else:
            qualifier_string = """
        - property: {propertyLine}
          value: {valueLine}
{optionalsLines}""".format(propertyLine=propertyLine, valueLine=valueLine, optionalsLines=optionalsLines)
        return qualifier_string

    @staticmethod
    def get_optionals_string(optional_line, indent=8):
        return """{indentation}{optional_line}""".format(indentation=" "*indent, optional_line=optional_line)


class ValueArgs:
    def __init__(self, annotation):
        self.annotation = annotation
        self.role = annotation["role"]
        self.type = annotation["type"]
        self.selection = annotation["selections"][0]
        self.use_item = annotation["type"] == "qNode"
        self.cell_args = self.get_cell_args(self.selection)
        self.matches = {}
        self.match_found = False

    def get_cell_args(self, selection):
        return (selection["x1"]-1, selection["y1"]-1), (selection["x2"]-1, selection["y2"]-1)

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
        return self.cell_args[0][0], self.cell_args[1][0]

    @property
    def row_args(self):
        return self.cell_args[0][1], self.cell_args[1][1]

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

    def get_alignment(self, relative_args):
        # TODO: add heuristics for imperfect alignments
        if self.row_args == relative_args.row_args:
            return "row"
        if self.col_args == relative_args.col_args:
            return "col"
        return False

    def get_alignment_value(self, relative_args):
        # TODO: add costs for imperfect alignments
        if self.row_args == relative_args.row_args:
            return 3
        if self.col_args == relative_args.col_args:
            return 3
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

        if self.get_alignment(relative_value_args) == "row":
            col = column_index_to_letter(self.cell_args[0][0])
            return return_string.format(indexer=col+row_var)

        elif self.get_alignment(relative_value_args) == "col":
            row = str(self.cell_args[0][1]+1)
            return return_string.format(indexer=col_var+row)
        else:
            print("Don't know how to match with imperfect alignment yet" +
                  self.range_str + ","+relative_value_args.range_str)
            return "#TODO: ????? -Don't know how to match with imperfect alignment yet"


class Annotation():
    def __init__(self, annotation_blocks_array=None):
        self.annotation_block_array = annotation_blocks_array or []
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
            match_candidates[c_i].match_found = True

    def get_optionals_and_property(self, region, use_q):
        property = region.matches.get("property", None)
        if property is None:
            propertyLine = "#TODO-- no property alignment found"
        else:
            propertyLine = property.get_expression(region, use_q)

        indentation = 10 if use_q else 8
        optionalsLines = ""
        unit = region.matches.get("unit", None)
        if unit is not None:
            optionalsLines += YamlFormatter.get_optionals_string(
                "unit: " + unit.get_expression(region, use_q)+"\n", indentation)
        for key in region.annotation:
            if key not in ["role", "selections", "type"]:
                optionalsLines += YamlFormatter.get_optionals_string(
                    key+": "+region.annotation[key]+"\n", indentation)

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

            alignment = qualifier_region.get_alignment(data_region)
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

    def _generate_yaml(self, data_region, subject_region, qualifier_regions):

        region = "range: {range_str}".format(range_str=data_region.range_str)
        mainSubjectLine = subject_region.get_expression(data_region)

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
        return self.comment_messages + yaml

    def generate_yaml(self, sheet=None):
        return_string = self.comment_messages

        # check if no point in generating yet.
        if not self.data_annotations:
            return_string += "# cannot create yaml without a dependent variable\n"
        if not self.subject_annotations:
            return_string += "# cannot create yaml without a main subject\n"
        if return_string:
            return [return_string]

        data_regions = [ValueArgs(d) for d in self.data_annotations]
        subject_regions = [ValueArgs(s) for s in self.subject_annotations]
        qualifier_regions = [ValueArgs(q) for q in self.qualifier_annotations]

        property_regions = [ValueArgs(p) for p in self.property_annotations]
        unit_regions = [ValueArgs(m) for m in self.unit_annotations]
        self._run_cost_matrix(
            property_regions, [data_regions, qualifier_regions])
        self._run_cost_matrix(unit_regions, [data_regions, qualifier_regions])

        return_arr = []
        for data_region in data_regions:
            for subject_region in subject_regions:
                yaml = self._generate_yaml(
                    data_region, subject_region, qualifier_regions)
                return_arr.append(yaml)
        return return_arr

    def save(self, filepath):
        with open(filepath, 'w', encoding="utf-8") as f:
            f.write(json.dumps(self.annotation_block_array))

    @classmethod
    def load(cls, filepath):
        with open(filepath, 'r', encoding="utf-8") as f:
            annotations = json.load(f)
        instance = cls(annotations)
        return instance
