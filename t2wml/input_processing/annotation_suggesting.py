from collections import Counter, defaultdict
from math import floor
from t2wml.input_processing.annotation_parsing import rect_distance
from t2wml.input_processing.utils import string_is_valid, rect_distance
from t2wml.wikification.country_wikifier_cache import countries, causx_only_countries
from t2wml.utils.date_utils import parse_datetime
from t2wml.parsing.cleaning_functions import strict_make_numeric
from t2wml.utils.debug_logging import basic_debug

time_property_node = {"id": "P585", 
                "label":"point in time", 
                "description": "time and date something took place, existed or a statement was true",
                "data_type": "time"}
country_trans = str.maketrans("-.,", "   ")

def get_types(cell_content):
    """given the content of the cell, check if it could be a country, numeric, or a date

    Args:
        cell_content (str): string of cell content

    Returns:
        (bool, bool, bool): is_country, is_numeric, is_date
    """
    cell_content=str(cell_content).strip().lower()

    country_cell_content = " ".join((cell_content.translate(country_trans).replace("&", " and ")).split())
    is_country = country_cell_content in countries or country_cell_content in causx_only_countries
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

#@basic_debug
def guess_block(sheet, selection, annotation_blocks_array):
    """guess what the annotation for a selection on a sheet should be

    Args:
        sheet (Sheet): the sheet we are annotating
        selection (dict): 1-indexed {x1, y1, x2, y2} dictionary
        annotation_blocks_array (list): existing annotation, an array of blocks (can be an empty array)

    Returns:
        dict: suggestion for annotation - will contain role, type, and additional fields in key "children"
    """
    already_has_subject=False
    already_has_var=False
    for block in annotation_blocks_array:
        if block["role"]=="mainSubject":
            already_has_subject=True
        if block["role"]=="dependentVar":
            already_has_var=True

    (x1, y1), (x2, y2) = (selection["x1"]-1, selection["y1"]-1), (selection["x2"]-1, selection["y2"]-1)
    totals = [0,0,0]
    cells=[]
    cells.append(sheet[y1, x1])
    cells.append(sheet[y2, x2])
    if y1!=y2:
        cells.append(sheet[floor((y2-y1)/2), x1])
    if x1!=x2:
        cells.append(sheet[y1, floor((x2-x1)/2)])
    for cell in cells:
        cell=str(cell).strip()
        if not cell:
            continue
        result_tuple = get_types(cell)
        for i, b_result in enumerate(result_tuple):
            if b_result:
                totals[i]+=1
    for i in range(len(totals)):
        totals[i] = totals[i]/len(cells)
        totals[i] = True if totals[i]>=0.5 else False
    totals=tuple(totals)
    is_country, is_numeric, is_date = totals


    children={} #this is a terrible name. Really it's additional fields like "property" or "unit"
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
        children["property"]=time_property_node
    
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
    """A class for running the histogram algorithm for finding blocks to create an annotation

    Args:
        sheet (Sheet): the sheet we are creating an annotation for
    
    
    Attributes:
        sheet (Sheet): the sheet we are creating an annotation for
        rows (list): a list of integer indices for rows on the sheet. if sheet length<=300, is just rows 0-300. otherwise, is a sub-selection of rows
        use_row_subset (bool): flag indicating whether rows is a sub-selection of rows or not.
    """
    def __init__(self, sheet):
        self.sheet=sheet

        if sheet.row_len>300:
            self.use_row_subset= True
            half = floor(sheet.row_len * 0.5)
            rows = [*range(0, 100), *range(half-50, half+50), *range(sheet.row_len-100, sheet.row_len)]
        else:
            self.use_row_subset = False
            rows = [*range(sheet.row_len)]
        
        self.rows=rows
    
    def block_finder(self):
        """finds all the blocks, modifies them, returns resulting annotation"""
        sheet=self.sheet

        count_by_col_numbers=Counter()
        count_by_row_numbers=Counter()
        count_by_row_dates=Counter()
        count_by_col_dates=Counter()
        count_by_row_countries=Counter()
        count_by_col_countries=Counter()
        blanks=set()
        numbers=set()
        dates=set()
        countries=set()


        for row in self.rows:
            for col in range(sheet.col_len):
                content = sheet[row, col]
                if not string_is_valid(content):
                    blanks.add((row, col))
                    continue
                is_country, is_numeric, is_date=get_types(content)
                if is_country:
                    if is_numeric: #for now override "numeric" countries
                        count_by_col_numbers[col]+=1
                        count_by_row_numbers[row]+=1
                        numbers.add((row, col))
                    else:
                        count_by_row_countries[row]+=1
                        count_by_col_countries[col]+=1
                        countries.add((row, col))
                elif is_date:
                    count_by_row_dates[row]+=1
                    count_by_col_dates[col]+=1
                    dates.add((row, col))
                    if is_numeric:
                        count_by_col_numbers[col]+=1
                        count_by_row_numbers[row]+=1
                        numbers.add((row, col))
                elif is_numeric:
                    count_by_col_numbers[col]+=1
                    count_by_row_numbers[row]+=1
                    numbers.add((row, col))
        
        date_index, date_is_column, date_count= self.get_most_common(count_by_row_dates, count_by_col_dates)
        country_index, country_is_column, country_count = self.get_most_common(count_by_row_countries, count_by_col_countries)

        date_block=self.get_1d_block(date_index, date_is_column, date_count, dates, blanks)
        country_block=self.get_1d_block(country_index, country_is_column, country_count, countries, blanks)
        number_block=self.get_2d_block(count_by_row_numbers, count_by_col_numbers, numbers, blanks, [date_block, country_block])
        
        date_block, country_block, number_block = self.normalization_and_overlaps(date_block, date_is_column, country_block, country_is_column, number_block)
        return self._create_annotations(date_block, country_block, number_block)
    

    def get_most_common(self, count_by_row, count_by_column):
        """find the row or the column with the highest count (normalized to dimensions)

        Args:
            count_by_row (Counter): counter with count for each row
            count_by_column (Counter): counter with count for each column

        Returns:
            index (int): index of the column or row with highest normalized count
            is_column (bool): is it a column, or a row?
            count (int): the count (not normalized)
        """
        num_rows = len(self.rows)
        num_cols = self.sheet.col_len
        if count_by_row:
            h_index, h_count = count_by_row.most_common(1)[0]
        else:
            h_count=0
        if count_by_column:
            v_index, v_count = count_by_column.most_common(1)[0]
        else:
            v_count=0
        h_count_norm = h_count/num_cols
        v_count_norm = v_count/num_rows
        
        if v_count_norm==h_count_norm==0:
            return None, None, 0
        if h_count_norm>v_count_norm:
            return h_index, False, h_count
        return v_index, True, v_count
    
    def get_1d_block(self, index, is_column, count, block_set, blank_set):
        """get the rectangle coordinates for a "1-dimensional" block

        Args:
            index (int): index of row or column
            is_column (bool): is it a columns, or a row?
            count (int): how many cells of the type are in the chosen row/column
            block_set (set): a set with index tuples (row, col) for each cell that fits the block category
            blank_set (set): a set with index tuples (row, col) for each cell that are blank

        Returns:
            tuple: ((x1, y1), (x2, y2)) 0-indexed rectangle coordinates. can also return None.
        """
        sheet = self.sheet
        if index is None:
            return None
        
        #if we are using a row subset and we are checking a column, there's no checking of threshold for blanks
        # (as our row sample is already "skewing" results)
        if self.use_row_subset and is_column:
            column = index
            for initial_row in range(0, sheet.row_len):
                if (initial_row, column) in block_set:
                    break
            for final_row in range(sheet.row_len, initial_row, -1):
                if (final_row, column) in block_set:
                    break
            return ((column, initial_row), (column, final_row))

        # in all other cases, have a threshold of blank cells where past a certain number we assume the block has ended
        threshold= max(floor(0.1 * count), 1)
        contig_dict={}

        if is_column:
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
                contig_dict[((column, initial_row), (column, final_row))] = total
                start_row=row+1
            return max(contig_dict, key=lambda p: contig_dict[p])

        else:  #is row
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
                contig_dict[((initial_column, row), (final_column, row))] = total
                start_column=col+1

            return max(contig_dict, key=lambda p: contig_dict[p])
        

    def get_2d_block(self, horizontal_count, vertical_count, block_set, blank_set, blocks_to_avoid):
        """[summary]

        Args:
            horizontal_count ([type]): [description]
            vertical_count ([type]): [description]
            block_set ([type]): [description]
            blank_set ([type]): [description]
            blocks_to_avoid ([type]): [description]

        Returns:
            [type]: [description]
        """
        sheet=self.sheet
        for block in blocks_to_avoid:
            if block:
                (start_c, start_r), (end_c, end_r) = block
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
        two_d_block=self.get_1d_block(start_column, True, v_count, block_set, blank_set)
        ((column, initial_row), (column, final_row)) = two_d_block        
        return (start_column, initial_row), (end_column, final_row)
            
    def fix_overlaps(self, block_to_shrink, other_block, is_column):
        if block_to_shrink is None:
            return None
        if other_block is None:
            return block_to_shrink

        (base_start_c, base_start_r), (base_end_c, base_end_r) = block_to_shrink

        test=rect_distance(block_to_shrink, other_block)
        if test!=0: #no overlap
            return block_to_shrink

        (start_c, start_r), (end_c, end_r) = other_block
        if is_column: #need to adjust columns
            if start_c==base_start_c:
                base_start_c+=1
            elif end_c==base_end_c:
                base_end_c-=1
            else: #is somewhere in the middle
                left = start_c - base_start_c
                right = base_end_c - end_c
                if left>right:
                    base_end_c = start_c-1 #take the left rectangle
                else:
                    base_start_c = end_c+1 #take the right rectangle
        else: #need to adjust rows
            if start_r==base_start_r:
                base_start_r+=1
            elif end_r==base_end_r:
                base_end_r-=1
            else: #is somewhere in the middle
                top = start_r - base_start_r
                bottom = base_end_r - end_r
                if top>bottom:
                    base_end_r = start_r-1 #take the left rectangle
                else:
                    base_start_r = end_r+1 #take the right rectangle
        return (base_start_c, base_start_r), (base_end_c, base_end_r)

    def normalize_to_selection(self, selection, normalize_against):
        if not normalize_against or not selection:
            return selection
        (nc1, nr1), (nc2, nr2) = normalize_against
        (c1, r1),(c2, r2) = selection
        if r1==r2 and c1!=c2: #row
            return (nc1, r1), (nc2, r2)
        if c1==c2 and r1!=r2: #column
            return (c1, nr1),(c2, nr2)
        return selection
    
    def normalization_and_overlaps(self, date_block, date_is_column, country_block, country_is_column, number_block):
        if not number_block:
            return date_block, country_block, number_block
        
        number_block = self.fix_overlaps(number_block, date_block, date_is_column)
        number_block = self.fix_overlaps(number_block, country_block, country_is_column)
        
        if country_block:
            normalized_country_block=self.normalize_to_selection(country_block, number_block)
            if rect_distance(normalized_country_block, number_block)!=0 and \
                rect_distance(normalized_country_block, date_block)!=0:
                    country_block=normalized_country_block

        if date_block:
            normalized_date_block=self.normalize_to_selection(date_block, number_block)
            if rect_distance(normalized_date_block, number_block)!=0 and \
                rect_distance(normalized_date_block, country_block)!=0:
                    date_block=normalized_date_block
        
        return date_block, country_block, number_block
    
    def _create_annotations(self, date_block, country_block, number_block):
        annotations=[]
        if date_block:
            annotations.append({
                    "selection":dict(x1=date_block[0][0]+1, y1=date_block[0][1]+1, x2= date_block[1][0]+1, y2=date_block[1][1]+1),
                    "role":"qualifier",
                    "type": "time",
                    "property": time_property_node
            })

        if country_block:
            annotations.append({
                    "selection":dict(x1=country_block[0][0]+1, y1=country_block[0][1]+1, x2= country_block[1][0]+1, y2=country_block[1][1]+1),
                    "role":"mainSubject",
                    "type": "wikibaseitem",
            })
        if number_block:
            annotations.append({
                    "selection":dict(x1=number_block[0][0]+1, y1=number_block[0][1]+1, x2= number_block[1][0]+1, y2=number_block[1][1]+1),
                    "role":"dependentVar",
                    "type": "quantity",
            })
        

        return annotations




def guess_annotation(sheet):
    """guess annotation for a sheet"""
    h=HistogramSelection(sheet)
    return h.block_finder()
