

from enum import Enum


class Command(str, Enum):
    SET = "SET"
    GET = "GET"
    DELETE = "DELETE"
    EXISTS = "EXISTS"
    INCR = "INCR"
    EXPIRE = "EXPIRE"
    