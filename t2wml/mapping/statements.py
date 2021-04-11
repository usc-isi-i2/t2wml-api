from copy import deepcopy
from collections import defaultdict
from t2wml.input_processing.region import YamlRegion
import t2wml.utils.t2wml_exceptions as T2WMLExceptions
from t2wml.parsing.t2wml_parsing import iter_on_n_for_code, T2WMLCode
from t2wml.parsing.classes import ReturnClass
from t2wml.spreadsheets.conversions import to_excel
from t2wml.wikification.utility_functions import get_property_type
from t2wml.utils.ethiopian_date import EthiopianDateConverter
from t2wml.utils.date_utils import VALID_PROPERTY_TYPES, parse_datetime
from t2wml.settings import t2wml_settings


class StatementError:
    def __init__(self, message, field, qualifier=-1, level=None):
        #set role
        if qualifier>-1:
            role="qualifier"
            level="Minor" if level is None else level
        else:
            role=field
            if field not in ["value", "subject",  "property", "unit"]:
                role="value"
                level="Minor" if level is None else level

        #set level
        if role in ["value", "subject", "property"]:
            level="Major" if level is None else level
        else:
            level="Minor" if level is None else level

        self.role=role
        self.message=message
        self.qualifier_index=qualifier
        self.level=level
        self.field=field


def fake_iter():
    yield None, None


def handle_ethiopian_calendar(node, add_node_list):
    calendar = node.__dict__.get("calendar")
    if calendar in ["Q215271", "Ethiopian"]:
        if t2wml_settings.handle_calendar!="leave":
            try:
                gregorian_value = EthiopianDateConverter.iso_to_gregorian_iso(node.value)
                if t2wml_settings.handle_calendar=="replace":
                    node.value=gregorian_value
                if t2wml_settings.handle_calendar=="add":
                    new_node=Node(**deepcopy(node.__dict__), validate=False)
                    new_node.value=gregorian_value
                    new_node.__dict__["calendar"]="Q1985727"
                    #TODO: handle precision
                    add_node_list.append(new_node)
            except Exception as e:
                node._errors.append(StatementError(field="calendar",
                                                    message="Failed to convert to gregorian calendar: "+str(e),
                                                    qualifier=node.qualifier_index),
                                                    level="Minor")

class Node:
    def __init__(self, property=None, value=None, validate=True, qualifier_index=-1, **kwargs):
        self._errors = []
        self.property = property
        self.value = value
        self.qualifier_index=qualifier_index
        self.__dict__.update(kwargs)
        if validate:
            self.validate()

    @property
    def errors(self):
        return list(self._errors)

    def validate(self):
        if t2wml_settings.no_wikification:
            return

        try:
            if self.property:
                try:
                    property_type = get_property_type(self.property)
                except Exception as e:
                    self._errors.append(StatementError(field="property",
                                                    message="Could not get property type for " + str(self.property),
                                                    qualifier=self.qualifier_index))
                    property_type = "Not found"
            else:
                self._errors.append(StatementError(field="property",
                                                    message="Missing property",
                                                    qualifier=self.qualifier_index))
                property_type = "Not found"
        except AttributeError:  # we init value, but it might be popped elsewhere, don't assume it exists
            #Not creating an error here because it's created when we pop elsewhere?
            property_type = "Not found"

        try:
            if self.value is not None:
                if property_type == "quantity":
                    try:
                        float(self.value)
                    except:
                        self._errors.append(StatementError(field="value",
                                                    message="Quantity type property must have numeric value",
                                                    qualifier=self.qualifier_index))

                if property_type == "time":
                    self.validate_datetime()
            else:
                if property_type == "globecoordinate":
                    try:
                        test_coordinate_presence = [
                            self.longitude, self.latitude]
                    except AttributeError:
                        self._errors.append(StatementError(field="value",
                                                    message="GlobeCoordinates must specify longitude and latitude or point value",
                                                    qualifier=self.qualifier_index))
                else:
                    self._errors.append(StatementError(field="value",
                                                    message="Missing value field",
                                                    qualifier=self.qualifier_index))
        except AttributeError:  # we init value, but it might be popped elsewhere, don't assume it exists
            #Not creating an error here because it's created when we pop elsewhere?
            pass

        if property_type not in VALID_PROPERTY_TYPES and property_type!="Not found":
            self._errors.append(StatementError(field="property",
                                                message="Unsupported property type: "+property_type,
                                                qualifier=self.qualifier_index))

    def validate_datetime(self):
        try:
            datetime_string, parsed_precision, used_format = parse_datetime(
                self.value,
                additional_formats=self.__dict__.get("format", []),
                precisions=self.__dict__.get("precision", [])
            )
            self.value = datetime_string
            if parsed_precision:
                self.precision = parsed_precision
            if used_format:
                self.format=used_format
        except:
            self._errors.append(StatementError(field="value",
                                               message="Invalid datetime: "+str(self.value),
                                               qualifier=self.qualifier_index))
        

    def serialize(self):
        return_dict = dict(self.__dict__)
        return_dict.pop("_errors")
        return_dict.pop("qualifier_index")
        return return_dict


