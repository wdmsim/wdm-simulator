from abc import ABC, abstractmethod

from wdmsim.arbiter.arbiter_factory import BaseArbiter
from wdmsim.models.rx_slice import RxSlice
from wdmsim.models.tuner import Tuner


class InstTemplate(ABC):
    _SUCCESS = 0
    _FAILURE = 1

    def __init__(self, arbiter: BaseArbiter):
        self.arbiter = arbiter
        self._stage_iter = self.stage()

        # stopper
        self.done = False

    @abstractmethod
    def stage(self):
        pass

    def run_step(self):
        if self.done is False:
            next(self._stage_iter)

    def run(self):
        while not self.done:
            self.run_step()


class SearchInst(InstTemplate):
    def __init__(self, arbiter: BaseArbiter, slice_idx: int):
        super().__init__(arbiter)

        if slice_idx not in range(self.arbiter.num_slices):
            raise ValueError(f"Invalid target index, {slice_idx}")

        self.slice_idx = slice_idx

        self.tgt_slice: RxSlice = self.arbiter.rx_slices[slice_idx]

    def stage(self):
        self.tgt_slice.search_lock()
        self.arbiter.memory["SEARCH_TABLES"].update(
            {self.slice_idx: self.tgt_slice.tuner.search_table}
        )
        self.done = True
        yield

        # status_code = (
        #     self._SUCCESS
        #     if self.tgt_slice.tuner.search_status == Tuner.SEARCH_DONE
        #     else self._FAILURE
        # )
        # self.done = True
        # yield status_code


class LockInst(InstTemplate):
    def __init__(self, arbiter: BaseArbiter, slice_idx: int, mode: str, select: int):
        super().__init__(arbiter)

        if slice_idx not in range(self.arbiter.num_slices):
            raise ValueError(f"Invalid target index, {slice_idx}")

        self.slice_idx = slice_idx
        self.mode = mode
        self.select = select

        self.tgt_slice: RxSlice = self.arbiter.rx_slices[slice_idx]

    def stage(self):
        self.tgt_slice.search_and_acquire_lock(self.mode, self.select)
        if self.tgt_slice.tuner.lock_status == Tuner.LOCK_DONE:
            self.arbiter.memory["LOCK_TABLE"].update(
                {self.slice_idx: self.tgt_slice.tuner.get_lock_idx()}
            )
        self.done = True
        yield

        # status_code = (
        #     self._SUCCESS
        #     if self.tgt_slice.tuner.lock_status == Tuner.LOCK_DONE
        #     else self._FAILURE
        # )
        # self.done = True
        # yield status_code


class UnlockInst(InstTemplate):
    def __init__(self, arbiter: BaseArbiter, slice_idx: int):
        super().__init__(arbiter)

        if slice_idx not in range(self.arbiter.num_slices):
            raise ValueError(f"Invalid target index, {slice_idx}")

        self.slice_idx = slice_idx

        self.tgt_slice: RxSlice = self.arbiter.rx_slices[slice_idx]

    def stage(self):
        self.tgt_slice.release_lock()
        self.arbiter.memory["LOCK_TABLE"].pop(self.slice_idx)
        self.done = True
        yield

        # yield self._SUCCESS


# class LockThenSearchInst(InstTemplate):
#     def __init__(
#         self,
#         arbiter: BaseArbiter,
#         slice_idx: int,
#         aggr_idx: int,
#         aggr_lock_mode: str,
#         aggr_peak_idx: int,
#     ):
#         super().__init__(arbiter)
#
#         if slice_idx not in self.arbiter.target_lane_order:
#             raise ValueError(f"Invalid target index, {slice_idx}")
#
#         if aggr_idx not in self.arbiter.target_lane_order:
#             raise ValueError(f"Invalid target index, {aggr_idx}")
#
#         self.slice_idx = slice_idx
#         self.aggr_idx = aggr_idx
#         self.aggr_lock_mode = aggr_lock_mode
#         self.aggr_peak_idx = aggr_peak_idx
#
#         self.tgt_slice: RxSlice = self.arbiter.rx_slices[slice_idx]
#         self.aggr_slice: RxSlice = self.arbiter.rx_slices[aggr_idx]
#
#     def stage(self):
#         self.aggr_slice.search_and_acquire_lock(self.aggr_lock_mode, self.aggr_peak_idx)
#         # status_code = (
#         #     self._SUCCESS
#         #     if self.aggr_slice.tuner.lock_status == Tuner.LOCK_DONE
#         #     else self._FAILURE
#         # )
#         # yield status_code
#         yield
#
#         self.tgt_slice.search_lock()
#         self.arbiter.memory["SEARCH_TABLES"].update(
#             {self.slice_idx: self.tgt_slice.tuner.search_table}
#         )
#         # status_code = (
#         #     self._SUCCESS
#         #     if self.tgt_slice.tuner.search_status == Tuner.SEARCH_DONE
#         #     else self._FAILURE
#         # )
#         # yield status_code
#         yield
#
#         self.aggr_slice.release_lock()
#         self.done = True
#         # yield self._SUCCESS
#         yield
