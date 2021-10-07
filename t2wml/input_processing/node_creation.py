import os
import pandas as pd
from t2wml.utils.bindings import update_bindings
from t2wml.input_processing.utils import get_Pnode, get_Qnode
from t2wml.wikification.utility_functions import get_provider, dict_to_kgtk, kgtk_to_dict
from t2wml.utils.debug_logging import basic_debug

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
        #const_property=region.annotation.get("property")
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
        
    #@basic_debug
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


