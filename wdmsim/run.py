"""
Main Experiments Run functions
- run_experiment (run)
- run_experiments (sweep)

"""
import argparse
import cProfile
import logging
import multiprocessing
import os
from pathlib import Path
import pstats
import sys
from itertools import product
from typing import Any, NamedTuple, Optional, Tuple, Union, List

import pandas as pd
# import tabulate

# from tabulate import tabulate
# from tqdm import tqdm
# from tqdm.contrib.slack import tqdm as tqdm

from wdmsim.simulator import Simulator, SimulatorOutputs

from wdmsim.schemas.design_params import LaserDesignParams, RingDesignParams, LaneOrderParams
from wdmsim.schemas.base_config import ConfigFile, RunType
from wdmsim.schemas.yml_config import (
    ConfigYAML,
    LaserSweepConfigYAML,
    RingSweepConfigYAML,
)
from wdmsim.plotters.plotter import (
    ShmooPlotter,
    SnapshotPlotter,
    FigureTemplate,
    StatisticsPlotter,
)
from wdmsim.global_vars import DEBUG_MAX_TRIALS, STATISTICS_MAX_ITERATIONS
from wdmsim.utils.sim_json import SimReplay, SimSweepRecord
from wdmsim.utils.logger import _VERBOSE, setup_logger
from wdmsim.utils.pretty_print import pad_print, print_run_header, str_print
from wdmsim.utils.slack import tqdm_slack

logger = logging.getLogger(__name__)

_DESIGN_PARAMS_TYPE = Union[
    LaserDesignParams, 
    RingDesignParams, 
    LaneOrderParams,
    List[LaserDesignParams], 
    List[RingDesignParams],
    List[LaneOrderParams],
]

def get_design_params(
    config_file: str,
    config_section: str
) -> _DESIGN_PARAMS_TYPE:

    # config_cls = ConfigFile.from_filetype(config_file).get_config_cls(config_file, config_section)
    # ad-hoc solution
    if config_file.endswith('.yml') or config_file.endswith('.yaml'):
        config_cls = ConfigYAML.get_config_cls(config_file, config_section)
    else:
        raise NotImplementedError(f'Config file type not supported: {config_file}')

    if config_cls.RUN is RunType.SINGLE:
        return config_cls(config_file, config_section).design_params
    elif config_cls.RUN is RunType.SWEEP:
        return config_cls(config_file, config_section).design_sweep_params
    else:
        raise ValueError("Invalid config class")


class ExperimentPaths:
    def __init__(self, 
                 arbiter: str, 
                 laser_config_section: str, 
                 ring_config_section: str, 
                 init_lane_order_section: str,
                 tgt_lane_order_section: str,
                 results_dir: Union[str, Path],
                 result_type: str,
                 arbiter_compare: Optional[str] = None,
                 ):
        self.result_type = result_type
            
        self.arbiter_rep = f"AR_{arbiter}"
        self.laser_rep = f"LS_{laser_config_section}"
        self.ring_rep = f"RN_{ring_config_section}"
        self.init_lane_order_rep = f"ILO_{init_lane_order_section}"
        self.tgt_lane_order_rep = f"TLO_{tgt_lane_order_section}"

        self.arbiter_compare = arbiter_compare
        if not self._is_compare_type() and self.arbiter_compare is not None:
            raise ValueError("Arbiter compare must be None for non-compare result type")
        elif self._is_compare_type() and self.arbiter_compare is None:
            raise ValueError("Arbiter compare must be provided for compare result type")

        self.dirname = Path(self.arbiter_rep) / self.laser_rep
        # self.exp_results_dir = Path('results') / result_type / self.dirname
        # self.results_dir = Path(results_dir) if isinstance(results_dir, str) else results_dir

        if isinstance(results_dir, str):
            self.results_dir = Path(results_dir)
        elif isinstance(results_dir, Path):
            self.results_dir = results_dir
        else:
            raise ValueError(f"results_dir must be either str or Path, got {results_dir}")
        self.exp_results_dir = self.results_dir / result_type / self.dirname
        self.exp_results_dir.mkdir(parents=True, exist_ok=True)

    def _is_compare_type(self):
        """Check if result type is compare type

        If result type is compare, then arbiter_compare must be provided and additional processing is needed
        """
        return self.result_type == "compare" or self.result_type == "sweep_compare"

    def get_filepath(self, filename_suffix='', file_extension='csv') -> Path:
        if not self._is_compare_type():
            filename = f"{self.result_type}__{self.ring_rep}__{self.init_lane_order_rep}__{self.tgt_lane_order_rep}"
        else:
            arb_comp_tag = f"{self.arbiter_rep}_vs_{self.arbiter_compare}"
            filename = f"{self.result_type}__{arb_comp_tag}__{self.ring_rep}__{self.init_lane_order_rep}__{self.tgt_lane_order_rep}"

        if filename_suffix:
            filename += f"__{filename_suffix}"
        return self.exp_results_dir / f"{filename}.{file_extension}"


def run_filename_suffix(num_laser_swaps: int, num_ring_swaps: int) -> str:
    return f"num_swaps_laser_{num_laser_swaps}_ring_{num_ring_swaps}"

def sweep_filename_suffix(num_laser_swaps: int, num_ring_swaps: int) -> str:
    return run_filename_suffix(num_laser_swaps, num_ring_swaps)

def sweep_ptn_filename_suffix(num_laser_swaps: int, num_ring_swaps: int, ptn_idx: int) -> str:
    return run_filename_suffix(num_laser_swaps, num_ring_swaps) + f"__ptn_{ptn_idx}"

def stat_filename_suffix(num_bins: int) -> str:
    return f"num_bins_{num_bins}"

def run_experiment(
    laser_design_params: LaserDesignParams,
    ring_design_params: RingDesignParams,
    init_lane_order_params: LaneOrderParams,
    tgt_lane_order_params: LaneOrderParams,
    arbiter_of_choice: str,
    num_laser_swaps: int,
    num_ring_swaps: int,
) -> SimulatorOutputs:
    """Run experiment

    Wrapper function of simulator experiment runners
    It runs a set of experiments and produces lock success rate counts    

    :param laser_design_params: laser design parameters
    :param ring_design_params: ring design parameters
    :param arbiter_of_choice: arbiter of choice
    :param num_iterations: number of iterations
    :return: simulator outputs
    :rtype: SimulatorOutputs
    """

    # initialize simulator
    simulator = Simulator.build_from_design_params(
        laser_design_params, 
        ring_design_params, 
        init_lane_order_params,
        tgt_lane_order_params,
        arbiter_of_choice,
    )

    # run experiment
    sim_outputs = simulator.do_experiment(num_ring_swaps, num_laser_swaps)

    # TODO: VERY EXPERIMENTAL!
    # manually gc collect
    del simulator

    return sim_outputs


