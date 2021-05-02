import numpy as np
from t2wml.input_processing.utils import string_is_valid
from t2wml.wikification.country_wikifier_cache import countries
from t2wml.utils.date_utils import parse_datetime
from t2wml.parsing.cleaning_functions import make_numeric

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
            if not string_is_valid(content):
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


def does_overlap(start_y, start_x, end_y, end_x, overlaps):
    for selection in overlaps:
        if selection:
            (x1, y1, x2, y2)=selection
            if (end_x<x1 or x2<start_x) or (start_y>y2 or y1>end_y):
                continue
            return True
    return False

def get_selection(sheet_data, rows, columns, two_d=False, overlaps=None):
    overlaps=overlaps or []
    indices=[(int(row), int(col)) for row, col in zip(rows, columns)]
    candidates={}

    for start_row, start_col in indices:
        if sheet_data[start_row][start_col]==0 or does_overlap(start_row, start_col, start_row, start_col, overlaps):
            continue
        
        #search for row
        col=start_col
        while (start_row, col) in indices and not does_overlap(start_row, start_col, start_row, col, overlaps):
            col+=1
        col-=1

        row=start_row
        if two_d:
            while(row, col) in indices and not does_overlap(start_row, start_col, row, col, overlaps):
                row+=1
            row-=1

        candidates[(start_row, row, start_col, col)]=0

        #search for column:
        row=start_row
        while (row, start_col) in indices and not does_overlap(start_row, start_col, row, start_col, overlaps):
            row+=1
        row-=1

        col=start_col
        if two_d:
            while(row, col) in indices and not does_overlap(start_row, start_col, row, col, overlaps):
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

