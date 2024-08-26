""" Usefull enum
"""
from enum import IntEnum


class Arrow(IntEnum):
    """ Euneration for Arrow
    """
    START = 1
    END = 3
    NO_ARROW = 2


class Nature(IntEnum):
    """ Euneration for Arrow
    """
    INTERDICTION = 0
    PERMISSION = 1


class SideOfStreet(IntEnum):
    """ Euneration for Arrow
    """
    RIGHT = 1
    LEFT = -1


class TrafficDir(IntEnum):
    """ Euneration for Arrow
    """
    DIGITALIZATION_DIR = 1
    REVERSE_DIR = -1
    BOTH_DIR = 0
    UNSET = -2

