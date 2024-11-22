from abc import ABC, abstractmethod
from typing import Dict, List, Mapping, Optional, TypeVar, Union
from copy import deepcopy
import pprint
from typing_extensions import TypedDict

from wdmsim.utils.update_dict import update_dict

MEM_DATA_TYPE = Dict[int, Union[int, float]]


class ArbiterMemoryTemplate(ABC):
    """
    Base class for arbiter memory
    """

    def __init__(self):
        self.__entry = {}
        for label, value_type in self.SCHEMA.items():
            self.__entry[label] = value_type()

    @property
    @abstractmethod
    def SCHEMA(self) -> Mapping[str, type]:
        return NotImplementedError

    @property
    def entry(self) -> Dict[str, MEM_DATA_TYPE]:
        return self.__entry

    @entry.setter
    def entry(self, value) -> None:
        self.__entry = value

    @property
    def labels(self) -> List[str]:
        """
        Get all labels
        """
        return [x for x in self.SCHEMA]

    def __str__(self) -> str:
        return pprint.pformat(self.entry)

    def __getitem__(self, label: str) -> MEM_DATA_TYPE:
        """
        Wrapper for fetch for [] notation
        WARNING: Fetched data can change since it inherits the vulnerable pass by reference issue of mutable dict type
        """
        return self.fetch(label)

    # def __setitem__(self, label: str, data: MEM_DATA_TYPE) -> None:
    #     """
    #     Wrapper for update for [] notation
    #     WARNING: Fetched data can change since it inherits the vulnerable pass by reference issue of mutable dict type
    #
    #     :param label: Label to update
    #     :param data: Data to update
    #     """
    #     self.update(label, data)

    def update(self, label: str, data: MEM_DATA_TYPE) -> None:
        """
        Upload data to memory
        WARNING: Fetched data can change since it inherits the vulnerable pass by reference issue of mutable dict type

        :param label: Label to update
        :param data: Data to update
        """
        # Validate if label is in schema
        if label not in self.SCHEMA:
            raise KeyError(f"Label {label} not in schema")

        # Validate if data is of correct type
        if not isinstance(data, self.SCHEMA[label]):
            raise TypeError(f"Data {data} is not of type {self.SCHEMA[label]}")

        update_dict(self.__entry, {label: data})

    def fetch(self, label: str) -> MEM_DATA_TYPE:
        """
        Fetch data from memory
        WARNING: Fetched data can change since it inherits the vulnerable pass by reference issue of mutable dict type
        """
        # Validate if label is in schema
        if label not in self.SCHEMA:
            raise KeyError(f"Label {label} not in schema")

        return self.__entry[label]

    def copy(self, label: str, index: Optional[int] = None) -> MEM_DATA_TYPE:
        """
        Copy data from memory
        """
        # Validate if label is in schema
        if label not in self.SCHEMA:
            raise KeyError(f"Label {label} not in schema")

        data = self.entry[label]
        if index is None:
            # Copy all
            return deepcopy(data)
        else:
            # Copy single item
            if isinstance(data, dict):
                if index not in data:
                    raise KeyError(f"Index {index} not in {label}")
                return deepcopy(data[index])
            elif isinstance(data, list):
                if index >= len(data):
                    raise IndexError(f"Index {index} out of range for {label}")
                return deepcopy(data[index])
            else:
                raise NotImplementedError(f"Data {data} is not of type dict or list")
            # Copying multiple items from index list is not supported
            # since it would force the function to return a dictionary which is not consistent with the return type

    def flush(self, label: str) -> None:
        """
        Flush memory
        """
        # Validate if label is in schema
        if label not in self.SCHEMA:
            raise KeyError(f"Label {label} not in schema")

        self.__entry[label] = self.SCHEMA[label]()

    def reset(self) -> None:
        """
        Reset memory
        """
        for label in self.labels:
            self.__entry[label] = self.SCHEMA[label]()

    # def print(self) -> None:
    #     """
    #     Pretty print memory
    #     """
    #     pprint(self.__entry)


class BaseArbiterMemory(ArbiterMemoryTemplate):
    """
    Default memory for arbiter
    """

    SCHEMA = {
        "SEARCH_TABLES": dict,
        "RELATION_INDEX_TABLE": dict,
        "LOCK_TABLE": dict,
        "SCRATCHPAD": set,
    }
