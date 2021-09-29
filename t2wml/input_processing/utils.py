import math
import re
from string import punctuation
from t2wml.utils.t2wml_exceptions import InvalidAnnotationException

try:
    from math import dist
except:
    def dist(point1, point2):
        (x1,y1) = point1
        (x2,y2) = point2
        distance = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        return distance

nonalphanumeric = re.compile(r'[^A-Za-z0-9\s]+')
spaces=re.compile(r"\s")


def clean_id(input):
    '''
    remove non alphanumeric characters and lowercase
    replace whitespace by _ (underscore)
    '''
    output = str(input)
    output = nonalphanumeric.sub('', output)
    output = output.strip().lower() #needs to be here to prevent trailing underscore
    output = spaces.sub("_", output)
    if not output:
        raise ValueError(f"Cleaning {input} returned empy string for id")
    return output



def check_special_characters(text: str) -> bool:
    return all(char in punctuation for char in str(text))

def string_is_valid(text: str) -> bool:
    text=str(text)
    if not text:
        return False
    text = text.strip().lower()
    if check_special_characters(text):
        return False
    if text in ["", "#na", "nan"]:
        return False
    return True



def get_Qnode(project, item):
    return f"QCustomNode-{clean_id(item)}"
    #return f"Q{project.dataset_id}-{clean_id(item)}"
    
def get_Pnode(project, property):
    return f"PCustomNode-{clean_id(property)}"
    #return f"P{project.dataset_id}-{clean_id(property)}"


def rect_distance(rect1, rect2):
    if rect1 is None or rect2 is None:
        return None
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



def normalize_rectangle(annotation):
    selection = annotation["selection"]
    top=min(selection["y1"], selection["y2"])
    bottom=max(selection["y1"], selection["y2"])
    left=min(selection["x1"], selection["x2"])
    right=max(selection["x1"], selection["x2"])
    annotation["selection"]={"x1": left, "x2": right, "y1":top, "y2":bottom}