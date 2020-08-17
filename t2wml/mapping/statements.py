from collections import defaultdict
import t2wml.utils.t2wml_exceptions as T2WMLExceptions
from t2wml.parsing.t2wml_parsing import iter_on_n_for_code, T2WMLCode
from t2wml.spreadsheets.conversions import to_excel
from t2wml.wikification.utility_functions import get_property_type
from t2wml.utils.utilities import VALID_PROPERTY_TYPES, parse_datetime, translate_precision_to_integer


class Node:
    def __init__(self, property=None, value=None, **kwargs):
        self._errors = defaultdict(str)
        self.property = property
        self.value = value
        self.__dict__.update(kwargs)
        self.validate()

    @property
    def errors(self):
        return dict(self._errors)

    def validate(self):
        try:
            if self.property:
                try:
                    property_type = get_property_type(self.property)
                except Exception as e:
                    self._errors["property"] += "Could not get property type for " + \
                        str(self.property)
                    property_type = "Not found"
            else:
                self._errors["property"] += "Missing property "
                property_type = "Not found"
        except AttributeError:  # we init value, but it might be popped elsewhere, don't assume it exists
            property_type = "Not found"

        try:
            if self.value is not None:
                if property_type == "quantity":
                    try:
                        float(self.value)
                    except:
                        self._errors["value"] += "Quantity type property must have numeric value "

                if property_type == "time":
                    self.validate_datetime()
            else:
                if property_type == "globecoordinate":
                    try:
                        test_coordinate_presence = [
                            self.longitude, self.latitude]
                    except AttributeError:
                        self._errors["value"] += "GlobeCoordinates must specify longitude and latitude or point value "
                else:
                    self._errors["value"] += "Missing value field "
        except AttributeError:  # we init value, but it might be popped elsewhere, don't assume it exists
            pass

        if property_type not in VALID_PROPERTY_TYPES and property_type!="Not found":
            self._errors["property"] += "Unsupported property type: "+property_type

    def validate_datetime(self):
        try:
            datetime_string, parsed_precision = parse_datetime(
                self.value,
                additional_formats=self.__dict__.get("format", []),
                precisions=self.__dict__.get("precision", [])
            )
            self.value = datetime_string
            if parsed_precision:
                self.precision = parsed_precision
        except:
            self._errors["value"] += "Invalid datetime: "+str(self.value)

    def serialize(self):
        return_dict = dict(self.__dict__)
        return_dict.pop("_errors")
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
        try:
            item = self.item
        except AttributeError:
            self._errors["item"] += "Missing item"

        self.node_class.validate(self)

        if self.has_qualifiers:
            qual_errors = {}
            new_qualifiers = []
            for i, q in enumerate(self.qualifier):
                node_qual = self.node_class(context=self.context, **q)
                if len(node_qual._errors):
                    qual_errors[str(i)] = node_qual.errors
                if node_qual._errors["property"] or node_qual._errors["value"]:
                    pass  # discard qualifier
                    # new_qualifiers.append(node_qual) #don't discard qualifier
                else:
                    new_qualifiers.append(node_qual)
            if qual_errors:
                self._errors["qualifier"] = qual_errors
            self.qualifier = new_qualifiers

        if self.has_references:
            for i, r in enumerate(self.references):
                self.reference[i] = self.node_class(context=self.context, **r)

        if len(set(["property", "value", "item"]).intersection(self._errors.keys())):
            raise T2WMLExceptions.TemplateDidNotApplyToInput(
                errors=self._errors)

    def serialize(self):
        return_dict = super().serialize()
        if self.has_qualifiers:
            for i, q in enumerate(return_dict["qualifier"]):
                return_dict["qualifier"][i] = q.serialize()
        if self.has_references:
            for i, q in enumerate(return_dict["reference"]):
                return_dict["qualifier"][i] = q.serialize()
        return return_dict


class NodeForEval(Node):
    def __init__(self, property=None, value=None, context={}, **kwargs):
        self.context = context
        self.cells = {}
        super().__init__(property, value, **kwargs)

    def validate(self):
        keys = list(self.__dict__.keys())
        for key in keys:
            if isinstance(self.__dict__[key], T2WMLCode):
                try:
                    entry_parsed = iter_on_n_for_code(
                        self.__dict__[key], self.context)
                    value = entry_parsed.value
                    if value is None:
                        self._errors[key] += "Failed to resolve"
                        self.__dict__.pop(key)
                        # self.__dict__[key]=self.__dict__[key].unmodified_str
                    elif value=="":
                        self._errors[key] += "Empty cell"
                        self.__dict__.pop(key)
                    else:
                        self.__dict__[key] = value

                    try:
                        cell = to_excel(entry_parsed.col, entry_parsed.row)
                        self.cells[key] = cell
                    except AttributeError:
                        pass

                except Exception as e:
                    self._errors[key] += str(e)
                    self.__dict__.pop(key)
                    # self.__dict__[key]=self.__dict__[key].unmodified_str

        Node.validate(self)

    def serialize(self):
        return_dict = super().serialize()
        return_dict.pop("context")
        return_dict.pop("cells")
        cell = self.cells.get("value")
        if cell:
            return_dict["cell"] = cell
        return return_dict


class EvaluatedStatement(Statement, NodeForEval):
    @property
    def node_class(self):
        return NodeForEval

    def validate(self):
        Statement.validate(self)

    def serialize(self):
        return_dict = super().serialize()
        return_dict.pop("cell", None)

        cell = self.cells.get("item")
        if cell:
            return_dict["cell"] = cell
        return return_dict
