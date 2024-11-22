from typing import Dict, List
import pprint
from abc import ABC, abstractmethod


class BaseStats(ABC):
    def __init__(self):
        # initialize info data structure by schema
        self.info = {}
        for label, value_type in self.SCHEMA.items():
            self.info[label] = value_type()

    @property
    @abstractmethod
    def SCHEMA(self):
        pass

    @property
    def labels(self) -> List[str]:
        """
        Get all labels
        """
        return [x for x in self.SCHEMA]

    def __str__(self) -> str:
        return pprint.pformat(self.info)

    def __getitem__(self, label: str) -> Dict:
        """
        Wrapper for fetch for [] notation
        WARNING: Fetched data can change since it inherits the vulnerable pass by reference issue of mutable dict type
        """
        # Validate if label is in schema
        if label not in self.SCHEMA:
            raise KeyError(f"Label {label} not in schema")

        return self.info[label]

    def __setitem__(self, label: str, data: Dict) -> None:
        """
        Wrapper for update for [] notation
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

        self.info[label] = data

    def __len__(self) -> int:
        """
        Get number of lock code distributions
        """
        return len(self.info['slice']) + len(self.info['summary'])


WDM_STATS_SCHEMA = {
    'slice': dict,
    'summary': dict,
}

class WDMDistr(BaseStats, ABC):
    SCHEMA = WDM_STATS_SCHEMA

    @abstractmethod
    def read(self) -> None:
        raise NotImplementedError


class WDMStats(BaseStats, ABC):
    SCHEMA = WDM_STATS_SCHEMA

    @property
    @abstractmethod
    def _DATA_SCHEMA(self):
        """Data collection base class
        e.g., LockCodeStats -> LockCodeDistr and RelationStats -> RelationDistr
        """
        raise NotImplementedError

    def __iadd__(self, wdm_data_distr: WDMDistr) -> 'WDMStats':
        """
        Overload += operator to append lock code distribution
        """
        # # Validate if lock_code_distr is of correct type
        # if not isinstance(wdm_data_distr, WDMDistr):
        #     raise TypeError(f"lock_code_distr {wdm_data_distr} is not of type {WDMDistr}")

        if not isinstance(wdm_data_distr, self._DATA_SCHEMA):
            raise TypeError(f"lock_code_distr {wdm_data_distr} is not of type {self._DATA_SCHEMA}")

        # update info
        # each lock_code_dist['slice'] is a dict of the form {0: 100, 1: 200, ...}
        # each lock_code_dist['summary'] is a dict of the form {'mean': 100, 'std': 10, ...}
        # lock_code_stat['slice'] is a dict of the form {0: [100, 200, ...], 1: [200, 300, ...], ...}
        # lock_code_stat['summary'] is a dict of the form {'mean': [100, 200, ...], 'std': [10, 20, ...], ...}
        for label in self.labels:
            for key, value in wdm_data_distr[label].items():
                self.info[label].setdefault(key, []).append(value)

        return self



