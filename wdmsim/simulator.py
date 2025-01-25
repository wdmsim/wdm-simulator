
import logging
import random
from typing import List, NamedTuple, Optional

import numpy 
import pandas as pd
from art import text2art

from wdmsim.models.laser_grid import LaserGrid
from wdmsim.models.system_under_test import SystemUnderTest
# from wdmsim.arbiters.arbiter_registry import arbiter_registry
from wdmsim.arbiter.arbiter_factory import arbiter_registry

from wdmsim.schemas.design_params import LaserDesignParams, RingDesignParams, LaneOrderParams
from wdmsim.stats.lock_code_stat import LockCodeDistr, LockCodeStat
from wdmsim.stats.relation_stat import RelationDistr, RelationStats
from wdmsim.utils.sim_json import SimReplay

from wdmsim.utils.logger import _VERBOSE

logger = logging.getLogger(__name__)

"""
Simulator initializer helper methods
"""
def calculate_lane_order(
    lane_order_params: LaneOrderParams,
) -> Optional[List[int]]:
    """Calculate lane ordering from lane_order_params

    If lane_order_params.lane is None, then return None (for lock-to-any arbiters)
    If lane_order_params.lane is not None and is dict, then construct
    the lane ordering as a list of ints from the dict
    e.g., {0: 0, 1: 1, 2: 2} -> [0, 1, 2]
    """
    if lane_order_params.lane is None:
        return None
    else:
        return [lane_order_params.lane[i] for i in sorted(lane_order_params.lane.keys())]


def calculate_laser_wavelengths(
    laser_design_params: LaserDesignParams,
) -> List[float]:
    """Calculate laser wavelengths

    :param laser_design_params: LaserDesignParams object
    """
    num_channel       = laser_design_params.num_channel
    center_wavelength = laser_design_params.center_wavelength
    grid_spacing      = laser_design_params.grid_spacing
    grid_variance     = laser_design_params.grid_variance
    grid_max_offset   = laser_design_params.grid_max_offset
    
    # Use numpy to generate wavelengths
    # generate random grid variance in numpy array
    grid_variance_array = grid_spacing*numpy.random.uniform(-grid_variance, grid_variance, num_channel)
    # generate random grid variance in numpy array from gaussian distribution
    # grid_variance_array = grid_spacing*numpy.random.normal(0, grid_variance/3.0, num_channel)

    # generate random global grid offset
    grid_offset = grid_max_offset*random.uniform(-1,1)
    # generate numpy array of wavelengths
    wavelengths = center_wavelength + \
                    grid_spacing*(numpy.arange(num_channel)-num_channel/2.0) + \
                    grid_offset + \
                    grid_variance_array

    # convert numpy array to list
    wavelengths = wavelengths.tolist()
    return wavelengths


def calculate_ring_row_params(num_channel: int, ring_design_params: RingDesignParams) -> List[dict]:
    """Calculate ring row parameters

    :param ring_design_params: RingDesignParams object
    """
    # construct ring_row_params which is a list of dict of ring parameters
    # each dict is in a format {'fsr': fsr, 'tuning_range': tuning_range}

    # for each ring, sample tuning range from design parameters
    num_ring = num_channel
    ring_row_params = []
    for _ in range(num_ring):
        fsr_min = ring_design_params.fsr_mean * (1 - ring_design_params.fsr_variance)
        fsr_max = ring_design_params.fsr_mean * (1 + ring_design_params.fsr_variance)
        tuning_range_min = ring_design_params.tuning_range_mean * (1 - ring_design_params.tuning_range_variance)
        tuning_range_max = ring_design_params.tuning_range_mean * (1 + ring_design_params.tuning_range_variance)
        ring_row_params.append({
            'fsr': random.uniform(fsr_min, fsr_max),
            'tuning_range': random.uniform(tuning_range_min, tuning_range_max)
        })

    return ring_row_params


