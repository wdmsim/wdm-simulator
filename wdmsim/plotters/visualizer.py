

import enum
from abc import ABC, abstractmethod
from typing import List, Tuple, Union, Dict

import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib import pyplot as plt
from matplotlib.axes import Axes

from wdmsim.models.laser_grid import LaserGrid
from wdmsim.models.ring_row import RingRxWDMRow, RingRxWDM

from wdmsim.utils.snapshot import Snapshot
from wdmsim.stats.lock_code_stat import LockCodeStat


class BaseVis(ABC):
    """An abstract class to represent an object visualizer.
    A template class for transforming a data object into a visual representation fit for pyplot-style plotting.
    This class intends to present a compact and transferrable format for visualizing data.
    The return object should be a list of matplotlib.pyplot objects to be supplied to a corresponding plotters

    """
    def infrared(self, cnum: Union[int, float]):
        """Returns a color for a given infrared value.
        The color palette is a list of colors that can be used to represent different data.

        :param cnum: The index of the color to be returned, usually normalized to 1
        :return: The color at the index of the color palette
        """
        return plt.cm.get_cmap('plasma')(cnum)

    @abstractmethod
    def draw(self, axes: Axes):
        """draw the object
        """
        pass


class LaserGridVis(BaseVis):
    """A class to represent a laser grid visualizer.

    https://matplotlib.org/stable/gallery/text_labels_and_annotations/fancyarrow_demo.html
    """
    def __init__(self, laser_grid: LaserGrid):
        """Initialize the laser grid visualizer.
        """
        self.laser_grid = laser_grid

        self.wavelengths = laser_grid.wavelengths
        self.arrowprops = lambda i: dict(arrowstyle="<-", connectionstyle="arc3", color=self.infrared(i), linewidth=1.5)

    def draw(self, axes: Axes):
        """Draw the laser grid visualizer.
        It draws an arrow shape at each wavelength grid
        """
        # laser representation with index as a subscript of greek lambda letter
        laser_repr = lambda idx : f"$\lambda_{{{idx}}}$" + f"\n{self.wavelengths[idx]*1e9:.1f}"

        y_start, y_end = 0.75, 1.5

        # draw the laser grid
        for idx, wavelength in enumerate(self.wavelengths):
            axes.annotate(laser_repr(idx), xy=(wavelength, y_start), xytext=(wavelength, y_end), \
                    arrowprops=self.arrowprops(i=idx/len(self.wavelengths)), \
                    horizontalalignment='center', verticalalignment='center', fontsize=6)