def run_compare(
    laser_design_params: LaserDesignParams,
    ring_design_params: RingDesignParams,
    init_lane_order_params: LaneOrderParams,
    tgt_lane_order_params: LaneOrderParams,
    arbiter_of_choice: str,
    arbiter_of_compare: str,
    num_laser_swaps: int,
    num_ring_swaps: int,
    stop_on_failure: bool = False,
) -> SimulatorOutputs:
    """Run experiment

    Wrapper function of simulator experiment runners
    It runs a set of experiments and produces lock success rate counts    

    :param laser_design_params: laser design parameters
    :param ring_design_params: ring design parameters
    :param arbiter_of_choice: arbiter of choice
    :param num_iterations: number of iterations
    :return: simulator outputs
    :rtype: SimulatorOutputs
    """

    # initialize simulator
    simulator = Simulator.build_from_design_params(
        laser_design_params, 
        ring_design_params, 
        init_lane_order_params,
        tgt_lane_order_params,
        arbiter_of_choice,
    )

    # compare arbiters
    sim_outputs = simulator.do_compare_experiment(arbiter_of_compare, num_ring_swaps, num_laser_swaps, stop_on_failure)

    # TODO: VERY EXPERIMENTAL!
    # manually gc collect
    del simulator

    return sim_outputs


def run_debug(
    laser_design_params: LaserDesignParams,
    ring_design_params: RingDesignParams,
    init_lane_order_params: LaneOrderParams,
    tgt_lane_order_params: LaneOrderParams,
    arbiter_of_choice: str,
    exit_status: int,
    plot_snapshot: bool,
) -> SimulatorOutputs:
    """Run debug experiment

    Wrapper function of simulator debug experiment runners
    It produces a debug snapshot plot of the experiment

    :param laser_design_params: laser design parameters
    :param ring_design_params: ring design parameters
    :param arbiter_of_choice: arbiter of choice
    :param exit_status: target exit status
    """
    max_trials = DEBUG_MAX_TRIALS

    if logger.isEnabledFor(_VERBOSE):
        logger.info(f"Running debug experiment with exit status {exit_status}...")

    # initialize simulator
    simulator = Simulator.build_from_design_params(
        laser_design_params, 
        ring_design_params, 
        init_lane_order_params,
        tgt_lane_order_params,
        arbiter_of_choice,
    )

    # run experiment
    sim_outputs = simulator.do_debug(exit_status, max_trials, plot_snapshot)

    return sim_outputs


def run_and_record(
    laser_design_params: LaserDesignParams,
    ring_design_params: RingDesignParams,
    init_lane_order_params: LaneOrderParams,
    tgt_lane_order_params: LaneOrderParams,
    arbiter_of_choice: str,
    num_laser_swaps: int,
    num_ring_swaps: int,
) -> List[SimReplay]:
    """Run experiment

    Wrapper function of simulator experiment runners
    It runs a set of experiments and produces lock success rate counts    

    :param laser_design_params: laser design parameters
    :param ring_design_params: ring design parameters
    :param arbiter_of_choice: arbiter of choice
    :param num_iterations: number of iterations
    :return: simulator outputs
    :rtype: SimulatorOutputs
    """

    # initialize simulator
    simulator = Simulator.build_from_design_params(
        laser_design_params, 
        ring_design_params, 
        init_lane_order_params,
        tgt_lane_order_params,
        arbiter_of_choice,
    )

    # run experiment
    sim_replays = simulator.do_record(num_ring_swaps, num_laser_swaps)

    return sim_replays

def run_replay(
    laser_design_params: LaserDesignParams,
    ring_design_params: RingDesignParams,
    init_lane_order_params: LaneOrderParams,
    tgt_lane_order_params: LaneOrderParams,
    arbiter_of_choice: str,
    laser_wavelengths: List[float],
    ring_wavelengths: List[float],
    ring_row_params: List[dict],
    expected_exit_status: int,
) -> bool:

    # initialize simulator
    simulator = Simulator.build_replay(
        laser_design_params, 
        ring_design_params, 
        init_lane_order_params,
        tgt_lane_order_params,
        arbiter_of_choice, 
        laser_wavelengths,
        ring_wavelengths, 
        ring_row_params
    )

    # run experiment
    success = simulator.do_replay(expected_exit_status)

    return success

def run_statistics(
    laser_design_params: LaserDesignParams,
    ring_design_params: RingDesignParams,
    init_lane_order_params: LaneOrderParams,
    tgt_lane_order_params: LaneOrderParams,
    arbiter_of_choice: str,
    num_bins: int,
) -> SimulatorOutputs:
    """Run lock code statistics experiment

    Wrapper function of simulator statistics experiment runners
    It produces a statistics of the experiment

    :param laser_design_params: laser design parameters
    :param ring_design_params: ring design parameters
    :param arbiter_of_choice: arbiter of choice
    :param exit_status: target exit status
    """
    max_iterations = STATISTICS_MAX_ITERATIONS

    # initialize simulator
    simulator = Simulator.build_from_design_params(
        laser_design_params, 
        ring_design_params, 
        init_lane_order_params,
        tgt_lane_order_params,
        arbiter_of_choice,
    )

    # run experiment
    sim_outputs = simulator.do_statistics(num_bins, max_iterations)

    return sim_outputs


def debug(
    exit_status, 
    arbiter, 
    laser_config_file, 
    laser_config_section, 
    ring_config_file, 
    ring_config_section, 
    init_lane_order_config_file,
    init_lane_order_config_section,
    tgt_lane_order_config_file,
    tgt_lane_order_config_section,
    results_dir,
    plot,
    verbose,
):

    pr = cProfile.Profile()
    pr.enable()

    # define experiment parameters
    laser_design_params : LaserDesignParams = get_design_params(laser_config_file,
                                                                laser_config_section)
    ring_design_params : RingDesignParams = get_design_params(ring_config_file,
                                                              ring_config_section)

    init_lane_order_params : LaneOrderParams = get_design_params(init_lane_order_config_file,
                                                                 init_lane_order_config_section)
    tgt_lane_order_params : LaneOrderParams = get_design_params(tgt_lane_order_config_file,
                                                                tgt_lane_order_config_section)

    # # set fname
    # arbiter_rep = f"arbiter_{arbiter}"
    # laser_rep = f"laser_{laser_config_section}"
    # ring_rep = f"ring_{ring_config_section}"
    # # fname = f"{arbiter_rep}__{laser_rep}__{ring_rep}"
    #
    # dirname = f"{arbiter_rep}/{laser_rep}"
    # fname = f"{ring_rep}"
    
    exp_paths = ExperimentPaths(
        arbiter, 
        laser_config_section, 
        ring_config_section, 
        init_lane_order_config_section,
        tgt_lane_order_config_section,
        results_dir,
        'debug',
    )

    # file name to save log file
    setup_logger(exp_paths.get_filepath(file_extension='log'), verbose)

    # file name to save sweep results in fig
    # fig_fname = f'results/debug/{dirname}/snapshot__{fname}.pdf'
    fig_fname = exp_paths.get_filepath(file_extension='pdf')

    # print log header
    print_run_header(
        laser_config_file, 
        laser_config_section,
        ring_config_file,
        ring_config_section, 
        init_lane_order_config_file,
        init_lane_order_config_section,
        tgt_lane_order_config_file,
        tgt_lane_order_config_section,
        laser_design_params, 
        ring_design_params, 
        init_lane_order_params,
        tgt_lane_order_params,
        arbiter,
    )

    # log experiment start
    logger.info(str_print("Experiment Start"))
    logger.info(pad_print())

    # If debug mode is set, run a single iteration and plot snapshots
    # run debug experiment until the exit status is 0
    sim_outputs = run_debug(
        laser_design_params, 
        ring_design_params, 
        init_lane_order_params,
        tgt_lane_order_params,
        arbiter, 
        exit_status, 
        plot,
    )

    # disable profile 
    pr.disable()
    # print profile stats of top 20 functions only ordered by tottime and cumtime
    ps = pstats.Stats(pr).sort_stats('tottime', 'cumtime')
    ps.print_stats(20)

    if plot:
        # plot snapshots
        snapshots = sim_outputs.result['snapshots']
        figsize_x, figsize_y = 25, 2*len(snapshots)
        fig_template = FigureTemplate.draw(nrows=len(snapshots), ncols=1, 
                                           figsize=(figsize_x, figsize_y),
                                           properties={'tight_layout': True})

        # TODO: remove hardcode
        fig_template.set_xlim([1285e-9, 1315e-9])

        for idx, axes in enumerate(fig_template.ax):
            SnapshotPlotter(axes).plot(snapshots[idx])
        fig_template.save(fig_fname)
        fig_template.show()


