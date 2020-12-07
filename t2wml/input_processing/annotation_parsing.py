import json
import numpy as np
from munkres import Munkres
from t2wml.spreadsheets.conversions import cell_range_str_to_tuples, cell_str_to_tuple, column_index_to_letter


class YamlFormatter:
    @staticmethod
    def get_yaml_string(region, mainSubjectLine, propertyLine, optionalsLines, qualifierLines):
        yaml="""#AUTO-GENERATED YAML
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
    

def get_cell_args(range_str):
    if ":" in range_str:
        return cell_range_str_to_tuples(range_str)
    try:
        tuple=cell_str_to_tuple(range_str)
        return tuple, tuple
    except:
        return (None, None), (None, None)

class ValueArgs:
    def __init__(self, range_str, use_item=False):
        self.range_str=range_str
        self.use_item=use_item
        self.cell_args=get_cell_args(range_str)
        self.property_alignment=None
    
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
        if self.row_args==relative_args.row_args:
            return "row"
        if self.col_args==relative_args.col_args:
            return "col"
        return False
    
    def get_expression(self, relative_value_args, use_q=False):
        if self.use_item:
            return_string= "=item[{indexer}]"
        else:
            return_string= "=value[{indexer}]"
        
        if self.cell_args[0] == self.cell_args[1]: #single cell
            cell_str = column_index_to_letter(self.cell_args[0][0]) + ", " + str(self.cell_args[0][1]+1)
            return return_string.format(indexer=cell_str)
        
        row_var = ", $qrow-$n" if use_q else ", $row-$n"
        col_var= "$qcol-$n, " if use_q else "$col-$n, "
        
        if self.get_alignment(relative_value_args)=="row":
            col=column_index_to_letter(self.cell_args[0][0])
            return return_string.format(indexer=col+row_var)

        elif self.get_alignment(relative_value_args)=="col":
            row=str(self.cell_args[0][1]+1)
            return return_string.format(indexer=col_var+row)
        else:
            print("Don't know how to match with imperfect alignment yet"+self.range_str +","+relative_value_args.range_str)
            return "#TODO: ????? -Don't know how to match with imperfect alignment yet"
    



class Annotations:
    def __init__(self, data_regions, subject_regions, qualifier_regions=[], property_regions=[], sheet=None):
        self.data_regions=data_regions
        self.subject_regions=subject_regions
        self.qualifier_regions=qualifier_regions or []
        self.property_regions= property_regions or []
        self.sheet=sheet
        self.find_alignments()
    
    def find_alignments(self):
        num_properties=len(self.property_regions)
        num_to_assign=len(self.data_regions)+len(self.qualifier_regions)
        cost_matrix= np.empty((num_properties, num_to_assign), dtype=int)
        cost_matrix.fill(5)
        alignment_arr=[dat for dat in self.data_regions]+[qual for qual in self.qualifier_regions]

        for p_i, p_reg in enumerate(self.property_regions):
            for d_i, d_reg in enumerate(self.data_regions):
                if p_reg.get_alignment(d_reg):
                    cost_matrix[p_i][d_i]=1
                
            for q_i, q_reg in enumerate(self.qualifier_regions):
                if p_reg.get_alignment(q_reg):
                    cost_matrix[p_i][q_i+len(self.data_regions)]=1
        
        m=Munkres()
        indexes=m.compute(cost_matrix)
        not_matched=[True]*num_to_assign
        for (p_i, x_i) in indexes:
            not_matched[x_i]=False
            alignment_arr[x_i].property_alignment=self.property_regions[p_i]
        
        return indexes

    def get_yaml_parts(self, input_region, use_q=False):
        propertyLine=optionalsLines=""
        if input_region.property_alignment:
            propertyLine = input_region.property_alignment.get_expression(input_region, use_q)
        else: 
            propertyLine = "P2561  #??? #TODO-- no property alignment found"
            #TODO: can add heuristics here like P585 for points in time
        return propertyLine, optionalsLines
    
    def get_qualifier_yaml(self, qualifier_region: ValueArgs, data_region):
        propertyLine, optionalsLines = self.get_yaml_parts(qualifier_region, use_q=True)
        if qualifier_region.is_2D:
            if qualifier_region.use_item:
                valueLine="=item[$qcol, $qrow]"
            else:
                valueLine="=value[$qcol, $qrow]"
            
            alignment = qualifier_region.get_alignment(data_region)
            if alignment == False:
                region="range: "+qualifier_region.range_str
            else:
                if alignment == "col":
                    left=right="=$col"
                    top, bottom =qualifier_region.row_args
                    top+=1
                    bottom+=1

                else: # alignment == "row":
                    top=bottom="=$row"
                    left, right = qualifier_region.col_args
                    left, right = column_index_to_letter(left), column_index_to_letter(right)

            
                region="""left: {left}
                        right: {right}
                        top: {top}
                        bottom: {bottom}""".format(left=left, right=right, top=top, bottom=bottom)
            


            qualifier_string = """
                - region: 
                        {region}
                  property: {propertyLine}
                  value: =value[$qcol, $qrow]
                {optionalsLines}""".format(region=region, propertyLine=propertyLine, valueLine=valueLine, optionalsLines=optionalsLines)

        else:
            valueLine=qualifier_region.get_expression(data_region)
            qualifier_string = """
                - property: {propertyLine}
                  value: {valueLine}
                {optionalsLines}""".format(propertyLine=propertyLine, valueLine=valueLine, optionalsLines=optionalsLines)
        return qualifier_string

    def generate_yaml(self):
        yamls=[]
        for data_region in self.data_regions:
            for subject_region in self.subject_regions:
                region="range: {range_str}".format(range_str=data_region.range_str)
                propertyLine, optionalsLines = self.get_yaml_parts(data_region)
                mainSubjectLine=subject_region.get_expression(data_region)
                if len(self.qualifier_regions):
                    qualifierLines="qualifier:"
                    for qualifier in self.qualifier_regions:
                        qualifierLines+=self.get_qualifier_yaml(qualifier, data_region)
                else:
                    qualifierLines=""
                yaml=YamlFormatter.get_yaml_string(region, mainSubjectLine, propertyLine, optionalsLines, qualifierLines)
                yamls.append(yaml)
        return yamls





class DynamicallyGeneratedAnnotation:
    def __init__(self, data_regions=None, subject_regions=None, qualifier_regions=None, metadata_regions=None, property_regions=None):
        self.data_regions= data_regions or []
        self.subject_regions= subject_regions or []
        self.qualifier_regions= qualifier_regions or []
        self.metadata_regions= metadata_regions or []
        self.property_regions= property_regions or []
    
    def _generate_alignments(self):
        pass

    def _generate_yaml(self, data_region, subject_region):
        pass
    
    def generate_yaml(self):
        return_string=""
        
        #check if no point in generating yet.
        if not self.data_regions:
            return_string+="# cannot create yaml without a dependent variable\n"
        if not self.subject_regions:
            return_string+="# cannot create yaml without a main subject\n"
        if return_string:
            return [return_string]
        
        alignments=self._generate_alignments()

        return_arr=[]
        for data_region in alignments.data_regions:
            for subject_region in alignments.subject_regions:
                yaml = self._generate_yaml(data_region, subject_region, alignments)
                return_arr.append(yaml)
        return return_arr
    
    def add_annotation(self, annotation):
        role=annotation["role"]
        if role=="dependentVar":
            self.data_regions.append(annotation)
        elif role=="mainSubject":
            self.subject_regions.append(annotation)
        elif role=="qualifier":
            self.qualifier_regions.append(annotation)
        elif role=="property":
            self.property_regions.append(annotation)
        elif role=="metadata":
            self.metadata_regions.append(annotation)
        else:
            raise ValueError("unrecognized role type for annotation")
    
    def save(self, filepath):
        with open(filepath, 'w', encoding="utf-8") as f:
            f.write(json.dumps(self.__dict__))
    
    @classmethod
    def load(cls, filepath):
        with open(filepath, 'r', encoding="utf-8") as f:
            annotations=json.load(f)
        instance = cls(**annotations)
        return instance