class RingRxWDMVis(BaseVis):
    """A class to represent a ring receiver WDM visualizer.

    :param ring_rx_wdm: the ring receiver WDM object
    :type ring_rx_wdm: RingRxWDM
    :param idx: the index of the ring receiver WDM object
    :type idx: int
    :param cnum: the index of the color to be used
    :type cnum: Union[int, float]
    """
    def __init__(self, ring_rx_wdm: RingRxWDM, idx: int, cnum: Union[int, float]):
        """Initialize the ring receiver WDM visualizer.
        """

        self.ring_rx_wdm = ring_rx_wdm

        self.curr_wavelength = ring_rx_wdm.curr_wavelength
        self.fsr = ring_rx_wdm.fsr
        self.fwhm = ring_rx_wdm.wavelength/2e4

        self.idx = idx
        self.cnum = cnum

        self.wavelength = ring_rx_wdm.wavelength
        self.tuning_range = ring_rx_wdm.tuning_range

    def lorentzian(self, x, x0, gamma):
        """Lorentzian function
        """
        # return lorentzian function with max value 1, width gamma, and center x0
        return 1/(1+((x-x0)/gamma)**2)

    def draw(self, axes: Axes, verbose):
        """Draw the ring receiver WDM visualizer.
        """
        xlim = axes.get_xlim()
        x = np.linspace(xlim[0], xlim[1], 10000)
        y = self.lorentzian(x, self.curr_wavelength, self.fwhm) + \
            self.lorentzian(x, self.curr_wavelength + self.fsr, self.fwhm) + \
            self.lorentzian(x, self.curr_wavelength - self.fsr, self.fwhm)

        # plot the lorentzian
        axes.plot(x, y, color=self.infrared(self.cnum))

        # annotate the current wavelength without arrows
        axes.annotate(f"$\lambda_{{{self.idx}}}$", xy=(self.curr_wavelength, 0.25),
                      xytext=(self.curr_wavelength, 0.25),
                      horizontalalignment='center', verticalalignment='center', fontsize=6)

        axes.annotate(f"$\lambda_{{{self.idx}}}$", xy=(self.curr_wavelength + self.fsr, 0.25),
                      xytext=(self.curr_wavelength + self.fsr, 0.25),
                      horizontalalignment='center', verticalalignment='center', fontsize=6)

        axes.annotate(f"$\lambda_{{{self.idx}}}$", xy=(self.curr_wavelength - self.fsr, 0.25),
                      xytext=(self.curr_wavelength - self.fsr, 0.25),
                      horizontalalignment='center', verticalalignment='center', fontsize=6)

        # draw a horizontal arrow about its tuning range
        if verbose:
            # tuning_range_arrow_y_start = 0.25
            tuning_range_arrow_y_start = 0.25
            tuning_range_arrow_linewidth = 1.0
            # tuning_range_arrow_linewidth = 0.5
            # arrow_ngroup = 3
            arrow_ngroup = 4

            tune_start = [
                    self.wavelength - self.tuning_range/2 - self.fsr,
                    self.wavelength - self.tuning_range/2,
                    self.wavelength - self.tuning_range/2 + self.fsr,
                    ]

            tune_end = [
                    self.wavelength + self.tuning_range/2 - self.fsr,
                    self.wavelength + self.tuning_range/2,
                    self.wavelength + self.tuning_range/2 + self.fsr,
                    ]
            tuning_range_arrow_height = tuning_range_arrow_y_start + 0.25*(self.idx%arrow_ngroup)
            for i in range(3):
                axes.annotate("", xy=(tune_start[i], tuning_range_arrow_height),
                              xytext=(tune_end[i], tuning_range_arrow_height),
                              arrowprops=dict(arrowstyle="<->", 
                                              connectionstyle="arc3", 
                                              color=self.infrared(self.cnum),
                                              linewidth=tuning_range_arrow_linewidth,
                                              linestyle='dashed'),
                              horizontalalignment='center', verticalalignment='center', fontsize=6)


class RingRxWDMRowVis(BaseVis):
    """A class to represent a ring row visualizer.

    :param ring_wdm_row: the ring row object
    """
    def __init__(self, ring_wdm_row: RingRxWDMRow):
        """Initialize the ring row visualizer.
        """
        self.ring_wdm_row = ring_wdm_row

    def draw(self, axes: Axes, verbose=True):
        """Draw the ring row visualizer.
        """
        for idx, ring in enumerate(self.ring_wdm_row.rings):
            RingRxWDMVis(ring_rx_wdm=ring, idx=idx, cnum=idx/len(self.ring_wdm_row.rings)).draw(axes, verbose)


class ArbiterStateVis(BaseVis):
    """A class to represent arbiter states
    It annotates the state as a text box and draws an arrow for each target slice if any

    :param arbiter_state: the arbiter state
    :type arbiter_state: dict[str, str]
    """
    def __init__(self, arbiter_state: Dict[str, str]):
        """Initialize the arbiter state visualizer.
        """
        self.arbiter_state = arbiter_state

    def draw(self, axes: Axes, system_clock: Union[int, float], ring_wdm_row: RingRxWDMRow):
        """Draw the arbiter state visualizer.
        Draw the following:
        - the state as a text box
        - the target slice as an arrow at wavelengths

        :param axes: the axes to draw on
        :type axes: Axes
        :param system_clock: the system clock
        :type system_clock: Union[int, float]
        :param ring_wdm_row: the ring row
        :type ring_wdm_row: RingRxWDMRow
        """
     
        # set the string description of the system clock and arbiter state
        description = f"System clock: {system_clock:.2f} \nArbiter state: {self.arbiter_state['state_name']}"
        # add to description if the arbiter state dictionary has a target_slices key
        if 'target_slices' in self.arbiter_state.keys():
            description += f"\nTarget slices: {self.arbiter_state['target_slices']}"

        # draw the text box at top right corner with arbiter state description
        axes.text(0.95, 0.95, description,
            horizontalalignment='right',
            verticalalignment='top',
            transform=axes.transAxes,
            fontsize=8,
            bbox=dict(facecolor='white', alpha=0.5, edgecolor='none', boxstyle='round,pad=0.5')
        )

        # TODO: find a better way of illustrating the target slices
        # # if arbiter state dictionary has a target_slices key, draw an arrow for each target slice
        # if 'target_slices' in self.arbiter_state.keys():
        #     # get the target slices
        #     target_slices = self.arbiter_state['target_slices']
        #     # get the current wavelengths of the ring row
        #     curr_wavelengths = [ring.curr_wavelength for ring in ring_wdm_row.rings]
        #     # get the wavelengths of the target slices
        #     target_wavelengths = [curr_wavelengths[slice] for slice in target_slices]
        #     # draw a bold arrow for each target slice
        #     for target_wavelength in target_wavelengths:
        #         axes.annotate('', xy=(target_wavelength+2e-10, 0.5), xytext=(target_wavelength-1e-10, 0.5),
        #                       arrowprops=dict(arrowstyle='->', linewidth=2, color='black'))
        #