def run(
    profile, 
    num_laser_swaps, 
    num_ring_swaps,
    arbiter, 
    laser_config_file, 
    laser_config_section, 
    ring_config_file, 
    ring_config_section, 
    init_lane_order_config_file,
    init_lane_order_config_section,
    tgt_lane_order_config_file,
    tgt_lane_order_config_section,
    results_dir,
    verbose,
):
    """
    run function
    """
    if profile:
        # Profile code
        pr = cProfile.Profile()
        pr.enable()

    # define experiment parameters
    laser_design_params : LaserDesignParams = get_design_params(laser_config_file,
                                                                laser_config_section)
    ring_design_params : RingDesignParams = get_design_params(ring_config_file,
                                                              ring_config_section)

    init_lane_order_params : LaneOrderParams = get_design_params(init_lane_order_config_file,
                                                                 init_lane_order_config_section)
    tgt_lane_order_params : LaneOrderParams = get_design_params(tgt_lane_order_config_file,
                                                                tgt_lane_order_config_section)

    # verify experiment parameters
    # if parameters related to variations are 0, then it should be a single experiment
    if laser_design_params.grid_variance == 0 and laser_design_params.grid_max_offset == 0:
        if num_laser_swaps > 1:
            raise ValueError(f"Number of laser swaps should be 1 for a single experiment. \
                                Laser design parameters {laser_design_params}")
    
    if ring_design_params.fsr_variance == 0 and ring_design_params.tuning_range_variance == 0:
        if num_ring_swaps > 1:
            raise ValueError(f"Number of ring swaps should be 1 for a single experiment. \
                                Ring design parameters {ring_design_params}")

    exp_paths = ExperimentPaths(
        arbiter, 
        laser_config_section, 
        ring_config_section, 
        init_lane_order_config_section,
        tgt_lane_order_config_section,
        results_dir,
        'run',
    )

    # file name to save log file
    log_fpath: str = exp_paths.get_filepath(
        filename_suffix=run_filename_suffix(num_laser_swaps, num_ring_swaps), file_extension='log')
    setup_logger(log_fpath, verbose)
    # setup_logger(exp_paths.get_filepath(
    #     filename_suffix=run_filename_suffix(num_laser_swaps, num_ring_swaps), file_extension='log'), verbose=verbose)

    # print log header
    print_run_header(
        laser_config_file, 
        laser_config_section,
        ring_config_file,
        ring_config_section, 
        init_lane_order_config_file,
        init_lane_order_config_section,
        tgt_lane_order_config_file,
        tgt_lane_order_config_section,
        laser_design_params, 
        ring_design_params, 
        init_lane_order_params,
        tgt_lane_order_params,
        arbiter,
    )

    # log experiment start
    logging.info(str_print("Experiment Start"))
    logging.info(pad_print())

    sim_outputs = run_experiment(
        laser_design_params, 
        ring_design_params, 
        init_lane_order_params,
        tgt_lane_order_params,
        arbiter, 
        num_laser_swaps, 
        num_ring_swaps,
    )

    # log experiment end
    logging.info(pad_print())
    logging.info(str_print("Experiment End"))
    logging.info(pad_print())

    # print where the log file is stored
    logging.info(f"Log: {log_fpath}")

    if profile:
        # disable profile 
        pr.disable()
        # print profile stats of top 20 functions only ordered by tottime and cumtime
        ps = pstats.Stats(pr).sort_stats('tottime', 'cumtime')
        ps.print_stats(20)


def compare(
    num_laser_swaps, 
    num_ring_swaps,
    arbiter, 
    arbiter_compare,
    laser_config_file, 
    laser_config_section, 
    ring_config_file, 
    ring_config_section, 
    init_lane_order_config_file,
    init_lane_order_config_section,
    tgt_lane_order_config_file,
    tgt_lane_order_config_section,
    stop_on_failure,
    results_dir,
    verbose,
):
    """
    compare function
    """
    # define experiment parameters
    laser_design_params : LaserDesignParams = get_design_params(laser_config_file,
                                                                laser_config_section)
    ring_design_params : RingDesignParams = get_design_params(ring_config_file,
                                                              ring_config_section)

    init_lane_order_params : LaneOrderParams = get_design_params(init_lane_order_config_file,
                                                                 init_lane_order_config_section)
    tgt_lane_order_params : LaneOrderParams = get_design_params(tgt_lane_order_config_file,
                                                                tgt_lane_order_config_section)

    # verify experiment parameters
    # if parameters related to variations are 0, then it should be a single experiment
    if laser_design_params.grid_variance == 0 and laser_design_params.grid_max_offset == 0:
        if num_laser_swaps > 1:
            raise ValueError(f"Number of laser swaps should be 1 for a single experiment. \
                                Laser design parameters {laser_design_params}")
    
    if ring_design_params.fsr_variance == 0 and ring_design_params.tuning_range_variance == 0:
        if num_ring_swaps > 1:
            raise ValueError(f"Number of ring swaps should be 1 for a single experiment. \
                                Ring design parameters {ring_design_params}")

    exp_paths = ExperimentPaths(
        arbiter, 
        laser_config_section, 
        ring_config_section, 
        init_lane_order_config_section,
        tgt_lane_order_config_section,
        results_dir,
        'compare',
        arbiter_compare,
    )

    # file name to save log file
    # setup_logger(exp_paths.get_filepath(
    #     filename_suffix=run_filename_suffix(num_laser_swaps, num_ring_swaps), file_extension='log'), verbose=verbose)
    log_fpath: str = exp_paths.get_filepath(
        filename_suffix=run_filename_suffix(num_laser_swaps, num_ring_swaps), file_extension='log')
    setup_logger(log_fpath, verbose)

    # print log header
    print_run_header(
        laser_config_file, 
        laser_config_section,
        ring_config_file,
        ring_config_section, 
        init_lane_order_config_file,
        init_lane_order_config_section,
        tgt_lane_order_config_file,
        tgt_lane_order_config_section,
        laser_design_params, 
        ring_design_params, 
        init_lane_order_params,
        tgt_lane_order_params,
        arbiter,
    )

    # log experiment start
    logging.info(str_print("Experiment Start"))
    logging.info(pad_print())

    run_compare(
        laser_design_params, 
        ring_design_params, 
        init_lane_order_params,
        tgt_lane_order_params,
        arbiter, 
        arbiter_compare, 
        num_laser_swaps, 
        num_ring_swaps,
        stop_on_failure,
    )

    # log experiment end
    logging.info(pad_print())
    logging.info(str_print("Experiment End"))
    logging.info(pad_print())

    logging.info(f"Log: {log_fpath}")


