from t2wml.input_processing.annotation_suggesting import annotation_suggester,  block_finder
from t2wml.input_processing.annotation_parsing import Annotation
from t2wml.api import Sheet






def add_annotation_from_suggestion(sheet, selection, annotations):
    suggestion=annotation_suggester(sheet, selection, annotations)
    annotations.append(
        {
                "selection":selection,
                "role":suggestion["roles"][0],
                "type": suggestion["types"][0],
        }
    )
    return annotations



def test_suggestions():
    csv_string="""main subject,date qualifier,ugly numbers,numbers with stuff
ethiopia,1998,10 000 000,$100
ethiopia,1997,12 450,100$
panama,11/14/2011, ..,abcde
panama,14/11/2011,"13,400",200.8
italy,"July 4, 2011",100,2.00E+21
italy,"July 4, 2012",200,11"""
    sheet= Sheet.load_sheet_from_csv_string(csv_string)
    selection={"x1":3,"x2":4,"y1":2,"y2":7} #depvar
    annotations=add_annotation_from_suggestion(sheet, selection, [])
    #add property block manually
    annotations.append({"selection":{"x1":3,"x2":4,"y1":1,"y2":1},
        "role":"property"})
    selection={"x1":2,"x2":2,"y1":2,"y2":7} #qualifier
    annotations=add_annotation_from_suggestion(sheet, selection, annotations)
    selection={"x1":2,"x2":2,"y1":1,"y2":1}#qual prop
    annotations=add_annotation_from_suggestion(sheet, selection, annotations)
    selection={"x1":1,"x2":1,"y1":2,"y2":7} #main subject
    annotations=add_annotation_from_suggestion(sheet, selection, annotations)
    a=Annotation(annotations)
    #print(a.generate_yaml())

def test_blocks_from_csv():
    csv_string="""date qualifier,ugly numbers,numbers with stuff
"",ethiopia,panama
1998,10 000 000,$100
1997,12 450,100$
11/14/2011, ..,abcde
14/11/2011,"13,400",200.8
"July 4, 2011",100,2.00E+21
"July 4, 2012",200,11"""

    s=Sheet.load_sheet_from_csv_string(csv_string, header=None)
    block_finder(s)

def test_block_from_sheet():
    data_file=r"C:\Users\devora\C_sources\pedro\various files\coumntry-wikifier-bug\FreedomHousePressFreedomIndex.csv"
    sheet_name="FreedomHousePressFreedomIndex"
    s=Sheet(data_file, sheet_name)
    a=block_finder(s)
    # a)
