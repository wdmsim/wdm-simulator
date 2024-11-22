
import logging
from typing import List, Optional, Type, Dict, Union

from copy import deepcopy, copy
import numpy as np
from art import text2art

from wdmsim.models.optical_port import OpticalPort
from wdmsim.models.laser_grid import LaserGrid
from wdmsim.models.rx_slice import RxSlice
from wdmsim.models.ring_row import RingRxWDM, RingRxWDMRow
from wdmsim.models.tuner import Tuner
from wdmsim.models.sim_instance import SimInstance
# from wdmsim.arbiters.base_arbiter import BaseArbiter
from wdmsim.arbiter.base_arbiter import BaseArbiter

from wdmsim.models.sysclk import execute_at_init, reset_sysclk
from wdmsim.utils.pretty_print import format_wavelengths
from wdmsim.utils.snapshot import Snapshot
from wdmsim.utils.lock_status_table import LockStatusTable
from wdmsim.stats.lock_code_stat import LockCodeDistr
from wdmsim.stats.relation_stat import RelationDistr
from wdmsim.exceptions import DuplicateLockException
from wdmsim.utils.logger import _VERBOSE

logger = logging.getLogger(__name__)


class SystemUnderTest(SimInstance):
    """System Under Test class

    Abstract behavioral model of Rx macro (SUT) consists of Rx slices (ring+tuner) and arbiter
    Serves as a main dut in testbench and is responsible for:
    - System initialization
    - System build
    - System reset
    - System experiment

    Attributes:
        rx_slices: group of Rx slices
        arbiter: Arbiter object
        ring_wdm_row: WDM ring row from Rx slices
    """
    # Class variables for SUT experiment exit conditions
    EXIT_SUCCESS = 0
    EXIT_ZERO_LOCK = 1
    EXIT_DUPLICATE_LOCK = 2
    EXIT_WRONG_LANE_ORDER = 3

    def __init__(self, rx_slices: List[RxSlice], arbiter: BaseArbiter) -> None:
        """Default constructor
        :param rx_slices: group of Rx slices
        :param arbiter: Arbiter object
        """
        # Initialize Rx slices and arbiter
        self.rx_slices = rx_slices
        self.arbiter = arbiter

        # Initialize system snapshot for visualization
        self.snapshots = []

        # Initialize lock code distribution dump for visualization
        # TODO: refactor - remove this for performance?
        self.lock_code_distr = LockCodeDistr()
        self.relation_distr = RelationDistr()
    
        # Initialize system clock
        self._sysclk = 0

        # System hard reset at boot up
        self.hard_reset()

    def __str__(self) -> str:
        """String representation of the System Under Test"""
        return f"System Under Test: {self.rx_slices} {self.arbiter}"

    def __repr__(self) -> str:
        """String representation of the System Under Test"""
        return self.__str__()

    @property
    def ring_wdm_row(self) -> RingRxWDMRow:
        """Get ring WDM row"""
        return RingRxWDMRow(rings=[rx_slice.ring for rx_slice in self.rx_slices])

    @property
    def ports(self) -> OpticalPort:
        return self.ring_wdm_row.ports

    # # TODO: remove this?
    # @classmethod
    # def build_from_laser_grid(cls,
    #                           ring_row_params: List[dict],
    #                           arbiter_cls: Type[BaseArbiter],
    #                           laser_grid: LaserGrid
    #                           ) -> 'SystemUnderTest':
    #     """ Build System Under Test from ring parameters locked onto the given laser grid
    #
    #     :param ring_params: list of ring parameters [{'fsr': fsr, 'tuning_range': tuning_range}, ...]
    #     :param arbiter_cls: Arbiter class
    #     :param laser_grid: LaserGrid object that ring is initially locked on
    #     :return: SystemUnderTest object
    #     """
    #     # Create Rx slices
    #     rx_slices = [RxSlice(RingRxWDM(wavelength, **ring_params), Tuner())
    #                  for wavelength, ring_params
    #                  in zip(laser_grid.wavelengths, ring_row_params)]
    #
    #     # Instantiate arbiter from arbiter class
    #     arbiter = arbiter_cls(rx_slices)
    #
    #     return cls(rx_slices=rx_slices, arbiter=arbiter)

    @classmethod
    def construct_slices_and_arbiter(
        cls, 
        ring_row_params: List[dict], 
        ring_wavelengths: List[float],
        init_lane_order: Optional[List[int]],
        arbiter_cls: Type[BaseArbiter],
        tgt_lane_order: Optional[List[int]],
    ) -> 'SystemUnderTest':
        """ Build System Under Test by constructing Rx slices and arbiter from ring parameters and wavelengths

        Note the two exceptions for the lane order parameters:
        : `init_lane_order`
        - At replay mode, the recorded lane order (implicit in ring wavelengths recorded) is used as-is
        : `tgt_lane_order`
        - At lock-to-any mode, the lane order is not specified (None) and the system should lock to any lane order

        :param ring_params: list of ring parameters [{'fsr': fsr, 'tuning_range': tuning_range}, ...]
        :param ring_wavelengths: list of ring wavelengths
        :param init_lane_order: initial lane order
        :param arbiter_cls: Arbiter class
        :param laser_grid: LaserGrid object that ring is initially locked on
        :return: SystemUnderTest object
        """
        # Set the initial lane order by reordering the ring wavelengths
        # At replay mode when init_lane_order is not supplied, this step is skipped (ring wavelengths are used as is)
        # because the lane order is already recorded as the ordering within ring wavelengths in the snapshot
        # Otherwise, reorder the generated ring wavelengths according to the init_lane_order
        if init_lane_order is not None:
            ring_wavelengths_reordered = [ring_wavelengths[i] for i in init_lane_order]
        else:
            ring_wavelengths_reordered = ring_wavelengths

        # Reordering ring_row_params is skipped because
        # 1. it should be skipped at replay mode
        # 2. currently ring row params don't have a specific physical/logical ordering embedded
        # TODO: you should change this when you add a specific ordering in ring row params

        # Create Rx slices
        rx_slices = [RxSlice(RingRxWDM(wavelength, **ring_params), Tuner()) 
                     for wavelength, ring_params 
                     in zip(ring_wavelengths_reordered, ring_row_params)]

        # Instantiate arbiter from arbiter class and set target lane order
        arbiter = arbiter_cls(rx_slices, tgt_lane_order)

        return cls(rx_slices=rx_slices, arbiter=arbiter)

    def hard_reset(self) -> None:
        """Hard reset all Rx slices and arbiter
        It is performed at the boot up of the system
        """
        # Reset all Rx slices and arbiter
        for rx_slice in self.rx_slices:
            rx_slice.hard_reset()
        self.arbiter.hard_reset()

        # Reset system snapshot
        self.snapshots = []

        # Reset system clock
        self.rst_sysclk()

    def soft_reset(self) -> None:
        """Soft reset all Rx slices and arbiter
        It is performed at laser hot swappings to reset RTL states and keeping the history register
        """
        # Reset all Rx slices and arbiter
        for rx_slice in self.rx_slices:
            rx_slice.soft_reset()
        self.arbiter.soft_reset()

        # Reset system snapshot
        self.snapshots = []

        # Reset system clock
        self.rst_sysclk()

    def hotplug_laser_grid(self, laser_grid: LaserGrid) -> None:
        """Plug in new laser grid to the system

        It is the main function that initializes the hotswap experiment before running the experiment
        It first makes a logical connection between the laser grid and the system
        Then it performs the laser turn on and pass the wavelengths to the rings
        :param laser_grid: LaserGrid object
        """
        # # print laser grid
        # logger.info(f"\nlaser grid {laser_grid.laser_id}: {format_wavelengths(laser_grid.ports['out'].wave.wavelengths)}")

        # Plug in laser
        self.ring_wdm_row.connect_laser_grid(laser_grid)

        # Turn on laser
        laser_grid.initialize_wave()

        # Rings downstream from the first ring will be initialized by the wavefront
        self.ring_wdm_row.passthrough_wave()
    
        # # check by printing the wavefronts at the ring inputs
        # logger.info(f"first ring input: {self.ring_wdm_row.rings[0].ports['in'].wave.wavelengths}")
        # logger.info(f"first ring thru : {self.ring_wdm_row.rings[0].ports['thru'].wave.wavelengths}")
        # logger.info(f"second ring input: {self.ring_wdm_row.rings[1].ports['in'].wave.wavelengths}")
        # logger.info(f"last ring input: {self.ring_wdm_row.rings[-1].ports['in'].wave.wavelengths}")

    def tick(self) -> None:
        """Run one tick of the system

        It is the main function that runs the system under test, and implementing a single tick
        of the system consists of the following steps:
        - Run one tick of arbiter
        - Propagate the wavefront through the rings
        This is to modulate the tuners and rings first then propagate the wavefront
        """
        # Tick one cycle at the arbiter
        self.arbiter.tick()

        # Update optical signals by propagating wavefronts through the rings downstream
        self.ring_wdm_row.propagate_wave()

        # log the current tuner state and the arbiter state
        if logger.isEnabledFor(_VERBOSE):
            logger.debug(f"tuner lock status: {[rx_slice.tuner.lock_status for rx_slice in self.rx_slices]}")
            logger.debug(f"tuner lock data: {[rx_slice.tuner.lock_data for rx_slice in self.rx_slices]}")
            tuner_wvl = [rx_slice.tuner.lock_wavelength for rx_slice in self.rx_slices]
            logger.debug(f"tuner wvl: {format_wavelengths(tuner_wvl)}")
            logger.debug(f"arbiter state: {self.arbiter.state}")

        # Update system clock
        self.sysclk += 1

    def run_lock_sequence(self, 
                          laser_grid: LaserGrid, 
                          plot_snapshot: bool = False, 
                          plot_statistics: bool = False) -> int:
        """Lock the system to the given laser grid

        Main run function of system under test, lock to the new laser grid and
        check if the system is locked

        :param laser_grid: LaserGrid object
        :param debug: debug flag 
        :return: exit status, 0 for success, 1 for duplicate lock, 2 for zero lock
        :rtype: int
        """
        # soft-reset the system
        self.soft_reset()

        # Plug in laser grid
        self.hotplug_laser_grid(laser_grid)

        # If plot snapshot is enabled, plot the initial snapshot, otherwise skip
        if plot_snapshot:
            self.snapshots += [Snapshot(self.sysclk, self.ring_wdm_row, self.arbiter, laser_grid)]
        else:
            self.snapshots = []

        # # Wait until arbiter reaches the end state (and record snapshots if debug flag is set)
        # while not self.arbiter.is_end_state():
        #     self.tick()
        #     if plot_snapshot:
        #         self.snapshots += [Snapshot(self.sysclk, self.ring_wdm_row, self.arbiter, laser_grid)]

        if logger.isEnabledFor(_VERBOSE):
            lock_status = LockStatusTable(self.rx_slices, self.arbiter.target_lane_order)
            logger.info(f"Target Ring->Laser ordering\n{lock_status.display_slice_to_lane}")
            logger.info(f"Target Laser->Ring ordering\n{lock_status.display_lane_to_slice}")
            logger.info(f"Search Table\n{lock_status.get_lock_table()}")

        while self.arbiter.tick():
            # logger.info("tick")
            # Update optical signals by propagating wavefronts through the rings downstream
            self.ring_wdm_row.propagate_wave()

            if plot_snapshot:
                self.snapshots += [Snapshot(self.sysclk, self.ring_wdm_row, self.arbiter, laser_grid)]

        if logger.isEnabledFor(_VERBOSE):
            lock_status.update_lock_result()
            logger.info(f"Target Ring->Laser ordering\n{lock_status.display_slice_to_lane}")
            logger.info(f"Target Laser->Ring ordering\n{lock_status.display_lane_to_slice}")
            logger.info(f"Lock Allocation Table\n{lock_status.get_lock_table()}")

        # Check if the system has duplicate lock
        if self.is_duplicate_lock():
            if logger.isEnabledFor(_VERBOSE):
                logger.info(f"Duplicate Lock Case: {laser_grid.laser_id}, return with status code 2\n")
                logger.info(f'Arbiter: {self.arbiter.__class__.__name__}')
                logger.info(f"\n{text2art('LOCK FAIL')}")
            return self.EXIT_DUPLICATE_LOCK

        # Check if the arbiter has detected a zero lock case
        if self.arbiter.is_lock_error_state():
            if logger.isEnabledFor(_VERBOSE):
                logger.info(f"Zero Lock Case: {laser_grid.laser_id}, return with status code 1\n")
                logger.info(f'Arbiter: {self.arbiter.__class__.__name__}')
                logger.info(f"\n{text2art('LOCK FAIL')}")
            return self.EXIT_ZERO_LOCK

        if self.arbiter.target_lane_order is not None:
            if not self.is_correct_lane_order():
                if logger.isEnabledFor(_VERBOSE):
                    logger.info(f"Wrong Lane Order: {laser_grid.laser_id}, return with status code 3\n")
                    logger.info(f'Arbiter: {self.arbiter.__class__.__name__}')
                    logger.info(f"\n{text2art('LOCK FAIL')}")
                return self.EXIT_WRONG_LANE_ORDER

        # system lock success
        # if plot statistics is enabled, read statistics from slices
        if plot_statistics:
            self.lock_code_distr.read(self.rx_slices)
            self.relation_distr.read(self.rx_slices)

        # return 0 when lock is successful
        if logger.isEnabledFor(_VERBOSE):
            logger.info(f"System is locked: {laser_grid.laser_id}, return with status code 0\n")
            logger.info(f'Arbiter: {self.arbiter.__class__.__name__}')
            logger.info(f"\n{text2art('LOCK SUCCESS')}")
        return self.EXIT_SUCCESS

    def is_duplicate_lock(self) -> bool:
        """Check if the system is has duplicate lock

        Since arbiter hardware cannot detect duplicate lock, it does not check the arbiter lock status
        Instead it checks the lock wavelength of all tuners to see if there is any duplicate wavelength

        :return: True if there is duplicate lock, False otherwise
        """
        # TODO: find a better way? floating number comparisons are vulnerable to precision errors
        # collect lock wavelength parameter from all Rx slices tuners and check
        lock_wavelengths = [rx_slice.tuner.lock_wavelength for rx_slice in self.rx_slices]
        if logger.isEnabledFor(_VERBOSE):
            logger.info(f"lock_wavelengths: {format_wavelengths(lock_wavelengths)}")
        return len(set(lock_wavelengths)) < len(lock_wavelengths)

    def is_correct_lane_order(self) -> bool:
        """Check if the system has correct lane order up to cyclic permutation
        """
        # TODO: document
        wavelength_with_index = [(rx_slice.tuner.lock_wavelength, index) for index, rx_slice in enumerate(self.rx_slices)]
        sorted_by_wavelength = sorted(wavelength_with_index, key=lambda x: x[0])
        # current_lane_order = [item[1] for item in sorted_by_wavelength]

        current_lane_order = []
        for item in wavelength_with_index:
            lane_idx = sorted_by_wavelength.index(item)
            current_lane_order.append(lane_idx)
        
        orig_target_lane_order = self.arbiter.target_lane_order
        for i in range(len(orig_target_lane_order)):
            # rotated = self.arbiter.target_lane_order[i:] + self.arbiter.target_lane_order[:i]  # Rotate the correct order

            # vertical rotation matters
            # i.e., [0, 3, 1, 2] == [1, 0, 2, 3] == [2, 1, 3, 0] == [3, 2, 0, 1]
            rotated = [(lane_order + i) % len(orig_target_lane_order) for lane_order in orig_target_lane_order]
            if rotated == current_lane_order:
                return True  # Found a matching cyclic permutation
        
        return False  # No matching cyclic permutation found
    
        # if self.arbiter.target_lane_order is not None:
        #     wavelength_with_index = [(rx_slice.tuner.lock_wavelength, index) for index, rx_slice in enumerate(self.rx_slices)]
        #     sorted_by_wavelength = sorted(wavelength_with_index, key=lambda x: x[0])
        #     current_lane_order = [item[1] for item in sorted_by_wavelength]
        #
        #     for i in range(len(self.arbiter.target_lane_order)):
        #         rotated = self.arbiter.target_lane_order[i:] + self.arbiter.target_lane_order[:i]  # Rotate the correct order
        #         if rotated == current_lane_order:
        #             return True  # Found a matching cyclic permutation
        #
        #     return False  # No matching cyclic permutation found
        #
        # else:
        #     # lock-to-any case: always return True
        #     return True
    

    # def get_lock_statistics(self) -> Dict[Union[int, str], Union[int, float]]:

    #     """Get lock code statistics of the system
    #
    #     Retrieve the lock code statistics of the system after running the system lock sequence
    #
    #     :return: lock code dictionary
    #     """
    #     lock_codes = {}
    #     # retrieve lock code from each tuner
    #     for idx, rx_slice in enumerate(self.rx_slices):
    #         lock_codes[idx] = rx_slice.tuner.lock_code
    #     # calculate mean and std of lock codes and append
    #     lock_codes['mean'] = np.mean(list(lock_codes.values()))
    #     lock_codes['std'] = np.std(list(lock_codes.values()))
    #
    #     return lock_codes
    
    # def is_locked(self) -> bool:
    #     """Check if the system is locked"""
    #     # TODO: lock status is not a good indicator, need to check the lock data
    #     # If the duplicate lock happens and arbiter exits, still the tuner lock status is True without reflecting the double lock
    #     # # for speed reason, poll directly to the tuners
    #     # #return all(rx_slice.is_locked() for rx_slice in self.rx_slices)
    #     # return all(rx_slice.tuner.lock_status for rx_slice in self.rx_slices)
    #
    #     # TODO: find a better way (is this a safe way? floating number comparisons are vulnerable to precision errors)
    #     # collect master lock wavelength parameter from all Rx slices tuners
    #     lock_wavelengths = [rx_slice.tuner.lock_wavelength for rx_slice in self.rx_slices]
    #     # check if there is any duplicate lock wavelength
    #     return len(set(lock_wavelengths)) == len(lock_wavelengths)

