
import configparser
from enum import Enum, auto
from typing import NamedTuple
import numpy as np
from abc import ABC, abstractmethod
import yaml

class ConfigFile(ABC):
    """Abstract class for config file format bookkeeper
    """
    def __init__(self, file: str, section: str):
        self.file = file
        self.section = section

    def load(self):
        raise NotImplementedError


class RunType(Enum):
    """Configuration file types.
    """
    SINGLE = auto()
    SWEEP  = auto()


class SimType(Enum):
    """Device types.
    """
    RING = auto()
    LASER = auto()
    LANEORDER = auto()
