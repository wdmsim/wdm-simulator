from typing import List, Any, Optional
from itertools import zip_longest, chain
from copy import deepcopy

from tabulate import tabulate

from wdmsim.models.rx_slice import RxSlice


def interleave(array_of_lists: List[List[Any]]) -> List[Any]:
    """
    If you have a list of lists with the same length, this function will interleave them.
    """
    len_list = len(array_of_lists[0])
    if not all(len(l) == len_list for l in array_of_lists):
        raise ValueError("All lists must have the same length")

    return list(chain(*zip(*array_of_lists)))


class LockStatusTable:
    def __init__(self, rx_slices: List[RxSlice], target_lane_order: Optional[List[int]]):
        self.rx_slices = rx_slices
        self.target_lane_order = target_lane_order

        self.search_data_group = self._record_search_data_group()
        self.lock_code_group = self._record_lock_code_group()

        default_display_order = list(range(len(self.rx_slices)))
        display_order = []
        if target_lane_order:
            for lane_idx, lane in enumerate(target_lane_order):
                display_order.append(target_lane_order.index(lane_idx))

        self.display_order = display_order if display_order else default_display_order

    def _record_search_data_group(self) -> List:
        for rx_slice in self.rx_slices:
            rx_slice.search_lock()

        search_data_group = list(
            zip_longest(
                *[
                    (
                        rx_slice.tuner.search_wavelength.values()
                        if rx_slice.tuner.search_wavelength
                        else [None]
                    )
                    for rx_slice in self.rx_slices
                ]
            )
        )

        for rx_slice in self.rx_slices:
            rx_slice.soft_reset()

        return deepcopy(search_data_group)

    def _record_lock_code_group(self) -> List:
        lock_code_group = [
            rx_slice.tuner.lock_code if rx_slice.tuner.lock_code else None
            for rx_slice in self.rx_slices
        ]
        return deepcopy(lock_code_group)

    @property
    def header_wave(self):
        return [f"R{i}/W" for i in self.display_order]

    @property
    def header_code(self):
        return [f"R{i}/C" for i in self.display_order]

    @property
    def header_lock(self):
        return [f"R{i}/L" for i in self.display_order]

    # @property
    # def display_slice_to_lane(self):
    #     if self.target_lane_order:
    #         return {f"R{i}": f"L{lane}" for i, lane in enumerate(self.target_lane_order)}
    #     else:
    #         return {f"R{i}": f"L{i}" for i in range(len(self.rx_slices))}
    #
    # @property
    # def display_lane_to_slice(self):
    #     return {f"L{i}": f"R{rx_idx}" for i, rx_idx in enumerate(self.display_order)}

    @property
    def _slice_to_lane(self) -> Optional[dict]:
        if self.target_lane_order:
            return {f"{i}": f"{lane}" for i, lane in enumerate(self.target_lane_order)}
        else:
            return None
    
    @property
    def _lane_to_slice(self) -> Optional[dict]:
        if self.target_lane_order:
            return {f"{i}": f"{rx_idx}" for i, rx_idx in enumerate(self.display_order)}
        else:
            return None

    @property
    def display_slice_to_lane(self) -> str:
        # return R{i} -> L{lane} style
        if self._slice_to_lane:
            maprep = [f"R{i} -> L{lane}" for i, lane in self._slice_to_lane.items()]
            return ", ".join(maprep)
        else:
            return "No Specific Target Lane Order"

    @property
    def display_lane_to_slice(self) -> str:
        if self._lane_to_slice:
            maprep = [f"L{i} -> R{rx_idx}" for i, rx_idx in self._lane_to_slice.items()]
            return ", ".join(maprep)
        else:
            return "No Specific Target Lane Order"

    def update_search_result(self):
        self.search_data_group = self._record_search_data_group()

    def update_lock_result(self):
        self.lock_code_group = self._record_lock_code_group()

    def get_search_table(self):
        headers = interleave([self.header_wave, self.header_code])

        rows = []
        for search_data_row in self.search_data_group:
            # Create each row by extracting 'code' from each dict, ignore None
            new_row_wave = []
            new_row_code = []
            for data_idx in self.display_order:
                data = search_data_row[data_idx]
                new_row_wave.append(data["wavelength"] * 1e9 if data else None)
                new_row_code.append(data["code"] if data else None)
            new_row = interleave([new_row_wave, new_row_code])
            rows.append(new_row)

            # for data in search_data_row:
            #     new_row_wave.append(data["wavelength"] * 1e9 if data else None)
            #     new_row_code.append(data["code"] if data else None)
            # new_row = interleave([new_row_wave, new_row_code])
            # rows.append(new_row)

        # Print table
        return tabulate(
            tabular_data=rows,
            headers=headers,
            tablefmt="grid",
            numalign="right",
            stralign="right",
            floatfmt=".2f",
            showindex=True,
            missingval="-",
        )

    def get_lock_table(self):
        headers = interleave([self.header_wave, self.header_code, self.header_lock])

        rows = []
        for search_data_row in self.search_data_group:
            # Create each row by extracting 'code' from each dict, ignore None
            new_row_wave = []
            new_row_code = []
            new_row_lock = []
            # for rx_idx, search_data in enumerate(search_data_row):
            for data_idx in self.display_order:
                search_data = search_data_row[data_idx]
                new_row_wave.append(
                    search_data["wavelength"] * 1e9 if search_data else None
                )
                new_row_code.append(search_data["code"] if search_data else None)
                new_row_lock.append(
                    "L"
                    if search_data
                    and search_data["code"] == self.lock_code_group[data_idx]
                    else None
                )
            new_row = interleave([new_row_wave, new_row_code, new_row_lock])
            rows.append(new_row)

        # Print table
        return tabulate(
            tabular_data=rows,
            headers=headers,
            tablefmt="grid",
            numalign="right",
            stralign="right",
            floatfmt=".2f",
            showindex=True,
            missingval="-",
        )