def calculate_ring_wavelengths(
    laser_design_params: LaserDesignParams, 
    ring_design_params: RingDesignParams,
) -> List[float]:
    """Calculate ring wavelengths
    
    ring wavelength is calculated by adding ring resonance variance to nominal laser grid spacing

    note that ring ordering is determined at SUT initialization, by init_lane_ordering parameter
    :param ring_design_params: RingDesignParams object
    """
    num_channel       = laser_design_params.num_channel
    center_wavelength = laser_design_params.center_wavelength
    grid_spacing      = laser_design_params.grid_spacing
    # fsr_mean          = ring_design_params.fsr_mean
    resonance_variance = ring_design_params.resonance_variance

    # ring_wavelength_variance_array = fsr_mean * numpy.random.uniform(-0.5, 0.5, num_channel)
    # ring_wavelength_variance_array = fsr_mean * numpy.random.uniform(-0.25, 0.25, num_channel)
    # ring_wavelength_variance_array = numpy.random.normal(0, resonance_variance / 3.0, num_channel)
    # ring_wavelength_variance_array = resonance_variance * numpy.random.normal(0, 1, num_channel)
    ring_wavelength_variance_array = resonance_variance * numpy.random.uniform(-1, 1, num_channel)
    # ring_wavelength_variance_array = numpy.random.uniform(-resonance_variance, resonance_variance, num_channel)

    # wavelengths = center_wavelength + \
    #         grid_spacing*(numpy.arange(num_channel)-num_channel/2.0) + \
    #         ring_wavelength_variance_array

    # TODO: is this ok?
    # # Due to red-shift, offset nominal center wavelength by half of tuning range
    # static_offset = -1 * ring_design_params.tuning_range_mean / 2.0
    # static offset to be half the FSR (large enough "fabrication bias" [Georgas, CICC 2011])
    static_offset = -1 * ring_design_params.fsr_mean / 2.0
    # # Try to use 2x the grid spacing as static offset
    # static_offset = -1 * grid_spacing * 2.0

    wavelengths = center_wavelength + \
            grid_spacing*(numpy.arange(num_channel)-num_channel/2.0) + \
            static_offset + \
            ring_wavelength_variance_array

    # convert numpy array to list
    return wavelengths.tolist()


# def initialize_laser_grid(
#     laser_design_params: LaserDesignParams,
# ) -> LaserGrid:
#     """Build new laser grid from design parameters
#
#     :param laser_design_params: LaserDesignParams object
#     """
#     # calculate laser wavelengths
#     wavelengths = calculate_laser_wavelengths(laser_design_params)
#
#     # build laser grid
#     return LaserGrid.from_wavelengths(wavelengths=wavelengths)


# def build_sysundertest_mmrralign(
#     ring_design_params: RingDesignParams,
#     arbiter_of_choice: str,
#     laser_grid: LaserGrid,
# ) -> SystemUnderTest:
#     """Build new system under test for multi-mrr alignment experiment
#     Assumes ring lane ordering is enforced (e.g., channel allocation via heater, optical circuit switching, etc.)
#
#     For system under test, rings are initially locked to the initial laser grid
#     :param ring_design_params: RingDesignParams object
#     """
#     # construct ring_row_params which is a list of dict of ring parameters
#     ring_row_params = calculate_ring_row_params(laser_grid.num_channels, ring_design_params)
#
#     # return system under test
#     return SystemUnderTest.build_from_laser_grid(
#                ring_row_params=ring_row_params,
#                arbiter_cls=arbiter_registry[arbiter_of_choice],
#                laser_grid=laser_grid,
#            )
#
#
# def build_sysundertest_mmrrinit(
#     ring_design_params: RingDesignParams,
#     laser_design_params: LaserDesignParams,
#     arbiter_of_choice: str,
# ) -> SystemUnderTest:
#     """Build new system under testf for multi-mrr initialization experiment
#     Assume ring lane ordering is *not* enforced which is the case of a new system initialization
#
#     For system under test, rings are randomly distributed across the range
#     For now assumes 50% of FSR is a ring resonance variance
#     :param ring_design_params: RingDesignParams object
#     """
#     # construct ring_row_params which is a list of dict of ring parameters
#     ring_row_params = calculate_ring_row_params(laser_design_params.num_channel, ring_design_params)
#
#     # calculate ring wavelengths
#     ring_wavelengths = calculate_ring_wavelengths(laser_design_params, ring_design_params)
#
#     # return system under test
#     return SystemUnderTest.build_with_ring_wavelengths(
#                ring_row_params=ring_row_params,
#                arbiter_cls=arbiter_registry[arbiter_of_choice],
#                ring_wavelengths=ring_wavelengths,
#            )


class SimulatorOutputs(NamedTuple):
    """Simulator return object"""
    laser: LaserDesignParams
    ring: RingDesignParams
    # TODO: arbiter type should be defined as an enum
    arbiter_str: str
    init_lane_order: LaneOrderParams
    tgt_lane_order: LaneOrderParams
    result: dict

    def to_dataframe(self):
        """Convert to pandas dataframe"""
        df_laser = pd.DataFrame(self.laser._asdict(), index=[0])
        df_ring = pd.DataFrame(self.ring._asdict(), index=[0])
        df_arbiter = pd.DataFrame({'arbiter': [self.arbiter_str]}, index=[0])
        df_init_lo = pd.DataFrame({'init_lane_order': [self.init_lane_order.alias]}, index=[0])
        df_tgt_lo = pd.DataFrame({'tgt_lane_order': [self.tgt_lane_order.alias]}, index=[0])
        df_result = pd.DataFrame(self.result, index=[0])
        return pd.concat([df_laser, df_ring, df_arbiter, df_init_lo, df_tgt_lo, df_result], 
                         keys=['laser', 'ring', 'arbiter', 'init_lane_order', 'tgt_lane_order', 'result'],
                         axis=1,
                         names=['type', 'param'],
                         sort=False)