class SnapshotVis(BaseVis):
    """A class to represent a simulation snapshot visualizer.
    A simulator snapshot would include a laser grid and ring row status at a given time.

    :param laser_grid: the laser grid object
    :type laser_grid: LaserGrid
    :param ring_wdm_row: the ring row object
    :type ring_wdm_row: RingRxWDMRow
    :param arbiter_state: the arbiter state
    :type arbiter_state: dict[str, str]
    :param system_clock: the system clock
    :type system_clock: Union[int, float]
    """
    def __init__(self, snapshot: Snapshot):
        """Initialize the simulation snapshot visualizer.
        """
        self.snapshot      = snapshot
        self.laser_grid    = snapshot.laser_grid
        self.ring_wdm_row  = snapshot.ring_wdm_row
        self.system_clock  = snapshot.system_clock
        self.arbiter_state = snapshot.arbiter_state
        
    def draw(self, axes: Axes):
        """Draw the simulation snapshot visualizer.
        """
        # instantiate the laser grid, ring row visualizer and arbiter state visualizer
        laser_grid_vis = LaserGridVis(self.laser_grid)
        ring_row_vis = RingRxWDMRowVis(self.ring_wdm_row)
        arbiter_state_vis = ArbiterStateVis(self.arbiter_state)
        
        # draw the laser grid, ring row visualizer and arbiter state visualizer
        laser_grid_vis.draw(axes)
        ring_row_vis.draw(axes, verbose=True)
        arbiter_state_vis.draw(axes, self.system_clock, self.ring_wdm_row)
        

class StatisticsVis(BaseVis):
    """A class to represent a statistics visualizer.
    Lock code statistics has a specific schema that can be accessed through [] operator.
    slice-level statistics (lock_code_stat['slice']) and summary statistics (lock_code_stat['summary'])
    are available for visualization.
    
    :param lock_code_stat: the lock code statistics
    :type lock_code_stat: LockCodeStat
    """
    def __init__(self, lock_code_stat: LockCodeStat):
        self.lock_code_stat = lock_code_stat

    def draw(self, axes: Axes, plot_slice: bool, plot_summary: bool):

        # get statistics and transform to dataframe
        df_slice_stat = pd.DataFrame.from_dict(self.lock_code_stat['slice'])
        df_summary_stat = pd.DataFrame.from_dict(self.lock_code_stat['summary'])

        # concatenate the slice-level and summary statistics
        df_all_stat = pd.concat([df_slice_stat, df_summary_stat], axis=0)
        
        # set df_stat based on plot_slice and plot_summary
        if plot_slice and plot_summary:
            df_stat = df_all_stat
            x_label = 'Slice and Summary'
        elif plot_slice:
            df_stat = df_slice_stat
            x_label = 'Slice'
        elif plot_summary:
            df_stat = df_summary_stat
            x_label = 'Summary'
        else:
            raise ValueError("plot_slice and plot_summary cannot both be False")

        # melt the dataframe to long format
        df_melted = df_stat.melt(var_name=x_label, value_name='Lock Code')

        # plot using seaborn violinplot
        sns.violinplot(x=x_label, y='Lock Code', data=df_melted, ax=axes, inner="stick", scale="count", bw=.15)

        # axes.violinplot(dataset=self.lock_code_stat)

