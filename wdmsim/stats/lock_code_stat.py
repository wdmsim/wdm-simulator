
from typing import Dict, List, Optional

import pprint

from wdmsim.models.rx_slice import RxSlice
from wdmsim.stats.base_stats import WDMDistr, WDMStats

class LockCodeDistr(WDMDistr):
    """
    Helper class for lock code distribution readout
    Example:
    >> lock_code_distr = LockCodeDistr()
    >> lock_code_distr.read(rx_slices)
    >> lock_code_distr['slice']
    {0: 100, 1: 100, 2: 300, 3: 100, 4: 100, 5: 100, 6: 100, 7: 100} # 8-WDM
    >> lock_code_distr['slice'][0]
    128
    >> lock_code_distr['summary']
    {'mean': ..., 'std': ..., 'min': ..., 'max': ...}

    Mainly used in system_under_test lock sequencing
    """
    # SCHEMA = {
    #     'slice': dict,
    #     'summary': dict,
    # }

    def read(self, rx_slices: List[RxSlice]) -> None:
        """
        Read lock code distribution from rx_slices
        """
        # assert rx_slices is not empty
        assert len(rx_slices) > 0

        # assert if all rx_slices are locked
        for rx_slice in rx_slices:
            assert rx_slice.tuner.lock_status == rx_slice.tuner.LOCK_DONE, "All rx_slices must be locked"

        # get lock code distribution
        code_slice_raw = {}
        for idx, rx_slice in enumerate(rx_slices):
            code_slice_raw[idx] = rx_slice.tuner.get_lock_voltage_code()

        # get lock code distribution summary
        code_summary_raw = {}
        code_summary_raw['mean'] = sum(code_slice_raw.values()) / len(code_slice_raw)
        code_summary_raw['std'] = (sum((x - code_summary_raw['mean']) ** 2 for x in code_slice_raw.values()) / len(code_slice_raw)) ** 0.5
        code_summary_raw['min'] = min(code_slice_raw.values())
        code_summary_raw['max'] = max(code_slice_raw.values())

        # update info
        self.info['slice'] = code_slice_raw
        self.info['summary'] = code_summary_raw


class LockCodeStat(WDMStats):
    """
    Helper class for lock code statistics readout
    It is initialized as an empty class i.e., no lock code distribution is stored by
    `lock_code_stat = LockCodeStat()` and lock code distribution can be added by
    `lock_code_stat += lock_code_distr`. Then the class info dict `lock_code_stat['slice']` 
    will be appended with the new lock code distribution as well as the summary 
    `lock_code_stat['summary']`.

    Mainly used at simulator do_statistics() to collect lock code distribution
    """
    _DATA_SCHEMA = LockCodeDistr

    @property
    def max(self) -> Optional[float]:
        # TODO: finish
        # self.info['summary'].get('max', [])
        pass

    @property
    def avg(self) -> Optional[float]:
        # TODO: finish
        pass

    # SCHEMA = {
    #     'slice': dict,
    #     'summary': dict,
    # }

    # def __iadd__(self, lock_code_distr: LockCodeDistr) -> 'LockCodeStat':
    #     """
    #     Overload += operator to append lock code distribution
    #     """
    #     # Validate if lock_code_distr is of correct type
    #     if not isinstance(lock_code_distr, LockCodeDistr):
    #         raise TypeError(f"lock_code_distr {lock_code_distr} is not of type {LockCodeDistr}")
    #
    #     # update info
    #     # each lock_code_dist['slice'] is a dict of the form {0: 100, 1: 200, ...}
    #     # each lock_code_dist['summary'] is a dict of the form {'mean': 100, 'std': 10, ...}
    #     # lock_code_stat['slice'] is a dict of the form {0: [100, 200, ...], 1: [200, 300, ...], ...}
    #     # lock_code_stat['summary'] is a dict of the form {'mean': [100, 200, ...], 'std': [10, 20, ...], ...}
    #     for label in self.labels:
    #         for key, value in lock_code_distr[label].items():
    #             self.info[label].setdefault(key, []).append(value)
    #
    #     return self