class Simulator:
    """Simulator class for WDM burst mode lock experiments with System Under Test

    This class consolidates the following components:
    - System Under Test
    - Laser Grid
    - Laser Design Parameters
    - Ring Design Parameters
    - Arbiter of Choice
    - Experiment Parameters
    - Experiment Results

    and is responsible for:
    - Initializing the system under test
    - Initializing the laser grid
    - Running the experiment
    - Collecting the results

    Attributes:
        system_under_test: SystemUnderTest object
        laser_grid: LaserGrid object
        laser_design_params: LaserDesignParams object
        ring_design_params: RingDesignParams object
        arbiter_of_choice: string
    """
    def __init__(self, 
                 system_under_test: SystemUnderTest, 
                 laser_grid: LaserGrid,
                 laser_design_params: LaserDesignParams,
                 ring_design_params: RingDesignParams,
                 init_lane_order_params: LaneOrderParams,
                 tgt_lane_order_params: LaneOrderParams,
                 arbiter_of_choice: str,
                 ) -> "Simulator":
        """Constructor

        :param system_under_test: SystemUnderTest object
        :param laser_grid: LaserGrid object
        :param laser_design_params: LaserDesignParams object
        :param ring_design_params: RingDesignParams object
        :param arbiter_of_choice: string of arbiter of choice
        """
        # System Components
        self.system_under_test = system_under_test
        self.laser_grid = laser_grid

        # Design Parameters
        self.laser_design_params = laser_design_params
        self.ring_design_params = ring_design_params
        self.init_lane_order_params = init_lane_order_params
        self.tgt_lane_order_params = tgt_lane_order_params
        self.arbiter_of_choice = arbiter_of_choice

    def __str__(self) -> str:
        """String representation of simulator object

        :return: string representation of simulator object
        """
        return f"Simulator: {self.system_under_test} with {self.arbiter_of_choice} arbiter"

    def __repr__(self) -> str:
        """String representation of simulator object

        :return: string representation of simulator object
        """
        return f"Simulator_{self.system_under_test}_arbiter_{self.arbiter_of_choice}"

    """
    Simulator initialization methods
    """
    @classmethod
    def build_from_design_params(
        cls,
        laser_design_params: LaserDesignParams,
        ring_design_params: RingDesignParams,
        init_lane_order_params: LaneOrderParams,
        tgt_lane_order_params: LaneOrderParams,
        arbiter_of_choice: str,
    ) -> 'Simulator':
        """System initializer
        This method builds simulator from design parameters

        :param laser_design_params: LaserDesignParams object
        :param ring_design_params: RingWDMDesignParams object
        :param arbiter_of_choice: string
        :return: Simulator object
        """
        # initialize laser grid
        # laser_grid = initialize_laser_grid(laser_design_params)
        laser_grid = LaserGrid.from_wavelengths(
            wavelengths=calculate_laser_wavelengths(laser_design_params),
        )

        # construct ring_row_params which is a list of dict of ring parameters
        ring_row_params = calculate_ring_row_params(laser_design_params.num_channel, ring_design_params)

        # construct lane orders
        init_lane_order = calculate_lane_order(init_lane_order_params)
        tgt_lane_order = calculate_lane_order(tgt_lane_order_params)

        if ring_design_params.inherit_laser_variance:
            # # build system under test initially locked to laser grid for multi-mrr alignment experiment
            # system_under_test = build_sysundertest_mmrralign(ring_design_params, arbiter_of_choice, laser_grid)
            # assume rings are initially locked to laser grid
            # note that ring ordering is determined by init_lane_order, applied at SUT initialization
            ring_wavelengths = laser_grid.wavelengths
        else:
            # # build system under test initially locked to laser grid for multi-mrr initialization experiment
            # system_under_test = build_sysundertest_mmrrinit(ring_design_params, laser_design_params, arbiter_of_choice)
            # calculate ring wavelengths
            ring_wavelengths = calculate_ring_wavelengths(laser_design_params, ring_design_params)

        system_under_test = SystemUnderTest.construct_slices_and_arbiter(
            ring_row_params=ring_row_params,
            ring_wavelengths=ring_wavelengths,
            init_lane_order=init_lane_order,
            arbiter_cls=arbiter_registry[arbiter_of_choice],
            tgt_lane_order=tgt_lane_order,
        )

        # return simulator instance
        return cls(
            system_under_test, 
            laser_grid, 
            laser_design_params, 
            ring_design_params, 
            init_lane_order_params,
            tgt_lane_order_params,
            arbiter_of_choice,
        )

    @classmethod
    def build_replay(
        cls,
        laser_design_params: LaserDesignParams,
        ring_design_params: RingDesignParams,
        init_lane_order_params: LaneOrderParams,
        tgt_lane_order_params: LaneOrderParams,
        arbiter_of_choice: str,
        laser_wavelengths: List[float],
        ring_wavelengths: List[float],
        ring_row_params: List[dict],
    ) -> 'Simulator':
        """System initializer for replay
        This method builds simulator from all the parameters and the replay data

        :return: Simulator object
        """
        # initialize laser grid
        laser_grid = LaserGrid.from_wavelengths(laser_wavelengths)

        # parse parameters
        arbiter_cls = arbiter_registry[arbiter_of_choice]
        # init_lane_order = calculate_lane_order(init_lane_order_params)
        tgt_lane_order = calculate_lane_order(tgt_lane_order_params)

        # `init_lane_order` set to None for replay
        # Use the implicit ring wavelength ordering from the replay data to avoid doubly reordering
        system_under_test = SystemUnderTest.construct_slices_and_arbiter(
            ring_row_params=ring_row_params, 
            ring_wavelengths=ring_wavelengths,
            init_lane_order=None,
            # init_lane_order,
            arbiter_cls=arbiter_cls, 
            tgt_lane_order=tgt_lane_order,
        )

        # return simulator instance
        return cls(
            system_under_test,
            laser_grid,
            laser_design_params,
            ring_design_params,
            init_lane_order_params,
            tgt_lane_order_params,
            arbiter_of_choice,
        )

    """
    Simulation run methods
    """
    def shuffle_laser_grid(self) -> None:
        """Shuffle new laser grid into the system
        """
        # calculate new laser wavelengths by the initial lane order
        wavelengths = calculate_laser_wavelengths(self.laser_design_params)

        # shuffle laser grid
        self.laser_grid.shuffle_wavelengths(wavelengths)

    def shuffle_ring_row(self) -> None:
        """Shuffle new ring row (or SUT) into the system

        To shuffle the new ring row, we need to rebuild the system under test
        with the new ring row parameters
        """

        # if self.ring_design_params.inherit_laser_variance:
        #     self.system_under_test = build_sysundertest_mmrralign(self.ring_design_params, self.arbiter_of_choice, self.laser_grid)
        # else:
        #     self.system_under_test = build_sysundertest_mmrrinit(self.ring_design_params, self.laser_design_params, self.arbiter_of_choice)

        # construct ring_row_params which is a list of dict of ring parameters
        ring_row_params = calculate_ring_row_params(self.laser_design_params.num_channel, self.ring_design_params)

        # construct lane orders
        init_lane_order = calculate_lane_order(self.init_lane_order_params)
        tgt_lane_order = calculate_lane_order(self.tgt_lane_order_params)

        # create ring wavelengths *unsorted* 
        if self.ring_design_params.inherit_laser_variance:
            # # build system under test initially locked to laser grid for multi-mrr alignment experiment
            # system_under_test = build_sysundertest_mmrralign(ring_design_params, arbiter_of_choice, laser_grid)
            # assume rings are initially locked to laser grid
            # note that ring ordering is determined by init_lane_order, ordered at SUT initialization
            ring_wavelengths = self.laser_grid.wavelengths
        else:
            # # build system under test initially locked to laser grid for multi-mrr initialization experiment
            # system_under_test = build_sysundertest_mmrrinit(ring_design_params, laser_design_params, arbiter_of_choice)
            # calculate ring wavelengths
            ring_wavelengths = calculate_ring_wavelengths(self.laser_design_params, self.ring_design_params)

        # build system under test with new ring row
        # note that ring ordering is determined at this step by init_lane_order
        self.system_under_test = SystemUnderTest.construct_slices_and_arbiter(
            ring_row_params=ring_row_params,
            ring_wavelengths=ring_wavelengths,
            init_lane_order=init_lane_order,
            arbiter_cls=arbiter_registry[self.arbiter_of_choice],
            tgt_lane_order=tgt_lane_order,
        )

    def do_experiment(self, num_ring_swaps: int, num_laser_swaps: int) -> SimulatorOutputs:
        """Run experiment

        :param num_ring_swaps: number of ring swaps
        :param num_laser_swaps: number of laser swaps
        :return: SimulatorOutputs object
        """
        # initialize experiment results
        # zero lock count
        num_zero_lock = 0
        # duplicate lock count
        num_duplicate_lock = 0
        # wrong lane order count
        num_wrong_lane_order = 0

        # if tgt lane order is none, then we don't need to check for wrong lane order
        check_wrong_lane_order = self.system_under_test.arbiter.target_lane_order is not None

        # run iterations
        for _ in range(num_ring_swaps):
            # first loop swaps ring row after laser swap iterations
            self.shuffle_ring_row()
            for _ in range(num_laser_swaps):
                # second loop swaps laser grid at each iteration
                # self.laser_grid is shuffled in place
                # At each iteration, shuffle laser grid and run experiment
                self.shuffle_laser_grid()
                exit_status = self.system_under_test.run_lock_sequence(laser_grid=self.laser_grid,
                                                                       plot_snapshot=False,
                                                                       plot_statistics=False)
                if exit_status == SystemUnderTest.EXIT_DUPLICATE_LOCK:
                    num_duplicate_lock += 1
                elif exit_status == SystemUnderTest.EXIT_ZERO_LOCK:
                    num_zero_lock += 1
                elif check_wrong_lane_order and exit_status == SystemUnderTest.EXIT_WRONG_LANE_ORDER:
                    num_wrong_lane_order += 1
                else:
                    pass

        # experiment results
        num_experiments = num_laser_swaps * num_ring_swaps
        num_failure = num_zero_lock + num_duplicate_lock + num_wrong_lane_order
        num_success = num_experiments - num_failure
        failure_in_time = num_failure / num_experiments
        failure_zero_lock = num_zero_lock / num_experiments
        failure_duplicate_lock = num_duplicate_lock / num_experiments
        failure_wrong_lane_order = num_wrong_lane_order / num_experiments

        # log experiment results - iterations and failure in time
        logging.info(f"[Experiment] ")
        logging.info(f"    - {num_experiments:06d} iterations")
        logging.info(f"    - {num_success:06d} successes")
        logging.info(f"    - {num_failure:06d} failures")
        logging.info(f"    - {num_zero_lock:05f} zero lock failures")
        logging.info(f"    - {num_duplicate_lock:05f} duplicate lock failures")
        logging.info(f"    - {num_wrong_lane_order:05f} wrong lane order failures")
        logging.info(f"    - {failure_in_time:05f} failure in time")
        logging.info(f"    - {failure_zero_lock:05f} failure in time by zero lock")
        logging.info(f"    - {failure_duplicate_lock:05f} failure in time by duplicate lock")
        logging.info(f"    - {failure_wrong_lane_order:05f} failure in time by wrong lane order")

        # assemble result into a dict
        result = {
            'num_success': num_success,
            'num_failure': num_failure,
            'num_zero_lock': num_zero_lock,
            'num_duplicate_lock': num_duplicate_lock,
            'num_wrong_lane_order': num_wrong_lane_order,
            'failure_in_time': failure_in_time,
            'failure_zero_lock': failure_zero_lock,
            'failure_duplicate_lock': failure_duplicate_lock,
            'failure_wrong_lane_order': failure_wrong_lane_order,
        }

        return SimulatorOutputs(
                self.laser_design_params, 
                self.ring_design_params, 
                self.arbiter_of_choice, 
                self.init_lane_order_params,
                self.tgt_lane_order_params,
                result
                )

    def do_compare_experiment(self, 
                              arbiter_of_compare: str, 
                              num_ring_swaps: int, 
                              num_laser_swaps: int, 
                              stop_on_failure: bool = False) -> SimulatorOutputs:
        """Run compare experiment
        Added `stop_on_failure` flag for interactive debugging, default to False

        :param num_ring_swaps: number of ring swaps
        :param num_laser_swaps: number of laser swaps
        :return: SimulatorOutputs object
        """
        # setup global parameters
        arbiter_cls = arbiter_registry[self.arbiter_of_choice]
        arbiter_compare_cls = arbiter_registry[arbiter_of_compare]
        init_lane_order = calculate_lane_order(self.init_lane_order_params)
        tgt_lane_order = calculate_lane_order(self.tgt_lane_order_params)

        # initialize experiment results
        num_failure = 0

        # wrong lane order count
        num_wrong_lane_order_mismatch = 0

        # if tgt lane order is none, then we don't need to check for wrong lane order
        check_wrong_lane_order = self.system_under_test.arbiter.target_lane_order is not None

        # exit status is loosely defined (lousy classification)
        # see if both failed or both succeeded
        is_success = lambda x: x == SystemUnderTest.EXIT_SUCCESS

        # detailed diagnostics
        zero_dupl_case = [SystemUnderTest.EXIT_ZERO_LOCK, SystemUnderTest.EXIT_DUPLICATE_LOCK]
        wrong_order_case = [SystemUnderTest.EXIT_WRONG_LANE_ORDER]

        num_zero_dupl_lock_mismatch = 0
        num_wrong_lane_order_mismatch = 0
    
        # tracking individual failures
        _num_failure_arbiter = 0
        _num_failure_arbiter_compare = 0

        # run iterations
        for _ in range(num_ring_swaps):
            # first loop swaps ring row after laser swap iterations
            # self.shuffle_ring_row()
            ring_row_params = calculate_ring_row_params(self.laser_design_params.num_channel, self.ring_design_params)

            # TODO: VERIFY!
            # create ring wavelengths *unsorted* 
            if self.ring_design_params.inherit_laser_variance:
                # assume rings are initially locked to laser grid
                # note that ring ordering is determined by init_lane_order, ordered at SUT initialization
                ring_wavelengths = self.laser_grid.wavelengths
            else:
                # calculate ring wavelengths
                ring_wavelengths = calculate_ring_wavelengths(self.laser_design_params, self.ring_design_params)

            # shuffle in new SUT with ring row parameters (and ring wavelengths)
            self.system_under_test = SystemUnderTest.construct_slices_and_arbiter(
                ring_row_params=ring_row_params,
                # ring_wavelengths=self.laser_grid.wavelengths, # TODO: is this correct?
                ring_wavelengths=ring_wavelengths,
                init_lane_order=init_lane_order,
                arbiter_cls=arbiter_cls,
                tgt_lane_order=tgt_lane_order,
            )

            # instantiate a new system under test with arbiter_of_compare
            system_under_test_compare = SystemUnderTest.construct_slices_and_arbiter(
                ring_row_params=ring_row_params,
                # ring_wavelengths=self.laser_grid.wavelengths, # TODO: is this correct?
                ring_wavelengths=ring_wavelengths,
                init_lane_order=init_lane_order,
                arbiter_cls=arbiter_compare_cls,
                tgt_lane_order=tgt_lane_order,
            )

            for _ in range(num_laser_swaps):
                # second loop swaps laser grid at each iteration
                self.shuffle_laser_grid()
                exit_status = self.system_under_test.run_lock_sequence(
                    laser_grid=self.laser_grid,
                    plot_snapshot=False,
                    plot_statistics=False,
                )

                # run the same experiment with the system under test with arbiter_of_compare
                exit_status_compare = system_under_test_compare.run_lock_sequence(
                    laser_grid=self.laser_grid,
                    plot_snapshot=False,
                    plot_statistics=False,
                )

                is_both_success = is_success(exit_status) and is_success(exit_status_compare)
                is_both_failure = not is_success(exit_status) and not is_success(exit_status_compare)

                # Record individual status
                if not is_success(exit_status):
                    _num_failure_arbiter += 1
                if not is_success(exit_status_compare):
                    _num_failure_arbiter_compare += 1

                # compare the exit status
                # if exit_status != exit_status_compare:
                # compare the success/fail status only
                # directly comparing error status caused 0.7% error at *extreme* corner cases
                if not is_both_success and not is_both_failure:
                    # exit if stop_at_err is True
                    # Exception raising for now, but there could be a better way
                    if stop_on_failure:
                        # logging.info(f"Exit status mismatch: {exit_status} vs {exit_status_compare}")
                        raise Exception(f"Exit status mismatch: {exit_status} vs {exit_status_compare}")

                    # if the exit status is different, then we have a failure
                    # raise Exception(f"Exit status mismatch: {exit_status} vs {exit_status_compare}")
                    num_failure += 1

                    if not is_success(exit_status):
                        num_zero_dupl_lock_mismatch += 1 if exit_status in zero_dupl_case else 0
                        num_wrong_lane_order_mismatch += 1 if exit_status in wrong_order_case else 0

                    elif not is_success(exit_status_compare):
                        num_zero_dupl_lock_mismatch += 1 if exit_status_compare in zero_dupl_case else 0
                        num_wrong_lane_order_mismatch += 1 if exit_status_compare in wrong_order_case else 0

                    if logger.isEnabledFor(_VERBOSE):
                        logger.info(f"\n{text2art('COMPARE FAIL')}")

                else:
                    # pass
                    if logger.isEnabledFor(_VERBOSE):
                        logger.info(f"\n{text2art('COMPARE SUCCESS')}")

                    # # otherwise, check if both have the same wavelength lock
                    # if exit_status == SystemUnderTest.EXIT_SUCCESS:
                    #     # if both have the same wavelength lock, then we have a success
                    #     tuner_wvl = [rx_slice.tuner.lock_wavelength for rx_slice in self.system_under_test.rx_slices]
                    #     tuner_wvl_compare = [rx_slice.tuner.lock_wavelength for rx_slice in system_under_test_compare.rx_slices]
                    #     if tuner_wvl != tuner_wvl_compare:
                    #         logger.info(f"Lock wavelength mismatch: {tuner_wvl} vs {tuner_wvl_compare}")
                    #         # raise Exception(f"Lock wavelength mismatch: {tuner_wvl} vs {tuner_wvl_compare}")

                # # add detailed diagnostics
                # if exit_status == SystemUnderTest.EXIT_DUPLICATE_LOCK:
                #     num_zero_dup_lock_mismatch += 1
                # elif exit_status == SystemUnderTest.EXIT_ZERO_LOCK:
                #     num_zero_lock_arb += 1
                # elif exit_status == SystemUnderTest.EXIT_WRONG_LANE_ORDER:
                #     num_wrong_lane_order_mismatch += 1
                #
                # if exit_status_compare == SystemUnderTest.EXIT_DUPLICATE_LOCK:
                #     num_duplicate_lock_arbcomp += 1
                # elif exit_status_compare == SystemUnderTest.EXIT_ZERO_LOCK:
                #     num_zero_lock_arbcomp += 1
                # elif exit_status_compare == SystemUnderTest.EXIT_WRONG_LANE_ORDER:
                #     num_wrong_lane_order_arbcomp += 1

                # # Updated diagnostics
                # if exit_status in zero_dupl_case and exit_status_compare not in zero_dupl_case:
                #     num_zero_dupl_lock_mismatch += 1
                # elif exit_status not in zero_dupl_case and exit_status_compare in zero_dupl_case:
                #     num_zero_dupl_lock_mismatch += 1
                #
                # if exit_status in wrong_order_case and exit_status_compare not in wrong_order_case:
                #     num_wrong_lane_order_mismatch += 1
                # elif exit_status not in wrong_order_case and exit_status_compare in wrong_order_case:
                #     num_wrong_lane_order_mismatch += 1


            # logging.info(f"Experiment completed - They are the same!")

        # experiment results
        num_experiments = num_laser_swaps * num_ring_swaps
        num_success = num_experiments - num_failure
        failure_in_time = num_failure / num_experiments
        # detailed diagnostics
        failure_zero_dupl_lock = num_zero_dupl_lock_mismatch / num_experiments
        failure_wrong_lane_order = num_wrong_lane_order_mismatch / num_experiments
        # individual failure rates
        _failure_arbiter = _num_failure_arbiter / num_experiments
        _failure_arbiter_compare = _num_failure_arbiter_compare / num_experiments

        # log experiment results - iterations and failure in time
        logging.info(f"[Experiment] ")
        logging.info(f"    - {num_experiments:06d} iterations")
        logging.info(f"    - {num_success:06d} successes")
        logging.info(f"    - {num_failure:06d} failures")
        logging.info(f"    - {failure_in_time:05f} failure in time")

        # assemble result into a dict
        result = {
            'num_success': num_success,
            'num_failure': num_failure,
            'failure_in_time': failure_in_time,
            # detailed diagnostics
            'num_zero_dupl_lock_mismatch': num_zero_dupl_lock_mismatch,
            'num_wrong_lane_order_mismatch': num_wrong_lane_order_mismatch,
            'failure_zero_dupl_lock': failure_zero_dupl_lock,
            'failure_wrong_lane_order': failure_wrong_lane_order,
            # individual failure rates
            '_failure_rate_arbiter': _failure_arbiter,
            '_failure_rate_arbiter_compare': _failure_arbiter_compare,
        }

        return SimulatorOutputs(
                self.laser_design_params, 
                self.ring_design_params, 
                self.arbiter_of_choice, 
                self.init_lane_order_params,
                self.tgt_lane_order_params,
                result
                )

    def do_debug(self, target_exit_status: int, max_trial: int, plot_snapshot: bool) -> SimulatorOutputs:
        """Run experiment for debug

        :param target_exit_status: target exit status
        :param max_trials: maximum number of trials to run
        """
        assert target_exit_status in [SystemUnderTest.EXIT_SUCCESS, 
                                      SystemUnderTest.EXIT_ZERO_LOCK, 
                                      SystemUnderTest.EXIT_DUPLICATE_LOCK,
                                      SystemUnderTest.EXIT_WRONG_LANE_ORDER], \
            "Invalid target exit status"

        logging.info(f"Entering Debug Mode...")
        logging.info(f"Producing Snapshot Plots of System Under Test...")

        for _ in range(max_trial):
            self.shuffle_ring_row()
            for _ in range(max_trial):
                self.shuffle_laser_grid()
                exit_status = self.system_under_test.run_lock_sequence(laser_grid=self.laser_grid, 
                                                                       plot_snapshot=plot_snapshot,
                                                                       plot_statistics=False)
                if exit_status == target_exit_status:
                    result = {
                        'exit_status': exit_status,
                        'snapshots': self.system_under_test.snapshots
                    }
                    return SimulatorOutputs(
                            self.laser_design_params, 
                            self.ring_design_params, 
                            self.arbiter_of_choice, 
                            self.init_lane_order_params,
                            self.tgt_lane_order_params,
                            result
                            )
        else:
            raise ValueError(f"Failed to produce target exit status {target_exit_status} after {max_trial} trials")

    def do_statistics(self, num_bins: int, max_iterations: int) -> SimulatorOutputs:
        """Run statistics

        Extract lock code from system under test and calculate statistics

        :param num_iterations: number of iterations to run experiment
        """
        # run iterations until we get the desired number of lock codes to analyze
        # run a while loop for both laser and ring swaps and break both loops when lock success count reaches num_bin
        # and collect lock_codes_statistics 
        lock_code_stat : LockCodeStat = LockCodeStat()
        relation_stat : RelationStats = RelationStats()
        num_experiments = 0
        num_lock_success = 0
        while True:
            self.shuffle_ring_row()
            while True:
                self.shuffle_laser_grid()
                # self.laser_grid is shuffled in place
                # At each iteration, shuffle laser grid and run experiment
                exit_status = self.system_under_test.run_lock_sequence(laser_grid=self.laser_grid, 
                                                                       plot_snapshot=False,
                                                                       plot_statistics=True)
                if exit_status == SystemUnderTest.EXIT_SUCCESS:
                    lock_code_stat += self.system_under_test.lock_code_distr
                    relation_stat += self.system_under_test.relation_distr
                    num_lock_success += 1
                else:
                    pass
                num_experiments += 1

                # break both loops when lock success count reaches num_bin or num_experiments reaches max_iterations
                if num_lock_success >= num_bins:
                    result = {
                        'lock_code_stat': lock_code_stat,
                        'relation_stat': relation_stat,
                    }
                    if logger.isEnabledFor(_VERBOSE):
                        logger.info(f"Lock code statistics: {lock_code_stat}")
                        logger.info(f"Relation statistics: {relation_stat}")

                    return SimulatorOutputs(
                            self.laser_design_params, 
                            self.ring_design_params, 
                            self.arbiter_of_choice, 
                            self.init_lane_order_params,
                            self.tgt_lane_order_params,
                            result
                            )
                elif num_experiments >= max_iterations:
                    raise ValueError(f"Failed to produce {num_bins} lock codes after {max_iterations} trials")

    def do_record(self, num_ring_swaps: int, num_laser_swaps: int) -> List[SimReplay]:
        # initialize experiment results
        records = []
        # zero lock count
        num_zero_lock = 0
        # duplicate lock count
        num_duplicate_lock = 0
        # wrong lane order count
        num_wrong_lane_order = 0

        # run iterations
        for _ in range(num_ring_swaps):
            # first loop swaps ring row after laser swap iterations
            self.shuffle_ring_row()
            for _ in range(num_laser_swaps):
                # second loop swaps laser grid at each iteration
                # At each iteration, shuffle laser grid and run experiment
                self.shuffle_laser_grid()
                exit_status = self.system_under_test.run_lock_sequence(laser_grid=self.laser_grid,
                                                                       plot_snapshot=False,
                                                                       plot_statistics=False)

                # record the experiment
                records.append(
                    SimReplay(
                        self.laser_design_params,
                        self.ring_design_params,
                        self.init_lane_order_params,
                        self.tgt_lane_order_params,
                        self.arbiter_of_choice,
                        self.laser_grid.wavelengths,
                        self.system_under_test.ring_wdm_row.wavelengths,
                        self.system_under_test.ring_wdm_row.ring_row_params,
                        exit_status,
                    )
                )

                if exit_status == SystemUnderTest.EXIT_DUPLICATE_LOCK:
                    num_duplicate_lock += 1
                elif exit_status == SystemUnderTest.EXIT_ZERO_LOCK:
                    num_zero_lock += 1
                elif exit_status == SystemUnderTest.EXIT_WRONG_LANE_ORDER:
                    num_wrong_lane_order += 1
                else:
                    # lock_codes = self.system_under_test.get_statistics()
                    # lock_codes_statistics = lock_codes_statistics.append(lock_codes, ignore_index=True)
                    pass

        # experiment results
        num_experiments = num_laser_swaps * num_ring_swaps
        num_failure = num_zero_lock + num_duplicate_lock + num_wrong_lane_order
        num_success = num_experiments - num_failure
        failure_in_time = num_failure / num_experiments
        failure_zero_lock = num_zero_lock / num_experiments
        failure_duplicate_lock = num_duplicate_lock / num_experiments
        failure_wrong_lane_order = num_wrong_lane_order / num_experiments

        # log experiment results - iterations and failure in time
        logging.info(f"[Experiment] ")
        logging.info(f"    - {num_experiments:06d} iterations")
        logging.info(f"    - {num_success:06d} successes")
        logging.info(f"    - {num_failure:06d} failures")
        logging.info(f"    - {num_zero_lock:05f} zero lock failures")
        logging.info(f"    - {num_duplicate_lock:05f} duplicate lock failures")
        logging.info(f"    - {num_wrong_lane_order:05f} wrong lane order failures")
        logging.info(f"    - {failure_in_time:05f} failure in time")
        logging.info(f"    - {failure_zero_lock:05f} failure in time by zero lock")
        logging.info(f"    - {failure_duplicate_lock:05f} failure in time by duplicate lock")
        logging.info(f"    - {failure_wrong_lane_order:05f} failure in time by wrong lane order")

        return records

    def do_replay(self, expected_exit_status: bool) -> bool:
        exit_status = self.system_under_test.run_lock_sequence(laser_grid=self.laser_grid,
                                                               plot_snapshot=False,
                                                               plot_statistics=False)

        return exit_status == expected_exit_status