def stat(
    num_bins,
    arbiter, 
    laser_config_file, 
    laser_config_section, 
    ring_config_file, 
    ring_config_section, 
    init_lane_order_config_file,
    init_lane_order_config_section,
    tgt_lane_order_config_file,
    tgt_lane_order_config_section,
    results_dir,
    plot,
    verbose,
    plot_slice=True,
    plot_summary=True,
):
    """
    run function
    """
    # define experiment parameters
    laser_design_params : LaserDesignParams = get_design_params(laser_config_file,
                                                                laser_config_section)
    ring_design_params : RingDesignParams = get_design_params(ring_config_file,
                                                              ring_config_section)

    init_lane_order_params : LaneOrderParams = get_design_params(init_lane_order_config_file,
                                                                 init_lane_order_config_section)
    tgt_lane_order_params : LaneOrderParams = get_design_params(tgt_lane_order_config_file,
                                                                tgt_lane_order_config_section)

    # verify experiment parameters
    # if parameters related to variations are 0, then it should be a single experiment
    if laser_design_params.grid_variance == 0 and laser_design_params.grid_max_offset == 0 \
        and ring_design_params.tuning_range_std == 0:
            raise ValueError(f"Cannot extract statistics without variations. \
                                Laser design parameters {laser_design_params} \
                                Ring design parameters {ring_design_params}")

    exp_paths = ExperimentPaths(
        arbiter, 
        laser_config_section, 
        ring_config_section, 
        init_lane_order_config_section,
        tgt_lane_order_config_section,
        results_dir,
        'stat',
    )

    # file name to save log file
    log_fpath: str = exp_paths.get_filepath(
        filename_suffix=stat_filename_suffix(num_bins), file_extension='log')
    setup_logger(log_fpath, verbose)
    # setup_logger(exp_paths.get_filepath(filename_suffix=stat_filename_suffix(num_bins), file_extension='log'),
    #              verbose=verbose)

    # file name to save sweep results in fig
    fig_fname = exp_paths.get_filepath(filename_suffix=stat_filename_suffix(num_bins), file_extension='pdf')

    # print log header
    print_run_header(
        laser_config_file, 
        laser_config_section,
        ring_config_file,
        ring_config_section, 
        init_lane_order_config_file,
        init_lane_order_config_section,
        tgt_lane_order_config_file,
        tgt_lane_order_config_section,
        laser_design_params, 
        ring_design_params, 
        init_lane_order_params,
        tgt_lane_order_params,
        arbiter,
    )

    # log experiment start
    logging.info(str_print("Experiment Start"))
    logging.info(pad_print())

    sim_outputs = run_statistics(
        laser_design_params, 
        ring_design_params, 
        init_lane_order_params,
        tgt_lane_order_params,
        arbiter, 
        num_bins,
    )

    if plot:
        # plot lock code statistics
        lock_code_stat = sim_outputs.result['lock_code_stat']
        figsize_x, figsize_y = 24, 14

        draw_template = lambda nrows: FigureTemplate.draw(nrows=nrows, ncols=1,
                                                          figsize=(figsize_x, figsize_y),
                                                          properties={'tight_layout': True})
        if plot_slice and plot_summary:
            nrows = 2
            fig_template = draw_template(nrows)
            StatisticsPlotter(fig_template.ax[0]).plot(lock_code_stat, plot_slice=True, plot_summary=False)
            StatisticsPlotter(fig_template.ax[1]).plot(lock_code_stat, plot_slice=False, plot_summary=True)
        elif plot_slice or plot_summary:
            nrows = 1
            fig_template = draw_template(nrows)
            StatisticsPlotter(fig_template.ax).plot(lock_code_stat, plot_slice=plot_slice, plot_summary=plot_summary)
        else:
            raise ValueError("At least one of plot_slice or plot_summary should be True")
        
        # fig_template = FigureTemplate.draw(nrows=nrows, ncols=1,
        #                                    figsize=(figsize_x, figsize_y),
        #                                    properties={'tight_layout': True})
        #
        # StatisticsPlotter(fig_template.axes[0]).plot(lock_code_stat)

        # boilerplate grid addition
        for axes in fig_template.ax:
            axes.grid(True)

        fig_template.save(fig_fname)
        # fig_template.show()


    # log experiment end
    logging.info(pad_print())
    logging.info(str_print("Experiment End"))
    logging.info(pad_print())

    logging.info(f"Log: {log_fpath}")


def _sweep(
    laser_design_sweep_params : Union[LaserDesignParams, List[LaserDesignParams]],
    ring_design_sweep_params : Union[RingDesignParams, List[RingDesignParams]],
    init_lane_order_params : LaneOrderParams,
    tgt_lane_order_params : LaneOrderParams,
    arbiter : str,
    num_laser_swaps : int, 
    num_ring_swaps : int, 
    nprocs : int,
) -> pd.DataFrame:
    """
    Core function to run sweep
    """
    # Initialize DataFrame to record the simulation result
    df_experiment = pd.DataFrame()

    # if nprocs is -1, then use all available processors
    # otherwise, use the number of processors specified
    # this includes a single process case when nproc = 1
    if nprocs == -1:
        mp_pool = multiprocessing.Pool()
    elif nprocs >= 1:
        mp_pool = multiprocessing.Pool(processes=nprocs)
    else:
        raise ValueError(f"nprocs should be -1 or >= 1. nprocs = {nprocs}")

    results_collect = []
    total_num_sims = len(laser_design_sweep_params) * len(ring_design_sweep_params)

    with tqdm_slack(
        total=total_num_sims,
        position=0,
        desc="Sweep",
        leave=True,
        unit="sims",
        postfix={
            'arbiter': arbiter,
            'num_laser_swaps': num_laser_swaps,
            'num_ring_swaps': num_ring_swaps,
            'node': os.uname().nodename,
            'nprocs': nprocs if nprocs != -1 else multiprocessing.cpu_count(),
        }
    ) as pbar:
        with mp_pool as pool:
            # Define the product of parameters
            param_product = product(
                                laser_design_sweep_params,
                                ring_design_sweep_params,
                                [init_lane_order_params],
                                [tgt_lane_order_params],
                                [arbiter],
                                [num_laser_swaps],
                                [num_ring_swaps])

            # Submit task asynchronously with a callback to update the progress bar
            results = []
            for param in param_product:
                result = pool.apply_async(run_experiment, args=param, callback=lambda x: pbar.update(1))
                results.append(result)

            # Ensure all tasks are done
            for result in results:
                output = result.get()
                results_collect.append(output.to_dataframe())
                    
        # Update the progress bar to 100%
        pbar.update(total_num_sims - pbar.n)
        pbar.refresh()

    # Concatenate all results at once
    df_experiment = pd.concat(results_collect, axis=0, sort=False, ignore_index=True)

    return df_experiment


