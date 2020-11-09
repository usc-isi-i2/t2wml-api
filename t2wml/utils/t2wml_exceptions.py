class T2WMLException(Exception):
    message = "Undefined T2WML exception"
    def __init__(self, detail_message="", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.detail_message=detail_message
    def __str__(self):
        return self.message + ":" + self.detail_message

class FileWithThatNameInProject(T2WMLException):
    message="A file with that name is already present in the project"

class FileTypeNotSupportedException(T2WMLException):
    message = "This file type is currently not supported"


class UnsupportedPropertyType(T2WMLException):
    message = "Unsupported property"

class InvalidEntityDefinition(T2WMLException):
    message= "Illegal entity definition"

class InvalidYAMLFileException(T2WMLException):
    message = "YAML file is either empty or not valid such that it cannot be loaded/parsed"

class ErrorInYAMLFileException(T2WMLException):
    message = "Valid by yaml standards, the file is nonetheless missing required keys or otherwise does not match t2wml-yaml specifications"

class RegionConstraintViolationErrorException(ErrorInYAMLFileException):
    message = "Region constraints self-contradict or are impossible"

class ErrorWhileApplyingYamlFileException(ErrorInYAMLFileException):
    message = "Errors occured while applying the t2wml-valid yaml file, possibly cell-specific"

class TemplateDidNotApplyToInput(ErrorWhileApplyingYamlFileException):
    def __init__(self, errors={}):
        self.errors = errors

class CellOutsideofBoundsException(T2WMLException):
    message = "Attempted to access cell outside of spreadsheet bounds"

class ItemNotFoundException(T2WMLException):
    message = "Couldn't find item in item table"

class ModifyingItemsIsForbiddenException(T2WMLException):
    message = "Cannot modify items from a function"





