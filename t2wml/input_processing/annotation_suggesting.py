from collections import Counter
from math import floor
from t2wml.input_processing.utils import string_is_valid
from t2wml.wikification.country_wikifier_cache import countries
from t2wml.utils.date_utils import parse_datetime
from t2wml.parsing.cleaning_functions import strict_make_numeric

def get_types(cell_content):
    cell_content=str(cell_content).strip()
    is_country = cell_content in countries or cell_content.lower() in countries
    if strict_make_numeric(cell_content) != "" and cell_content[0] not in ["P", "Q"]:
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
    type=None

    if is_country:
        if not already_has_subject:
            role="mainSubject"
        else:
            role="qualifier"
            type="wikibaseitem"
    
    elif is_date:
        role="qualifier"
        type="time"
        children["property"]="P585"
    
    elif is_numeric:
        if not already_has_var:
            role="dependentVar"
        else:
            role="qualifier"
        type="quantity"

    else:
        if x1==x2 and y1==y2: #single cell selection, default to property
            role="property"
        else: #all else, default to qualifier
            role="qualifier"
        type="string"

    suggestion=dict(role=role, children=children)
    if type:
        suggestion["type"]=type

    return suggestion


class HistogramSelection:
    @staticmethod
    def block_finder(sheet):
        vertical_numbers=Counter()
        horizontal_numbers=Counter()
        horizontal_dates=Counter()
        vertical_dates=Counter()
        horizontal_countries=Counter()
        vertical_countries=Counter()
        blanks=set()
        numbers=set()
        dates=set()
        countries=set()

        for row in range(sheet.row_len):
            for col in range(sheet.col_len):
                content = sheet[row, col]
                if not string_is_valid(content):
                    blanks.add((row, col))
                    continue
                is_country, is_numeric, is_date=get_types(content)
                if is_country:
                    if is_numeric: #for now override "numeric" countries
                        vertical_numbers[col]+=1
                        horizontal_numbers[row]+=1
                        numbers.add((row, col))
                    else:
                        horizontal_countries[row]+=1
                        vertical_countries[col]+=1
                        countries.add((row, col))
                elif is_date:
                    horizontal_dates[row]+=1
                    vertical_dates[col]+=1
                    dates.add((row, col))
                    if is_numeric:
                        vertical_numbers[col]+=1
                        horizontal_numbers[row]+=1
                        numbers.add((row, col))
                elif is_numeric:
                    vertical_numbers[col]+=1
                    horizontal_numbers[row]+=1
                    numbers.add((row, col))
        
        date_index, date_is_vertical= HistogramSelection.get_most_common(horizontal_dates, vertical_dates)
        date_count=horizontal_dates[date_index]
        country_index, country_is_vertical= HistogramSelection.get_most_common(horizontal_countries, vertical_countries)
        country_count=horizontal_dates[country_index]

        date_block=HistogramSelection.get_1d_block(sheet, date_index, date_is_vertical, date_count, dates, blanks)
        country_block=HistogramSelection.get_1d_block(sheet, country_index, country_is_vertical, country_count, countries, blanks)
        number_block=HistogramSelection.get_2d_block(sheet, horizontal_numbers, vertical_numbers, numbers, blanks, [date_block, country_block])
        
        date_block=HistogramSelection.normalize_to_selection(date_block, number_block)
        country_block=HistogramSelection.normalize_to_selection(country_block, number_block)

        return HistogramSelection._create_annotations(date_block, country_block, number_block)
        
    def normalize_to_selection(selection, normalize_against):
        if not normalize_against or not selection:
            return selection
        (nr1, nc1), (nr2, nc2) = normalize_against
        (r1, c1),(r2, c2) = selection
        if r1==r2 and c1!=c2: #row
            return (r1, nc1), (r2, nc2)
        if c1==c2 and r1!=r2: #column
            return (nr1, c1),(nr2, c2)
        return selection
    
    def _create_annotations(date_block, country_block, number_block):
        annotations=[]
        if date_block:
            annotations.append({
                    "selection":dict(x1=date_block[0][1]+1, y1=date_block[0][0]+1, x2= date_block[1][1]+1, y2=date_block[1][0]+1),
                    "role":"qualifier",
                    "type": "time",
                    "property": "P585"
            })

        if country_block:
            annotations.append({
                    "selection":dict(x1=country_block[0][1]+1, y1=country_block[0][0]+1, x2= country_block[1][1]+1, y2=country_block[1][0]+1),
                    "role":"mainSubject",
                    "type": "wikibaseitem",
            })
        if number_block:
            annotations.append({
                    "selection":dict(x1=number_block[0][1]+1, y1=number_block[0][0]+1, x2= number_block[1][1]+1, y2=number_block[1][0]+1),
                    "role":"dependentVar",
                    "type": "quantity",
            })

        return annotations

    def get_most_common(horizontal, vertical):
        if horizontal:
            h_index, h_count = horizontal.most_common(1)[0]
        else:
            h_count=0
        if vertical:
            v_index, v_count = vertical.most_common(1)[0]
        else:
            v_count=0
        if v_count==h_count==0:
            return None, None
        if h_count>v_count:
            return h_index, False
        return v_index, True
    
    def get_1d_block(sheet, index, is_vertical, count, block_set, blank_set):
        if index is None:
            return None
        threshold= max(floor(0.1 * count), 1)
        contig_dict={}
        if is_vertical:
            column=index
            start_row=0
            while start_row<sheet.row_len:
                total=0
                for initial_row in range(start_row, sheet.row_len):
                    if (initial_row, column) in block_set:
                        break
                
                row=initial_row
                while row < sheet.row_len:
                    bad_skips=0
                    while not ((row, column) in block_set):
                        if not ((row, column) in blank_set):
                            bad_skips+=1
                            if bad_skips>threshold:
                                break
                        row+=1

                    if bad_skips>threshold:
                        break
                    row+=1
                    total+=1
                
                #remove blanks and invalids
                final_row=row
                for final_row in range(row, 0, -1):
                    if (final_row, column) in block_set:
                        break
                    total-=1
                contig_dict[((initial_row, column), (final_row, column))] = total
                start_row=row+1
            return max(contig_dict, key=lambda p: contig_dict[p])

        else:        #horizontal:
            row=index
            start_column=0
            while start_column<sheet.col_len:
                total=0
                for initial_column in range(start_column, sheet.col_len):
                    if (row, initial_column) in block_set:
                        break

                col=initial_column
                while row < sheet.row_len:
                    bad_skips=0
                    while not ((row, col) in block_set):
                        if not ((row, col) in blank_set):
                            bad_skips+=1
                            if bad_skips>threshold:
                                break
                        col+=1
                    if bad_skips>threshold:
                        break
                    col+=1
                    total+=1

                for final_column in range(col, 0, -1):
                    total-=1
                    if (row, final_column) in block_set:
                        break
                contig_dict[((row, initial_column), (row, final_column))] = total
                start_column=col+1

            return max(contig_dict, key=lambda p: contig_dict[p])

    def get_2d_block(sheet, horizontal_count, vertical_count, block_set, blank_set, blocks_to_avoid):
        for block in blocks_to_avoid:
            if block:
                (start_r, start_c), (end_r, end_c) = block
                for r in range(start_r, end_r+1):
                    for c in range(start_c, end_c+1):
                        if (r,c) in block_set:
                            block_set.remove((r,c))
                            vertical_count[c]-=1
                            horizontal_count[r]-=1

        contiguous_columns=dict()
        start_i=0
        while start_i<sheet.col_len:
            contiguous_columns[start_i]=dict(count=0)
            for j in range(start_i, sheet.col_len+1):
                if vertical_count[j]:
                    contiguous_columns[start_i]["count"]+=vertical_count[j]
                else:
                    break
            contiguous_columns[start_i]["finish"]=j-1
            start_i=j+1
        start_column=max(contiguous_columns, key=lambda p: contiguous_columns[p]["count"])
        end_column=contiguous_columns[start_column]["finish"]
        v_index, v_count = vertical_count.most_common(1)[0]
        ((initial_row, column), (final_row, column))=HistogramSelection.get_1d_block(sheet, start_column, True, v_count, block_set, blank_set)
        return (initial_row, start_column), (final_row, end_column)
            

def block_finder(sheet): #convenience function
    return HistogramSelection.block_finder(sheet)
