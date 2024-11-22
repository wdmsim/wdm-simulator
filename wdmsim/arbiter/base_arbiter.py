from abc import ABC, abstractmethod
from typing import List, Union, Optional, Dict

from wdmsim.models.rx_slice import RxSlice
from wdmsim.models.tuner import Tuner
from wdmsim.arbiter.arbiter_memory import BaseArbiterMemory


class BaseArbiter(ABC):
    _registry = {}

    def __init__(
        self, rx_slices: List[RxSlice], target_lane_order: Optional[List[int]],
    ):
        self.rx_slices = rx_slices
        self.target_lane_order = target_lane_order
        # self.target_lane_order = (
        #     target_lane_order
        #     if target_lane_order is not None
        #     else list(range(len(rx_slices)))
        # )

        self.num_slices = len(rx_slices)

        self._step_algorithm = self.algorithm()
        self._memory = BaseArbiterMemory()

        self.end_state = False
        self.lock_error_state = False

    @property
    def memory(self) -> BaseArbiterMemory:
        return self._memory

    def hard_reset(self):
        self.end_state = False
        self.lock_error_state = False

        # reset the algorithm stepper
        self._step_algorithm = self.algorithm()

        # reset the memory
        self.memory.reset()

    def soft_reset(self):
        self.end_state = False
        self.lock_error_state = False

        # TODO: performance implication?
        # reset the algorithm stepper
        self._step_algorithm = self.algorithm()

        # reset the memory
        self.memory.reset()

    @abstractmethod
    def algorithm(self):
        raise NotImplementedError

    def tick(self):
        try:
            if not self.end_state and not self.lock_error_state:
                next(self._step_algorithm)
                return True
            else:
                return False
        except StopIteration:
            raise StopIteration("The arbiter has reached the end state")

    def is_end_state(self):
        return self.end_state

    def is_lock_error_state(self):
        return self.lock_error_state

    def check_zero_lock(
        self, slice_idx: Optional[Union[int, List[int]]] = None
    ) -> bool:
        """Check lock status
        Returns True if there is a zero lock case

        :param idx: The index of the RxSlice to check
                    If None, check all RxSlices, otherwise check the specified RxSlice
        :rtype idx: Optional[Union[int, List[int]]]
        :return: True if there is a zero lock case
        """
        # Parse the index
        if slice_idx is None:
            rx_slices = self.rx_slices
        elif isinstance(slice_idx, int):
            rx_slices = [self.rx_slices[slice_idx]]
        elif isinstance(slice_idx, list):
            rx_slices = [self.rx_slices[i] for i in slice_idx]

        # Check if there is a zero lock case
        for rx_slice in rx_slices:
            if rx_slice.tuner.lock_status in [
                Tuner.LOCK_NO_WAVE,
                Tuner.LOCK_NOT_IN_RANGE,
            ]:
                return True
        return False

    def check_lock_done(
        self, slice_idx: Optional[Union[int, List[int]]] = None
    ) -> bool:
        """Check lock status
        Returns True if there is a zero lock case

        :param idx: The index of the RxSlice to check
                    If None, check all RxSlices, otherwise check the specified RxSlice
        :rtype idx: Optional[Union[int, List[int]]]
        :return: True if there is a zero lock case
        """
        # Parse the index
        if slice_idx is None:
            rx_slices = self.rx_slices
        elif isinstance(slice_idx, int):
            rx_slices = [self.rx_slices[slice_idx]]
        elif isinstance(slice_idx, list):
            rx_slices = [self.rx_slices[i] for i in slice_idx]

        # Check if there is a zero lock case
        for rx_slice in rx_slices:
            if rx_slice.tuner.lock_status in [Tuner.LOCK_DONE]:
                return True
        return False
