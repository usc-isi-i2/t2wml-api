class T2WMLException(Exception):
    message = "Undefined T2WML exception"

class UnsupportedPropertyType(T2WMLException):
    message = "Unsupported property"


class FileTypeNotSupportedException(T2WMLException):
    message = "This file type is currently not supported"


class InvalidYAMLFileException(T2WMLException):
    message = "YAML file is either empty or not valid"


class ErrorInYAMLFileException(InvalidYAMLFileException):
    message = "Key not found in the YAML specification or value of a key in the YAML specification is not appropriate"


class TemplateDidNotApplyToInput(InvalidYAMLFileException):
    def __init__(self, message="Could not apply", errors={}):
        self.message=message
        self.errors = errors


class ValueOutOfBoundException(T2WMLException):
    message = "Value is outside the permissible limits"


class ItemNotFoundException(T2WMLException):
    message = "Couldn't find item in item table"


class InvalidT2WMLExpressionException(T2WMLException):
    message = "Invalid T2WML expression found"


class ConstraintViolationErrorException(T2WMLException):
    message = "Constraint on a given set of values have been violated"


class FileWithThatNameInProject(T2WMLException):
    message="A file with that name is already present in the project"

class InvalidEntityDefinition(T2WMLException):
    message= "Illegal entity definition"