class Statement(Node):
    @property
    def node_class(self):
        return Node

    @property
    def has_qualifiers(self):
        try:
            test = self.qualifier
            return True
        except AttributeError:
            return False

    @property
    def has_references(self):
        try:
            test = self.reference
            return True
        except AttributeError:
            return False
    
    def validate(self):
        raise NotImplementedError

    def serialize(self):
        return_dict = super().serialize()
        if self.has_qualifiers:
            for i, q in enumerate(return_dict["qualifier"]):
                return_dict["qualifier"][i] = q.serialize()
        if self.has_references:
            for i, q in enumerate(return_dict["reference"]):
                return_dict["reference"][i] = q.serialize()
        return return_dict


class NodeForEval(Node):
    def __init__(self, property=None, value=None, context={}, **kwargs):
        self.context = context
        self.cells = {}
        super().__init__(property, value, **kwargs)

    def parse_key(self, key):
        cell_indices=None, None
        if key=="region": #skip
            return cell_indices
        if isinstance(self.__dict__[key], T2WMLCode):
            try:
                entry_parsed = iter_on_n_for_code(
                    self.__dict__[key], self.context)
                try:
                    value = entry_parsed.value
                except AttributeError:
                    if not isinstance(entry_parsed, ReturnClass): #sometimes parses to a string or number, not a returnclass
                        value=str(entry_parsed)
                    else:
                        value=None
                if value is None:
                    self._errors.append(StatementError(field=key,
                                                    message=f"Failed to resolve for {key} ({self.__dict__[key].unmodified_str})",
                                                    qualifier=self.qualifier_index))
                    self.__dict__.pop(key)
                elif value=="":
                    if t2wml_settings.warn_for_empty_cells:
                        self._errors.append(StatementError(field=key,
                                            message="Empty cell",
                                            qualifier=self.qualifier_index,
                                            type="Minor"))
                    self.__dict__.pop(key)
                else:
                    self.__dict__[key] = value

                try:
                    cell_indices= (entry_parsed.col, entry_parsed.row)
                    cell = to_excel(entry_parsed.col, entry_parsed.row)
                    self.cells[key] = cell
                except AttributeError:
                    pass

            except Exception as e:
                self._errors.append(StatementError(field=key,
                                    message=f"Error parsing {key} ({self.__dict__[key].unmodified_str}): {str(e)}",
                                                    qualifier=self.qualifier_index))
                self.__dict__.pop(key)
        return cell_indices

    def validate(self):
        t_var_qcol=self.context.get("t_var_qcol", None) #if it isn't already defined outside
        if t_var_qcol is None:
            (col, row)=self.parse_key("value")
            if col is not None:
                self.context.update({"t_var_qcol":col+1, "t_var_qrow":row+1})
        for key in list(self.__dict__.keys()):
            self.parse_key(key)
        Node.validate(self)


    def serialize(self):
        return_dict = super().serialize()
        return_dict.pop("context", None)
        return_dict.pop("region", None)
        return return_dict


class EvaluatedStatement(Statement, NodeForEval):
    @property
    def node_class(self):
        return NodeForEval

    def validate(self):
        try:
            subject = self.subject
        except AttributeError:
            self._errors.append(StatementError(field="subject",
                                    message="Missing subject",
                                    qualifier=False))

        self.node_class.validate(self)
        self.context.pop("t_var_qrow", None)
        self.context.pop("t_var_qcol", None)

        gregorian_nodes=[]

        if self.has_qualifiers:
            new_qualifiers = []
            for i, q in enumerate(self.qualifier):
                region=q.get("region", None)
                if region:
                    iterator=YamlRegion(region, context=self.context)
                else:
                    iterator=fake_iter()
                for col, row in iterator:
                    try:
                        q_context=dict(t_var_qrow=row, t_var_qcol=col)
                        q_context.update(self.context)
                        node_qual = self.node_class(context=q_context, qualifier_index=i, **q)
                        handle_ethiopian_calendar(node_qual, gregorian_nodes)

                        self._errors+=node_qual.errors
                        
                        try:
                            node_qual.value
                        except AttributeError:
                            if t2wml_settings.warn_for_empty_cells:
                                self._errors.append((StatementError(field="value",
                                                    message="Empty cell",
                                                    qualifier=i)))
                            continue #either way, discard qualifier
                        
                        discard_qual=False
                        for error in node_qual._errors:
                            if error.field in ["property", "value"]:
                                discard_qual=True
                        if discard_qual:
                            continue  # discard qualifier

                        else:
                            new_qualifiers.append(node_qual)
                    except Exception as e:
                        self._errors.append((StatementError(field="fatal",
                                                    message=str(e),
                                                    qualifier=i)))
            self.qualifier = new_qualifiers
        
        handle_ethiopian_calendar(self, gregorian_nodes)
        if len(gregorian_nodes):
            self.qualifier = self.qualifier+gregorian_nodes

        if self.has_references:
            for i, r in enumerate(self.reference):
                try:
                    self.reference[i] = self.node_class(context=self.context, **r)
                except Exception as e: #problem with reference
                    self._errors.append((StatementError(field="reference",
                                                    message=str(e),
                                                    qualifier=False)))

        #check if statement is discarded from statement collection for major errors
        for error in self._errors:
            if error.level=="Major":
                raise T2WMLExceptions.TemplateDidNotApplyToInput(errors=self._errors)



