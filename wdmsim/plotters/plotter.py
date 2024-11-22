"""
This module contains the Plotter class, which is used to plot the results of the
visualization.

Note
----
Main confusion of matplotlib.Axes is that a single graph instance is a class instance of AxesSubplot,
a single axis is a class instance of Axis, and a figure contains multiple axes by a list and 
typically referred to as "ax".
>>> fig, ax = plt.subplots()
>>> type(ax)
>>> array([<matplotlib.axes._subplots.AxesSubplot object at 0x7f8b9c0b7a90>],
            <matplotlib.axes._subplots.AxesSubplot object at 0x7f8b9c0b7a90>]])
>>> type(ax[0])
>>> <matplotlib.axes._subplots.AxesSubplot object at 0x7f8b9c0b7a90>
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple, Union

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.text import Text
from matplotlib.ticker import AutoMinorLocator, FormatStrFormatter, FuncFormatter, LinearLocator
from matplotlib.colors import LogNorm, SymLogNorm

from wdmsim.plotters.visualizer import BaseVis, SnapshotVis, StatisticsVis
from wdmsim.utils.snapshot import Snapshot
from wdmsim.stats.lock_code_stat import LockCodeStat


class FigureTemplate:
    """Figure Canvas class
    This class holds a canvas for matplotlib figures.
    It contains the boilerplate matplotlib codes for fig canvas initialization 
    and various helper methods to be reused in multiple places
    
    Attributes:
        fig: Figure object
        ax: A group of axes objects in a list or a single axes object
        num_subplots: number of subplots
    """
    def __init__(self, fig: Figure, ax: Union[Axes, List[Axes]], properties):
        """
        :param fig: Figure object
        :param ax: A group of axes objects in a list or a single axes object
        """
        self.fig = fig
        self.ax = ax
        self.num_subplots = len(ax) if isinstance(ax, list) else 1
        self.properties = properties
        
    def set_fig_properties(self, properties: dict):
        """Sets the figure properties
        :param properties: figure properties
        """
        for key, value in properties.items():
            if key == "suptitle":
                self.fig.suptitle(value)
            elif key == "supxlabel":
                self.fig.supxlabel(value)
            elif key == "supylabel":
                self.fig.supylabel(value)
            else:
                pass

    def show(self):
        plt.show()

    def save(self, path: str):
        self.fig.savefig(path)

    def set_suptitle(self, title: str):
        """Sets the super title
        :param title: title
        """
        self.fig.suptitle(title)

    def set_supxlabel(self, xlabel: str):
        """Sets the super x label
        :param xlabel: x label
        """
        self.fig.supxlabel(xlabel)

    def set_supylabel(self, ylabel: str):
        """Sets the super y label
        :param ylabel: y label
        """
        self.fig.supylabel(ylabel)

    def set_xlim(self, xrange: List[float]):
        """Sets the x limit
        :param xmin: minimum x
        :param xmax: maximum x
        :param idx_x: x index
        :param idx_y: y index
        """
        for ax in self.ax:
            ax.set_xlim(xrange[0], xrange[1])

    def handle(self) -> Tuple[Figure, Union[Axes, List[Axes]]]:
        return self.fig, self.ax

    def get_axes(self, idx_x: int, idx_y: int) -> Axes:
        """Returns the axes object at the given index
        :param idx_x: x index
        :param idx_y: y index
        :return: axes object
        """
        if self.num_subplots == 1:
            return self.ax
        else:
            # return self.ax[self._to_subplot_idx(self.num_subplots, idx_x, idx_y)]
            return self.ax[idx_x, idx_y]

    def set_axes(self, axes: Axes, idx_x: int, idx_y: int):
        """Sets the axes object at the given index
        :param axes: axes object
        :param idx_x: x index
        :param idx_y: y index
        """
        if self.num_subplots == 1:
            self.ax = axes
        else:
            # self.ax[self._to_subplot_idx(self.num_subplots, idx_x, idx_y)] = axes
            self.ax[idx_x, idx_y] = axes

    def reshape(self, dim_x: int, dim_y: int):
        """Reshapes the figure canvas
        :param dim_x: x dimension
        :param dim_y: y dimension
        """
        assert dim_x * dim_y == self.num_subplots, "The number of subplots must be equal to dim_x * dim_y"
        self.ax.reshape(dim_x, dim_y)
        
    def _to_subplot_idx(self, num_subplots:int, idx_x: int, idx_y: int) -> int:
        """Converts the index to a matplotlib-style three digit number
        :param num_subplots: number of subplots
        :param idx_x: x index
        :param idx_y: y index
        :return: matplotlib-style three digit number
        """
        return num_subplots * 100 + idx_x * 10 + idx_y

    @classmethod
    def draw(cls,
             nrows: int,
             ncols: int,
             figsize: tuple,
             properties: dict = {}) -> 'FigureTemplate':
        """draw a figure canvas
        """
        fig = plt.figure(figsize=figsize, **properties)
        nsubplots = nrows * ncols
        if nsubplots > 1:
            ax = fig.subplots(nrows, ncols)
        else:
            ax = fig.subplots()
        return cls(fig, ax, properties)

    @classmethod
    def draw_simple(cls,
                    figsize: tuple) -> 'FigureTemplate':
        """Initialize the base plotter from properties
        """
        fig = plt.figure(figsize=figsize)
        ax = fig.subplots()
        return cls(fig, ax, {})
    

class BasePlotter(ABC):
    """Base plotter class
    This class defines the basic structure of a plotter to templatize the
    plotting process. It defines the abstract methods that need to be
    implemented by the child classes. It also includes some helper methods.
    """
    def __init__(self, axes: Axes, properties: Optional[dict] = None):
        """Initialize the plotter
        """
        self.axes = axes
        self.properties = properties

        # set default properties 
        self.set_default_properties()

        # set axes properties (overrides default)
        if self.properties:
            self.set_axes_properties(self.properties)

    def set_axes_properties(self, properties: dict):
        """Set the properties of each axes
        """
        # TODO: trim some of these
        for key, value in properties.items():
            if key == "title":
                self.axes.set_title(value)
            elif key == "xlabel":
                self.axes.set_xlabel(value)
            elif key == "ylabel":
                self.axes.set_ylabel(value)
            elif key == "xlim":
                self.axes.set_xlim(value)
            elif key == "ylim":
                self.axes.set_ylim(value)
            elif key == "xticks":
                if isinstance(value, list):
                    self.axes.set_xticks(value)
                else:
                    pass
            elif key == "yticks":
                if isinstance(value, list):
                    self.axes.set_yticks(value)
                else:
                    pass
            elif key == "xticklabels":
                if isinstance(value, list):
                    self.axes.set_xticklabels(value)
                else:
                    pass
            elif key == "yticklabels":
                if isinstance(value, list):
                    self.axes.set_yticklabels(value)
                else:
                    pass
            elif key == "xscale":
                self.axes.set_xscale("linear")
            elif key == "yscale":
                self.axes.set_yscale("linear")
            elif key == "invert_xaxis":
                if value is True:
                    self.axes.invert_xaxis()
            elif key == "invert_yaxis":
                if value is True:
                    self.axes.invert_yaxis()
            elif key == "grid":
                self.axes.grid(value)
            elif key == "legend":
                if value is True:
                    self.axes.legend()
                else:
                    pass
            elif key == "legend_loc":
                self.axes.legend(loc=value)
            elif key == "legend_bbox_to_anchor":
                self.axes.legend(bbox_to_anchor=value)
            elif key == "legend_ncol":
                self.axes.legend(ncol=value)
            elif key == "legend_fontsize":
                self.axes.legend(fontsize=value)
            elif key == "legend_frameon":
                self.axes.legend(frameon=value)
            elif key == "legend_framealpha":
                self.axes.legend(framealpha=value)
            elif key == "legend_facecolor":
                self.axes.legend(facecolor=value)
            elif key == "legend_edgecolor":
                self.axes.legend(edgecolor=value)
            elif key == "legend_title":
                self.axes.legend(title=value)
            elif key == "legend_title_fontsize":
                self.axes.legend(title_fontsize=value)
        
    @abstractmethod
    def set_default_properties(self):
        """Set the default properties for the plotter axes
        Place the default properties setup here to record the first cut design of the plotter
        """
        pass

    @abstractmethod
    def plot(self):
        """Plot the data
        This method is used to plot the data. It is an abstract method that
        needs to be implemented by the child classes.
        """
        pass


class SnapshotPlotter(BasePlotter):
    """Snapshot plotter
    This class draws a snapshot from simulation runs and depicts a dynamic update of system status at each time step

    """
    def set_default_properties(self):
        """Set the default properties for the plotter axes
        Place the default properties setup here to record the first cut design of the plotter
        """
        properties = {
            "title": None,
            "xlabel": None,
            "ylabel": None,
            "invert_xaxis": False,
            "invert_yaxis": False,
            "grid": False,
        }
        self.set_axes_properties(properties)

    def plot(self, snapshot: Snapshot):
        """Plot the snapshots
        """
        # Plot the snapshot
        SnapshotVis(snapshot).draw(self.axes)
        

class StatisticsPlotter(BasePlotter):

    def set_default_properties(self):
        """Set the default properties for the plotter axes
        Place the default properties setup here to record the first cut design of the plotter
        """
        properties = {
            "title": None,
            "xlabel": None,
            "ylabel": None,
            "invert_xaxis": False,
            "invert_yaxis": False,
            "grid": False,
        }
        self.set_axes_properties(properties)

    def plot(self, lock_code_stat: LockCodeStat, plot_slice: bool, plot_summary: bool) -> None:
        # for now, stat is a plain list
        StatisticsVis(lock_code_stat).draw(self.axes, plot_slice, plot_summary)


# TODO: refactor this into a separate visulization module
class ShmooPlotter(BasePlotter):
    """Shmoo plotter class
    This class draws a shmoo plot based on the experiment results stored in pandas dataframe
    It will pre-process the data from the main sweep result and plot the shmoo
    with axes given by the user
    """
    def set_default_properties(self):
        """Set the default properties for the plotter axes
        Place the default properties setup here to record the first cut design of the plotter
        """
        properties = {
            "title": None,
            "invert_xaxis": False,
            "invert_yaxis": True,
            "grid": False,
        }
        self.set_axes_properties(properties)

    def _process_dataframe(self, 
                           df_experiment: pd.DataFrame, 
                           x_axis: str, 
                           y_axis: str, 
                           z_axis: str
                           ) -> pd.DataFrame:
        # parse the experiment result
        # first, flatten the dataframe by fetching the level 1 index
        df_experiment = df_experiment.copy()
        df_experiment.columns = df_experiment.columns.get_level_values(1)
        # Then, set the index to be the x_axis and y_axis
        df_experiment = df_experiment.set_index([x_axis, y_axis])
        # Then, initially sort the index by x_axis and y_axis
        df_experiment = df_experiment.sort_index()
        # Then, get the z_axis column and drop others
        df_experiment = df_experiment[z_axis]
        # Then, unstack the dataframe so that x_axis becomes the column and y_axis becomes the index
        # level set to 0 to transpose the dataframe
        df_experiment = df_experiment.unstack(level=0)
        # Then, sort the dataframe by the x_axis
        df_experiment = df_experiment.sort_index(axis=1)
        # Then, sort the dataframe by the y_axis
        df_experiment = df_experiment.sort_index(axis=0)

        # formatted dataframe:
        # - x_axis == df_experiment.columns
        # - y_axis == df_experiment.index

        # reformat the dataframe to be used by seaborn heatmap
        if self.is_nanometer(x_axis):
            df_experiment.columns = df_experiment.columns * 1e9
        else:
            df_experiment.columns = df_experiment.columns 
        if self.is_nanometer(y_axis):
            df_experiment.index = df_experiment.index * 1e9
        else:
            pass

        return df_experiment

    def plot(self, 
             df_experiment: pd.DataFrame, 
             x_axis: str = None, 
             y_axis: str = None, 
             z_axis: str = None,
             annotate: bool = True,
             cbar: bool = True,
             cmap: str = "plasma",
             draw_xlabel: bool = True,
             draw_ylabel: bool = True,
             draw_xticklabels: bool = True,
             draw_yticklabels: bool = True,
             box_linewidth: float = 0.0,
             box_linecolor: str = "white",
             ):
        """Plot the data
        It parses the experiment result, x_axis and y_axis from dataframe and plot the shmoo
        It uses seaborn heatmap to draw the shmoo
        """
        # TODO: refactor so that dataframe processing is done in the visualizer class and not here
        # TODO: remove all the hardcodes - for now, it is hardcoded to laser sweep

        # process the dataframe
        df_experiment = self._process_dataframe(df_experiment, x_axis, y_axis, z_axis)

        # formatting labels
        fmt_labels = lambda x: f"{x:.3f}"
        xticklabels = [fmt_labels(x) for x in df_experiment.columns.values]
        yticklabels = [fmt_labels(x) for x in df_experiment.index.values]

        # # apply offset for LogNorm
        # offset = 1e-5
        # df_experiment = df_experiment + offset

        # plot the shmoo (heatmap using seaborn)
        # adjust ticklabels to be more readable

        linthresh = 1e-5
        sns.heatmap(df_experiment, 
                    fmt='.2f', 
                    annot=annotate,
                    cbar=cbar,
                    xticklabels=xticklabels,
                    yticklabels=yticklabels,
                    square=True,
                    vmin=0.0,
                    vmax=1.0,
                    cmap=cmap,
                    # norm=LogNorm(),
                    norm=SymLogNorm(linthresh=linthresh, linscale=1.0, vmin=0.0, vmax=1.0),
                    ax=self.axes,
                    linewidths=box_linewidth,
                    linecolor=box_linecolor,
                    )

        # TODO: fix that axis properties are set at one place
        # set the default properties again
        self.set_default_properties()

        if draw_xlabel:
            x_axis_prefix = "ring " if self.is_ring(x_axis) else "laser "
            if self.is_nanometer(x_axis):
                xlabel = x_axis_prefix + df_experiment.columns.name + " [nm]"
            else:
                xlabel = x_axis_prefix + df_experiment.columns.name
            self.axes.set_xlabel(xlabel, fontsize=20)
        else:
            self.axes.set_xlabel(None)

        if draw_ylabel:
            y_axis_prefix = "ring " if self.is_ring(y_axis) else "laser "
            if self.is_nanometer(y_axis):
                ylabel = y_axis_prefix + df_experiment.index.name + " [nm]"
            else:
                ylabel = y_axis_prefix + df_experiment.index.name
            self.axes.set_ylabel(ylabel, fontsize=20)
        else:
            self.axes.set_ylabel(None)

        self._redraw_frame()

        self._set_seaborn_xticklabels(5, draw_xticklabels)
        self._set_seaborn_yticklabels(5, draw_yticklabels)

        # self.axes.xaxis.label.set_visible(False)
        # self.axes.yaxis.label.set_visible(False)
        # self.axes.set_title(f"Shmoo : {z_axis}")
        # self.axes.set_title("Lock Failure Rate Shmoo Plot", fontsize=20, fontname='Times New Roman')
        # self.axes.set_title("Ideal Arbiter", fontsize=20, fontname='Times New Roman')

    def plot_shoreline(self, 
             df_experiment: pd.DataFrame, 
             x_axis: str = None, 
             y_axis: str = None, 
             z_axis: str = None,
             draw_xlabel: bool = True,
             draw_ylabel: bool = True,
             draw_xticklabels: bool = True,
             draw_yticklabels: bool = True,
             x_normalize: Optional[float] = None,
             y_normalize: Optional[float] = None,
             ):

        # process the dataframe
        df_experiment = self._process_dataframe(df_experiment, x_axis, y_axis, z_axis)
        
        linthresh = 1e-5

        transitions = []
        xaxis = []

        for column in df_experiment.columns:
            if not df_experiment[column].gt(linthresh).all():
                transition = df_experiment[column].gt(linthresh).idxmin()
                transitions.append(transition)
                xaxis.append(column)
            
            # if all values are above linthresh, then set the transition to the max value
            # If you want to skip this, then remove the else block
            else:
                transitions.append(df_experiment.index.max())
                xaxis.append(column)

        if x_normalize is not None:
            xaxis = [x / x_normalize for x in xaxis]
        if y_normalize is not None:
            transitions = [x / y_normalize for x in transitions]

        # self.axes.plot(df_experiment.columns, transitions, marker='o', markersize=5, color='black')
        # self.axes.plot(df_experiment.columns, transitions)
        self.axes.plot(xaxis, transitions, marker='o', markersize=5)

        if draw_xlabel:
            x_axis_prefix = "ring " if self.is_ring(x_axis) else "laser "
            if self.is_nanometer(x_axis):
                xlabel = x_axis_prefix + df_experiment.columns.name + " [nm]"
            else:
                xlabel = x_axis_prefix + df_experiment.columns.name
            self.axes.set_xlabel(xlabel, fontsize=20)
        else:
            self.axes.set_xlabel(None)

        if draw_ylabel:
            y_axis_prefix = "ring " if self.is_ring(y_axis) else "laser "
            if self.is_nanometer(y_axis):
                ylabel = y_axis_prefix + df_experiment.index.name + " [nm]"
            else:
                ylabel = y_axis_prefix + df_experiment.index.name
            self.axes.set_ylabel(ylabel, fontsize=20)
        else:
            self.axes.set_ylabel(None)

        self.set_default_properties()

        ylim_max = df_experiment.index.max()
        ylim_min = df_experiment.index.min()
        self.axes.set_ylim(ylim_min, ylim_max)

        self._redraw_frame()

        self.axes.set_xticks(df_experiment.columns)
        self.axes.set_yticks(df_experiment.index)

        # formatting labels
        fmt_labels = lambda x: f"{x:.2f}"
        xticklabels = [fmt_labels(x) for x in df_experiment.columns.values]
        yticklabels = [fmt_labels(x) for x in df_experiment.index.values]

        self.axes.set_xticklabels(xticklabels, rotation=45)
        self.axes.set_yticklabels(yticklabels)

        self._set_seaborn_xticklabels(5, draw_xticklabels)
        self._set_seaborn_yticklabels(5, draw_yticklabels)

    def is_ring(self, axis_name: str):
        """Check if the axis is a ring axis
        """
        return not axis_name.startswith("grid")

    def is_nanometer(self, axis_name: str):
        """Check if the axis is in nanometer
        """
        # if axis_name == "tuning_range_mean" or axis_name == "fsr_mean" or axis_name == "resonance_variance" or axis_name
        # == "grid_max_offset":
        if axis_name in ["tuning_range_mean", "fsr_mean", "resonance_variance", "grid_max_offset"]:
            return True
        # elif axis_name == "tuning_range_variance" or axis_name == "fsr_variance" or axis_name == "grid_variance":
        elif axis_name in ["tuning_range_variance", "fsr_variance", "grid_variance"]:
            return False
        else:
            raise ValueError(f"Unexpected axis name: {axis_name}")

    def _set_seaborn_xticklabels(self, num_xticklabels: int, draw_xticklabels: bool = True):
        """Trim the seaborn x-axis ticklabels."""
        xticks_curr = self.axes.get_xticks()
        xticklabels_curr = self.axes.get_xticklabels()
        num_xticklabels_curr = len(xticklabels_curr)

        assert int(num_xticklabels_curr / num_xticklabels) == num_xticklabels_curr / num_xticklabels, \
            "num_xticklabels must be a factor of num_xticklabels_curr"

        xticks_new = []
        xticklabels_new = []
        for i in range(num_xticklabels_curr):
            if i % (num_xticklabels_curr / num_xticklabels) == 0 or i == num_xticklabels_curr - 1:
                xticks_new.append(xticks_curr[i])
                xticklabels_new.append(f"{float(xticklabels_curr[i].get_text()):.2f}")

        self.axes.set_xticks(xticks_new)
        if draw_xticklabels:
            self.axes.set_xticklabels(xticklabels_new, rotation=45)
        else:
            self.axes.set_xticklabels([])
        self.axes.xaxis.set_minor_locator(AutoMinorLocator(5))

    def _set_seaborn_yticklabels(self, num_yticklabels: int, draw_yticklabels: bool = True):
        """Trim the seaborn y-axis ticklabels."""
        yticks_curr = self.axes.get_yticks()
        yticklabels_curr = self.axes.get_yticklabels()
        num_yticklabels_curr = len(yticklabels_curr)

        assert int(num_yticklabels_curr / num_yticklabels) == num_yticklabels_curr / num_yticklabels, \
            "num_yticklabels must be a factor of num_yticklabels_curr"

        yticks_new = []
        yticklabels_new = []
        for i in range(num_yticklabels_curr):
            if i % (num_yticklabels_curr / num_yticklabels) == 0 or i == num_yticklabels_curr - 1:
                yticks_new.append(yticks_curr[i])
                yticklabels_new.append(f"{float(yticklabels_curr[i].get_text()):.2f}")

        self.axes.set_yticks(yticks_new)
        if draw_yticklabels:
            self.axes.set_yticklabels(yticklabels_new)
        else:
            self.axes.set_yticklabels([])
        self.axes.yaxis.set_minor_locator(AutoMinorLocator(5))

    def _redraw_frame(self, linewidth: Optional[float] = None):
        spines_array = ['top', 'bottom', 'right', 'left']
        for spine_str in spines_array:
            self.axes.spines[spine_str].set_visible(True)

        if linewidth is not None:
            for spine_str in spines_array:
                self.axes.spines[spine_str].set_visible(linewidth)
        
    
if __name__ == "__main__":
    # create a figure
    fig_canvas = FigureTemplate.draw(nrows=1,
                                ncols=2,
                                figsize=(5, 5),
                                properties={"facecolor": "white"})