def _sweep_compare(
    laser_design_sweep_params : Union[LaserDesignParams, List[LaserDesignParams]],
    ring_design_sweep_params : Union[RingDesignParams, List[RingDesignParams]],
    init_lane_order_params : LaneOrderParams,
    tgt_lane_order_params : LaneOrderParams,
    arbiter : str,
    arbiter_compare: str,
    num_laser_swaps : int, 
    num_ring_swaps : int, 
    nprocs : int,
) -> pd.DataFrame:
    """
    Core function to run sweep
    """
    # Initialize DataFrame to record the simulation result
    df_experiment = pd.DataFrame()

    # if nprocs is -1, then use all available processors
    # otherwise, use the number of processors specified
    # this includes a single process case when nproc = 1
    if nprocs == -1:
        mp_pool = multiprocessing.Pool()
    elif nprocs >= 1:
        mp_pool = multiprocessing.Pool(processes=nprocs)
    else:
        raise ValueError(f"nprocs should be -1 or >= 1. nprocs = {nprocs}")

    results_collect = []
    total_num_sims = len(laser_design_sweep_params) * len(ring_design_sweep_params)

    with tqdm_slack(
        total=total_num_sims,
        position=0,
        desc="Sweep",
        leave=True,
        unit="sims",
        postfix={
            'arbiter': arbiter,
            'arbiter_compare': arbiter_compare,
            'num_laser_swaps': num_laser_swaps,
            'num_ring_swaps': num_ring_swaps,
            'node': os.uname().nodename,
            'nprocs': nprocs if nprocs != -1 else multiprocessing.cpu_count(),
        }
    ) as pbar:
        with mp_pool as pool:
            # Define the product of parameters
            # Set stop_at_err to False (the last flag)
            param_product = product(
                                laser_design_sweep_params,
                                ring_design_sweep_params,
                                [init_lane_order_params],
                                [tgt_lane_order_params],
                                [arbiter],
                                [arbiter_compare],
                                [num_laser_swaps],
                                [num_ring_swaps],
                                [False])

            # Submit task asynchronously with a callback to update the progress bar
            results = []
            for param in param_product:
                result = pool.apply_async(run_compare, args=param, callback=lambda x: pbar.update(1))
                results.append(result)

            # Ensure all tasks are done
            for result in results:
                output = result.get()
                results_collect.append(output.to_dataframe())
                    
            # Update the progress bar to 100%
            pbar.update(total_num_sims - pbar.n)
            pbar.refresh()

    # Concatenate all results at once
    df_experiment = pd.concat(results_collect, axis=0, sort=False, ignore_index=True)

    return df_experiment


def _check_sweep_on_list(
    laser_design_sweep_params: Union[LaserDesignParams, List[LaserDesignParams]],
    ring_design_sweep_params: Union[RingDesignParams, List[RingDesignParams]]
) -> bool:
    # if both laser and ring design params are not a list, then it should be a single experiment, raise error
    if not isinstance(laser_design_sweep_params, list) and not isinstance(ring_design_sweep_params, list):
        return False
    return True


def sweep(
    nprocs, 
    num_laser_swaps,
    num_ring_swaps,
    arbiter, 
    laser_config_file, 
    laser_config_section, 
    ring_config_file, 
    ring_config_section, 
    init_lane_order_config_file,
    init_lane_order_config_section,
    tgt_lane_order_config_file,
    tgt_lane_order_config_section,
    results_dir,
    verbose,
):

    # define experiment parameters
    laser_design_sweep_params : Union[LaserDesignParams, List[LaserDesignParams]] = get_design_params(laser_config_file,
                                                                                                       laser_config_section)
    ring_design_sweep_params : Union[RingDesignParams, List[RingDesignParams]] = get_design_params(ring_config_file,
                                                                                                    ring_config_section)

    if not _check_sweep_on_list(laser_design_sweep_params, ring_design_sweep_params):
        raise ValueError(f"Cannot sweep without variations. \
                            Laser design parameters {laser_design_sweep_params} \
                            Ring design parameters {ring_design_sweep_params}")

    # if either one of them is a list, then wrap around params as list if either of them is a singleton    
    # to simplify the later code
    if isinstance(laser_design_sweep_params, LaserDesignParams):
        laser_design_sweep_params = [laser_design_sweep_params]
    if isinstance(ring_design_sweep_params, RingDesignParams):
        ring_design_sweep_params = [ring_design_sweep_params]
    
    LaserSweepConfigYAML.validator(laser_design_sweep_params, num_laser_swaps)
    RingSweepConfigYAML.validator(ring_design_sweep_params, num_ring_swaps)

    # define lane order parameters
    init_lane_order_params : LaneOrderParams = get_design_params(init_lane_order_config_file,
                                                                 init_lane_order_config_section)
    tgt_lane_order_params : LaneOrderParams = get_design_params(tgt_lane_order_config_file,
                                                                tgt_lane_order_config_section)

    exp_paths = ExperimentPaths(
        arbiter, 
        laser_config_section, 
        ring_config_section, 
        init_lane_order_config_section,
        tgt_lane_order_config_section,
        results_dir,
        'sweep',
    )

    # file name to save log file
    log_fpath: str = exp_paths.get_filepath(
        filename_suffix=sweep_filename_suffix(num_laser_swaps, num_ring_swaps), file_extension='log')
    setup_logger(log_fpath, verbose)
    # setup_logger(exp_paths.get_filepath(
    #     filename_suffix=sweep_filename_suffix(num_laser_swaps, num_ring_swaps), file_extension='log'), verbose)

    sweep_csv_fname = exp_paths.get_filepath(
        filename_suffix=sweep_filename_suffix(num_laser_swaps, num_ring_swaps), file_extension='csv')

    df_experiment = _sweep(
        laser_design_sweep_params,
        ring_design_sweep_params,
        init_lane_order_params,
        tgt_lane_order_params,
        arbiter,
        num_laser_swaps,
        num_ring_swaps,
        nprocs,
    )
    
    # pretty print dataframe using tabulate
    df_experiment_tbl = df_experiment.copy()

    # df_experiment has a MultiIndex column with two levels of labels,
    # we want to display the second level of labels 
    df_experiment_tbl.columns = df_experiment_tbl.columns.get_level_values(1)
    # print(tabulate(df_experiment_tbl, headers='keys', tablefmt='psql'))

    # save experiment dataframe to file
    # df_experiment.to_csv(sweep_csv_fname, sep='\t', index=True, header=df_experiment.columns.levels[1].tolist())
    # this seem to export multi-level header well enough
    df_experiment.to_csv(sweep_csv_fname, sep='\t', index=True)

    # df_read = pd.read_csv(sweep_csv_fname, sep='\t', header=[0, 1], index_col=0)
    # from pandas.testing import assert_frame_equal
    # assert_frame_equal(df_experiment, df_read, check_exact=False)

    # save the config to json for reproducibility
    sweep_json_fname = exp_paths.get_filepath(
        filename_suffix=sweep_filename_suffix(num_laser_swaps, num_ring_swaps), file_extension='json')
    
    sweep_record = SimSweepRecord(
        laser_config_file=laser_config_file,
        laser_config_section=laser_config_section,
        ring_config_file=ring_config_file,
        ring_config_section=ring_config_section,
        init_lane_order_config_file=init_lane_order_config_file,
        init_lane_order_config_section=init_lane_order_config_section,
        tgt_lane_order_config_file=tgt_lane_order_config_file,
        tgt_lane_order_config_section=tgt_lane_order_config_section,
        arbiter_str=arbiter,
        num_laser_swaps=num_laser_swaps,
        num_ring_swaps=num_ring_swaps,
        laser_design_sweep_params=laser_design_sweep_params,
        ring_design_sweep_params=ring_design_sweep_params,
        init_lane_order_params=init_lane_order_params,
        tgt_lane_order_params=tgt_lane_order_params,
    )

    sweep_record.record_json(sweep_json_fname)

    logging.info(f"Log: {log_fpath}")
    logging.info(f"Result CSV: {sweep_csv_fname}")


