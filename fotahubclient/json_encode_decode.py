from enum import Enum
from json import JSONEncoder, JSONDecoder
import stringcase

def none_to_empty_string_valued_dict(dict):
    return { k: '' if not v else v for k, v in dict.items() }

def to_pascalcase_keyed_dict(dict):
    return { stringcase.pascalcase(k): v for k, v in dict.items() }

def from_pascalcase_keyed_dict(dict, enum_types=[]):
    return { stringcase.snakecase(k): to_enum_literal(v, enum_types) for k, v in dict.items() }

def to_enum_literal(value, enum_types):
    for enum_type in enum_types:
        if value in enum_type.__dict__['_member_names_']:
            return enum_type.__dict__['_member_map_'][value]
    return value

class PascalCaseJSONEncoder(JSONEncoder):

    def default(self, obj):
        if isinstance(obj, Enum):
            return obj.name
        else:
            return to_pascalcase_keyed_dict(none_to_empty_string_valued_dict(obj.__dict__))

class PascalCasedObjectArrayJSONDecoder(JSONDecoder):
    
    def __init__(self, array_type, object_type, enum_types=None):
        super().__init__(object_hook=self.object_hook)
        self.array_type = array_type
        self.object_type = object_type
        self.enum_types = enum_types if enum_types is not None else []

    def object_hook(self, data):
        if len(data) == 1 and isinstance(list(data.values())[0], list):
            return self.array_type(**from_pascalcase_keyed_dict(data))
        else:
            return self.object_type(**from_pascalcase_keyed_dict(data, self.enum_types))