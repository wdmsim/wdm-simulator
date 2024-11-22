

from typing import Any, Dict, List, Optional

from wdmsim.models.rx_slice import RxSlice
from wdmsim.stats.base_stats import WDMDistr, WDMStats

class RelationDistr(WDMDistr):
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

    def _collect_wavelength(self, search_datastruct: Dict[int, Any]) -> List[float]:
        """
        Collect wavelength from search_datastruct
        """
        return [search_tgt['wavelength'] for search_tgt in search_datastruct.values()]


    def read(self, rx_slices: List[RxSlice]) -> None:
        """
        Read lock code distribution from rx_slices
        """
        # assert rx_slices is not empty
        assert len(rx_slices) > 0

        # assert if all rx_slices have search data
        for rx_slice in rx_slices:
            assert rx_slice.tuner.search_status == rx_slice.tuner.SEARCH_DONE, "All rx_slices must have search data"

        # Relation should comprise any permutation of rx_slices
        # However, for the purpose of statistics, extracting N-consecutive relations would work
        # especially from the perspective of WDM wavelength search
        # 'slice' implies the relation btw rx_slices[i] and rx_slices[i+1]
        slice_wavelengths = {}
        for idx, rx_slice in enumerate(rx_slices):
            search_datastruct = rx_slice.tuner.search_wavelength
            slice_wavelengths[idx] = self._collect_wavelength(search_datastruct)

        slice_overlaps = {}
        for idx, rx_slice in enumerate(rx_slices):
            curr_wavelengths = slice_wavelengths[idx]
            nxt_wavelengths = slice_wavelengths[(idx + 1) % len(rx_slices)]
            slice_overlaps[idx] = len(set(curr_wavelengths) & set(nxt_wavelengths))

        self.info['slice'] = {'wavelengths': slice_wavelengths, 'overlaps': slice_overlaps}

        self.info['summary'] = {
            'min': min(slice_overlaps.values()),
            'max': max(slice_overlaps.values()),
        }

        # # get lock code distribution
        # code_slice_raw = {}
        # for idx, rx_slice in enumerate(rx_slices):
        #     code_slice_raw[idx] = rx_slice.tuner.get_lock_voltage_code()
        #
        # # get lock code distribution summary
        # code_summary_raw = {}
        # code_summary_raw['mean'] = sum(code_slice_raw.values()) / len(code_slice_raw)
        # code_summary_raw['std'] = (sum((x - code_summary_raw['mean']) ** 2 for x in code_slice_raw.values()) / len(code_slice_raw)) ** 0.5
        # code_summary_raw['min'] = min(code_slice_raw.values())
        # code_summary_raw['max'] = max(code_slice_raw.values())
        #
        # # update info
        # self.info['slice'] = code_slice_raw
        # self.info['summary'] = code_summary_raw


class RelationStats(WDMStats):
    """
    Helper class for lock code statistics readout
    It is initialized as an empty class i.e., no lock code distribution is stored by
    `lock_code_stat = LockCodeStat()` and lock code distribution can be added by
    `lock_code_stat += lock_code_distr`. Then the class info dict `lock_code_stat['slice']` 
    will be appended with the new lock code distribution as well as the summary 
    `lock_code_stat['summary']`.

    Mainly used at simulator do_statistics() to collect lock code distribution
    """
    _DATA_SCHEMA = RelationDistr

    # @property
    # def max(self) -> Optional[float]:
    #     # TODO: finish
    #     # self.info['summary'].get('max', [])
    #     pass
    #
    # @property
    # def avg(self) -> Optional[float]:
    #     # TODO: finish
    #     pass