def sweep_compare(
    nprocs, 
    num_laser_swaps,
    num_ring_swaps,
    arbiter, 
    arbiter_compare,
    laser_config_file, 
    laser_config_section, 
    ring_config_file, 
    ring_config_section, 
    init_lane_order_config_file,
    init_lane_order_config_section,
    tgt_lane_order_config_file,
    tgt_lane_order_config_section,
    results_dir,
    verbose,
):

    # define experiment parameters
    laser_design_sweep_params : Union[LaserDesignParams, List[LaserDesignParams]] = get_design_params(laser_config_file,
                                                                                                       laser_config_section)
    ring_design_sweep_params : Union[RingDesignParams, List[RingDesignParams]] = get_design_params(ring_config_file,
                                                                                                    ring_config_section)

    if not _check_sweep_on_list(laser_design_sweep_params, ring_design_sweep_params):
        raise ValueError(f"Cannot sweep without variations. \
                            Laser design parameters {laser_design_sweep_params} \
                            Ring design parameters {ring_design_sweep_params}")

    # if either one of them is a list, then wrap around params as list if either of them is a singleton    
    # to simplify the later code
    if isinstance(laser_design_sweep_params, LaserDesignParams):
        laser_design_sweep_params = [laser_design_sweep_params]
    if isinstance(ring_design_sweep_params, RingDesignParams):
        ring_design_sweep_params = [ring_design_sweep_params]
    
    LaserSweepConfigYAML.validator(laser_design_sweep_params, num_laser_swaps)
    RingSweepConfigYAML.validator(ring_design_sweep_params, num_ring_swaps)

    # define lane order parameters
    init_lane_order_params : LaneOrderParams = get_design_params(init_lane_order_config_file,
                                                                 init_lane_order_config_section)
    tgt_lane_order_params : LaneOrderParams = get_design_params(tgt_lane_order_config_file,
                                                                tgt_lane_order_config_section)

    exp_paths = ExperimentPaths(
        arbiter, 
        laser_config_section, 
        ring_config_section, 
        init_lane_order_config_section,
        tgt_lane_order_config_section,
        results_dir,
        f'sweep_compare',
        arbiter_compare,
    )

    # file name to save log file
    log_fpath: str = exp_paths.get_filepath(
        filename_suffix=sweep_filename_suffix(num_laser_swaps, num_ring_swaps), file_extension='log')
    setup_logger(log_fpath, verbose)
    # setup_logger(exp_paths.get_filepath(
    #     filename_suffix=sweep_filename_suffix(num_laser_swaps, num_ring_swaps), file_extension='log'), verbose)

    sweep_csv_fname = exp_paths.get_filepath(
        filename_suffix=sweep_filename_suffix(num_laser_swaps, num_ring_swaps), file_extension='csv')

    df_experiment = _sweep_compare(
        laser_design_sweep_params,
        ring_design_sweep_params,
        init_lane_order_params,
        tgt_lane_order_params,
        arbiter,
        arbiter_compare,
        num_laser_swaps,
        num_ring_swaps,
        nprocs,
    )
    
    # pretty print dataframe using tabulate
    df_experiment_tbl = df_experiment.copy()

    # df_experiment has a MultiIndex column with two levels of labels,
    # we want to display the second level of labels 
    df_experiment_tbl.columns = df_experiment_tbl.columns.get_level_values(1)
    # print(tabulate(df_experiment_tbl, headers='keys', tablefmt='psql'))

    # save experiment dataframe to file
    # df_experiment.to_csv(sweep_csv_fname, sep='\t', index=True, header=df_experiment.columns.levels[1].tolist())
    # this seem to export multi-level header well enough
    df_experiment.to_csv(sweep_csv_fname, sep='\t', index=True)

    # df_read = pd.read_csv(sweep_csv_fname, sep='\t', header=[0, 1], index_col=0)
    # from pandas.testing import assert_frame_equal
    # assert_frame_equal(df_experiment, df_read, check_exact=False)

    logging.info(f"Log: {log_fpath}")
    logging.info(f"Result CSV: {sweep_csv_fname}")

# Run a portion of sweep from the generated json sweep config
# This is useful when the sweep is too large to run at once (e.g., sensitivity analysis)
def sweep_ptn(
    nprocs, 
    json_path: Path,
    ptn_start_idx: int,
    ptn_end_idx: int,
    results_dir,
    verbose,
):

    # load json file
    sweep_record : SimSweepRecord = SimSweepRecord.from_json(json_path)
     
    # unwrap experiment parameters 
    # base params
    laser_config_file = sweep_record.laser_config_file
    laser_config_section = sweep_record.laser_config_section
    ring_config_file = sweep_record.ring_config_file
    ring_config_section = sweep_record.ring_config_section
    init_lane_order_config_file = sweep_record.init_lane_order_config_file
    init_lane_order_config_section = sweep_record.init_lane_order_config_section
    tgt_lane_order_config_file = sweep_record.tgt_lane_order_config_file
    tgt_lane_order_config_section = sweep_record.tgt_lane_order_config_section
    arbiter = sweep_record.arbiter_str
    num_laser_swaps = sweep_record.num_laser_swaps
    num_ring_swaps = sweep_record.num_ring_swaps

    # This part isn't necessary for this    
    # # define experiment parameters
    # laser_design_sweep_params : Union[LaserDesignParams, List[LaserDesignParams]] = get_design_params(laser_config_file,
    #                                                                                                    laser_config_section)
    # ring_design_sweep_params : Union[RingDesignParams, List[RingDesignParams]] = get_design_params(ring_config_file,
    #                                                                                                 ring_config_section)
    #
    # if not _check_sweep_on_list(laser_design_sweep_params, ring_design_sweep_params):
    #     raise ValueError(f"Cannot sweep without variations. \
    #                         Laser design parameters {laser_design_sweep_params} \
    #                         Ring design parameters {ring_design_sweep_params}")
    #
    # # if either one of them is a list, then wrap around params as list if either of them is a singleton
    # # to simplify the later code
    # if isinstance(laser_design_sweep_params, LaserDesignParams):
    #     laser_design_sweep_params = [laser_design_sweep_params]
    # if isinstance(ring_design_sweep_params, RingDesignParams):
    #     ring_design_sweep_params = [ring_design_sweep_params]
    
    # Skip validation at your risk
    # LaserSweepConfigYAML.validator(laser_design_sweep_params, num_laser_swaps)
    # RingSweepConfigYAML.validator(ring_design_sweep_params, num_ring_swaps)

    # # define lane order parameters
    # init_lane_order_params : LaneOrderParams = get_design_params(init_lane_order_config_file,
    #                                                              init_lane_order_config_section)
    # tgt_lane_order_params : LaneOrderParams = get_design_params(tgt_lane_order_config_file,
    #                                                             tgt_lane_order_config_section)

    # raise exception if the start and end indices are out of bounds
    if ptn_start_idx < 0 or ptn_start_idx >= len(sweep_record.laser_design_sweep_params):
        raise ValueError(f"ptn_start_idx {ptn_start_idx} out of bounds")
    if ptn_end_idx < 0 or ptn_end_idx > len(sweep_record.laser_design_sweep_params):
        raise ValueError(f"ptn_end_idx {ptn_end_idx} out of bounds")
    if ptn_start_idx >= ptn_end_idx:
        raise ValueError(f"ptn_start_idx {ptn_start_idx} should be less than ptn_end_idx {ptn_end_idx}")
    
    laser_design_sweep_params = sweep_record.laser_design_sweep_params[ptn_start_idx:ptn_end_idx]
    ring_design_sweep_params = sweep_record.ring_design_sweep_params[ptn_start_idx:ptn_end_idx]
    init_lane_order_params = sweep_record.init_lane_order_params
    tgt_lane_order_params = sweep_record.tgt_lane_order_params

    exp_paths = ExperimentPaths(
        arbiter, 
        laser_config_section, 
        ring_config_section, 
        init_lane_order_config_section,
        tgt_lane_order_config_section,
        results_dir,
        'sweep',
    )

    # file name to save log file
    setup_logger(exp_paths.get_filepath(
        filename_suffix=sweep_ptn_filename_suffix(num_laser_swaps, num_ring_swaps, [ptn_start_idx, ptn_end_idx]), file_extension='log'), verbose)

    sweep_csv_fname = exp_paths.get_filepath(
        filename_suffix=sweep_ptn_filename_suffix(num_laser_swaps, num_ring_swaps, [ptn_start_idx, ptn_end_idx]), file_extension='csv')

    df_experiment = _sweep(
        laser_design_sweep_params,
        ring_design_sweep_params,
        init_lane_order_params,
        tgt_lane_order_params,
        arbiter,
        num_laser_swaps,
        num_ring_swaps,
        nprocs,
    )
    
    # pretty print dataframe using tabulate
    df_experiment_tbl = df_experiment.copy()

    # df_experiment has a MultiIndex column with two levels of labels,
    # we want to display the second level of labels 
    df_experiment_tbl.columns = df_experiment_tbl.columns.get_level_values(1)
    # print(tabulate(df_experiment_tbl, headers='keys', tablefmt='psql'))

    # save experiment dataframe to file
    # df_experiment.to_csv(sweep_csv_fname, sep='\t', index=True, header=df_experiment.columns.levels[1].tolist())
    # this seem to export multi-level header well enough
    df_experiment.to_csv(sweep_csv_fname, sep='\t', index=True)

    # df_read = pd.read_csv(sweep_csv_fname, sep='\t', header=[0, 1], index_col=0)
    # from pandas.testing import assert_frame_equal
    # assert_frame_equal(df_experiment, df_read, check_exact=False)


def plot_sweep(
    num_laser_swaps,
    num_ring_swaps,
    arbiter, 
    laser_config_file,
    laser_config_section, 
    ring_config_file,
    ring_config_section, 
    init_lane_order_config_file,
    init_lane_order_config_section,
    tgt_lane_order_config_file,
    tgt_lane_order_config_section,
    results_dir,
    plot_x_axis,
    plot_y_axis,
):
    exp_paths = ExperimentPaths(
        arbiter, 
        laser_config_section, 
        ring_config_section, 
        init_lane_order_config_section,
        tgt_lane_order_config_section,
        results_dir,
        'sweep',
    )

    # file name to save log file
    setup_logger(exp_paths.get_filepath(
        filename_suffix=sweep_filename_suffix(num_laser_swaps, num_ring_swaps), file_extension='log'), verbose=False)

    sweep_csv_fname = exp_paths.get_filepath(
        filename_suffix=sweep_filename_suffix(num_laser_swaps, num_ring_swaps), file_extension='csv')

    sweep_fig_fname_png = exp_paths.get_filepath(
        filename_suffix=sweep_filename_suffix(num_laser_swaps, num_ring_swaps), file_extension='png')

    sweep_fig_fname_pdf = exp_paths.get_filepath(
        filename_suffix=sweep_filename_suffix(num_laser_swaps, num_ring_swaps), file_extension='pdf')

    # save experiment dataframe to file
    df_experiment = pd.read_csv(sweep_csv_fname, sep='\t', header=[0, 1], index_col=0)

    # # plot sweep results using ShmooPlotter
    # fig_template = FigureTemplate.draw(nrows=1, ncols=3,
    #                                    figsize=(24, 6),
    #                                    properties={'tight_layout': True})
    # # fig_template.set_fig_properties({'suptitle': 'Laser Variation Sweep'})
    # ShmooPlotter(axes=fig_template.ax[0]).plot(df_experiment=df_experiment,
    #                                            # x_axis='fsr_mean',
    #                                            # y_axis='tuning_range_mean',
    #                                            x_axis=plot_x_axis,
    #                                            y_axis=plot_y_axis,
    #                                            z_axis='failure_in_time',
    #                                            annotate=False,
    #                                            cbar=True)
    # ShmooPlotter(axes=fig_template.ax[1]).plot(df_experiment=df_experiment,
    #                                            # x_axis='fsr_mean',
    #                                            # y_axis='tuning_range_mean',
    #                                            x_axis=plot_x_axis,
    #                                            y_axis=plot_y_axis,
    #                                            z_axis='failure_zero_lock',
    #                                            annotate=False,
    #                                            cbar=True)
    # ShmooPlotter(axes=fig_template.ax[2]).plot(df_experiment=df_experiment,
    #                                            # x_axis='fsr_mean',
    #                                            # y_axis='tuning_range_mean',
    #                                            x_axis=plot_x_axis,
    #                                            y_axis=plot_y_axis,
    #                                            z_axis='failure_duplicate_lock',
    #                                            annotate=False,
    #                                            cbar=True)

    # plot sweep results using ShmooPlotter
    fig_template = FigureTemplate.draw(nrows=1, ncols=1,
                                       figsize=(8, 6),
                                       properties={'tight_layout': True})

    ShmooPlotter(axes=fig_template.ax).plot(
        df_experiment=df_experiment,
        x_axis=plot_x_axis,
        y_axis=plot_y_axis,
        z_axis='failure_in_time',
        annotate=False,
        cbar=True,
        cmap='viridis',
    )

    # save figure to file
    fig_template.save(sweep_fig_fname_pdf)
    fig_template.save(sweep_fig_fname_png)


def plot_sweep_compare(
    num_laser_swaps,
    num_ring_swaps,
    arbiter, 
    arbiter_compare,
    laser_config_file,
    laser_config_section, 
    ring_config_file,
    ring_config_section, 
    init_lane_order_config_file,
    init_lane_order_config_section,
    tgt_lane_order_config_file,
    tgt_lane_order_config_section,
    results_dir,
    plot_x_axis,
    plot_y_axis,
):
    exp_paths = ExperimentPaths(
        arbiter, 
        laser_config_section, 
        ring_config_section, 
        init_lane_order_config_section,
        tgt_lane_order_config_section,
        results_dir,
        'sweep_compare',
        arbiter_compare,
    )

    # file name to save log file
    setup_logger(exp_paths.get_filepath(
        filename_suffix=sweep_filename_suffix(num_laser_swaps, num_ring_swaps), file_extension='log'), verbose=False)

    sweep_csv_fname = exp_paths.get_filepath(
        filename_suffix=sweep_filename_suffix(num_laser_swaps, num_ring_swaps), file_extension='csv')

    sweep_fig_fname_png = exp_paths.get_filepath(
        filename_suffix=sweep_filename_suffix(num_laser_swaps, num_ring_swaps), file_extension='png')

    sweep_fig_fname_pdf = exp_paths.get_filepath(
        filename_suffix=sweep_filename_suffix(num_laser_swaps, num_ring_swaps), file_extension='pdf')

    # save experiment dataframe to file
    df_experiment = pd.read_csv(sweep_csv_fname, sep='\t', header=[0, 1], index_col=0)

    # # plot sweep results using ShmooPlotter
    # fig_template = FigureTemplate.draw(nrows=1, ncols=3,
    #                                    figsize=(24, 6),
    #                                    properties={'tight_layout': True})
    # # fig_template.set_fig_properties({'suptitle': 'Laser Variation Sweep'})
    # ShmooPlotter(axes=fig_template.ax[0]).plot(df_experiment=df_experiment,
    #                                            # x_axis='fsr_mean',
    #                                            # y_axis='tuning_range_mean',
    #                                            x_axis=plot_x_axis,
    #                                            y_axis=plot_y_axis,
    #                                            z_axis='failure_in_time',
    #                                            annotate=False,
    #                                            cbar=True)
    # ShmooPlotter(axes=fig_template.ax[1]).plot(df_experiment=df_experiment,
    #                                            # x_axis='fsr_mean',
    #                                            # y_axis='tuning_range_mean',
    #                                            x_axis=plot_x_axis,
    #                                            y_axis=plot_y_axis,
    #                                            z_axis='failure_zero_lock',
    #                                            annotate=False,
    #                                            cbar=True)
    # ShmooPlotter(axes=fig_template.ax[2]).plot(df_experiment=df_experiment,
    #                                            # x_axis='fsr_mean',
    #                                            # y_axis='tuning_range_mean',
    #                                            x_axis=plot_x_axis,
    #                                            y_axis=plot_y_axis,
    #                                            z_axis='failure_duplicate_lock',
    #                                            annotate=False,
    #                                            cbar=True)

    # plot sweep results using ShmooPlotter
    fig_template = FigureTemplate.draw(nrows=1, ncols=1,
                                       figsize=(8, 6),
                                       properties={'tight_layout': True})

    ShmooPlotter(axes=fig_template.ax).plot(
        df_experiment=df_experiment,
        x_axis=plot_x_axis,
        y_axis=plot_y_axis,
        z_axis='failure_in_time',
        annotate=False,
        cbar=True,
        cmap='viridis',
    )

    # save figure to file
    fig_template.save(sweep_fig_fname_pdf)
    fig_template.save(sweep_fig_fname_png)


def record(
    json_path,
    num_laser_swaps, 
    num_ring_swaps,
    arbiter, 
    laser_config_file, 
    laser_config_section, 
    ring_config_file, 
    ring_config_section, 
    init_lane_order_config_file,
    init_lane_order_config_section,
    tgt_lane_order_config_file,
    tgt_lane_order_config_section,
    results_dir,
    overwrite_json,
    verbose,
):
    """
    record function
    """
    # define experiment parameters
    laser_design_params : LaserDesignParams = get_design_params(laser_config_file,
                                                                laser_config_section)
    ring_design_params : RingDesignParams = get_design_params(ring_config_file,
                                                              ring_config_section)

    init_lane_order_params : LaneOrderParams = get_design_params(init_lane_order_config_file,
                                                                 init_lane_order_config_section)
    tgt_lane_order_params : LaneOrderParams = get_design_params(tgt_lane_order_config_file,
                                                                tgt_lane_order_config_section)

    # verify experiment parameters
    # if parameters related to variations are 0, then it should be a single experiment
    if laser_design_params.grid_variance == 0 and laser_design_params.grid_max_offset == 0:
        if num_laser_swaps > 1:
            raise ValueError(f"Number of laser swaps should be 1 for a single experiment. \
                                Laser design parameters {laser_design_params}")
    
    if ring_design_params.fsr_variance == 0 and ring_design_params.tuning_range_variance == 0:
        if num_ring_swaps > 1:
            raise ValueError(f"Number of ring swaps should be 1 for a single experiment. \
                                Ring design parameters {ring_design_params}")


    exp_paths = ExperimentPaths(
        arbiter, 
        laser_config_section, 
        ring_config_section, 
        init_lane_order_config_section,
        tgt_lane_order_config_section,
        results_dir,
        'record',
    )

    # file name to save log file
    setup_logger(exp_paths.get_filepath(
        filename_suffix=run_filename_suffix(num_laser_swaps, num_ring_swaps), file_extension='log'), verbose=verbose)

    # print log header
    print_run_header(
        laser_config_file, 
        laser_config_section,
        ring_config_file,
        ring_config_section, 
        init_lane_order_config_file,
        init_lane_order_config_section,
        tgt_lane_order_config_file,
        tgt_lane_order_config_section,
        laser_design_params, 
        ring_design_params, 
        init_lane_order_params,
        tgt_lane_order_params,
        arbiter,
    )

    # log experiment start
    logging.info(str_print("Experiment Start"))
    logging.info(pad_print())

    sim_replays = run_and_record(
        laser_design_params, 
        ring_design_params, 
        init_lane_order_params,
        tgt_lane_order_params,
        arbiter, 
        num_laser_swaps, 
        num_ring_swaps,
    )

    # log experiment end
    logging.info(pad_print())
    logging.info(str_print("Experiment End"))
    logging.info(pad_print())

    for i, sim_replay in enumerate(sim_replays):
        # Overwrite only used for the first record; otherwise, append
        if i == 0:
            sim_replay.record_json(json_path=json_path, overwrite=overwrite_json)
        else:
            sim_replay.record_json(json_path=json_path, overwrite=False)


def replay(
    json_path: Path,
    arbiter_override,
    verbose,
):

    sim_replays : List[SimReplay] = SimReplay.from_json(json_path)

    # file name to save log file
    setup_logger(json_path.with_suffix('.log'), verbose=verbose)

    results_collect = []
    for sim_replay in sim_replays:
        if arbiter_override:
            # run the original arbiter run before override
            run_replay(*sim_replay.astuple())

            args_override = sim_replay._convert_to_dict()
            args_override['arbiter_str'] = arbiter_override
            sim_replay = SimReplay._convert_from_dict(args_override)

        result = run_replay(*sim_replay.astuple())
        results_collect.append(result)
        if result:
            logger.info(f"Replay successful (arbiter: {sim_replay.arbiter_str})")
        else:
            logger.info(f"Replay failed (arbiter: {sim_replay.arbiter_str})")
            sys.exit(1)

    if logger.isEnabledFor(_VERBOSE):
        from art import text2art
        if all(results_collect):
            logger.info(f"\n{text2art('REPLAY SUCCESS')}")
        else:
            logger.info(f"\n{text2art('REPLAY FAIL')}")
            sys.exit(1)
