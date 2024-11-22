"""
INI Config File Parser
-- Likely deprecated in favor of YAML
"""


import configparser
from enum import Enum, auto
from typing import NamedTuple
import numpy as np
from abc import ABC, abstractmethod
import yaml

from wdmsim.schemas.design_params import LaserDesignParams, RingDesignParams
from wdmsim.schemas.base_config import ConfigFile, RunType


class ConfigSingleINI(ConfigFile):
    """INI file class

    :param file: INI file name
    :param section: INI section name
    """
    TYPE = RunType.SINGLE

    def load(self):
        """Loads the config dict from the INI file
        """
        config = configparser.ConfigParser()
        config.read(self.file)
        return config[self.section]


class ConfigSweepINI(ConfigFile):
    """INI file class

    :param file: INI file name
    :param section: INI section name
    """
    TYPE = RunType.SWEEP

    def load(self):
        """Loads the config dict from the INI file
        """
        config = configparser.ConfigParser()
        config.read(self.file)
        return config[self.section]


class LaserConfigINI(ConfigSingleINI):
    """Laser parameters class

    :param file: INI file name
    :type file: str
    :param section: INI section name
    :type section: str
    :param design_params: Laser design parameters
    :type design_params: LaserDesignParams
    """
    def __init__(self, file: str, section: str):
        super().__init__(file, section)

        # Load the config dict
        config_dict = self.load()

        # Set the attributes
        num_channel       = int(config_dict['num_channel'])
        center_wavelength = float(config_dict['center_wavelength'])
        grid_spacing      = float(config_dict['grid_spacing'])
        grid_variance     = float(config_dict['grid_variance'])
        grid_offset       = float(config_dict['grid_offset'])
        
        # Set the laser design params
        self.design_params = LaserDesignParams(num_channel, center_wavelength, grid_spacing, grid_variance, grid_offset)


class RingConfigINI(ConfigSingleINI):
    """Ring row parameters class

    :param file: INI file name
    :type file: str
    :param section: INI section name
    :type section: str
    :param design_params: Ring design parameters
    :type design_params: RingDesignParams
    """
    def __init__(self, file: str, section: str):
        super().__init__(file, section)

        # Load the config dict
        config_dict = self.load()

        # Set the attributes
        fsr               = float(config_dict['fsr'])
        tuning_range_mean = float(config_dict['tuning_range_mean'])
        tuning_range_std  = float(config_dict['tuning_range_std'])
        
        self.design_params = RingDesignParams(fsr, tuning_range_mean, tuning_range_std)


class LaserConfigSweepINI(ConfigSweepINI):
    """A group of laser design parameters for sweep

    :param file: INI file name
    :type file: str
    :param section: INI section name
    :type section: str
    :param design_sweep_params: List of laser design parameters
    :type design_sweep_params: List[LaserDesignParams]
    """
    def __init__(self, file: str, section: str):
        super().__init__(file, section)

        # Load the config dict
        config_dict = self.load()

        # Set the attributes
        num_channel              = int(config_dict['num_channel'])
        center_wavelength        = float(config_dict['center_wavelength'])
        grid_spacing             = float(config_dict['grid_spacing'])
        grid_variance_min        = float(config_dict['grid_variance_min'])
        grid_variance_max        = float(config_dict['grid_variance_max'])
        grid_variance_num_points = int(config_dict['grid_variance_num_points'])
        grid_offset_min          = float(config_dict['grid_offset_min'])
        grid_offset_max          = float(config_dict['grid_offset_max'])
        grid_offset_num_points   = int(config_dict['grid_offset_num_points'])

        # Set the laser design params list
        self.design_sweep_params = []
        for grid_variance in np.linspace(grid_variance_min, grid_variance_max, grid_variance_num_points):
            for grid_offset in np.linspace(grid_offset_min, grid_offset_max, grid_offset_num_points):
                self.design_sweep_params.append(
                        LaserDesignParams(num_channel, center_wavelength, grid_spacing, grid_variance, grid_offset)
                        )


class RingConfigSweepINI(ConfigSweepINI):
    """Ring row parameters class

    :param file: INI file name
    :type file: str
    :param section: INI section name
    :type section: str
    :param design_sweep_params: List of ring design parameters
    :type design_sweep_params: List[RingDesignParams]
    """
    def __init__(self, file: str, section: str):
        super().__init__(file, section)

        # Load the config dict
        config_dict = self.load()

        # Set the attributes
        fsr                          = float(config_dict['fsr'])
        tuning_range_mean_min        = float(config_dict['tuning_range_mean_min'])
        tuning_range_mean_max        = float(config_dict['tuning_range_mean_max'])
        tuning_range_mean_num_points = int(config_dict['tuning_range_mean_num_points'])
        tuning_range_std_min         = float(config_dict['tuning_range_std_min'])
        tuning_range_std_max         = float(config_dict['tuning_range_std_max'])
        tuning_range_std_num_points  = int(config_dict['tuning_range_std_num_points'])
        
        # Set the ring design params list
        self.design_sweep_params = []
        for tuning_range_mean in np.linspace(tuning_range_mean_min, tuning_range_mean_max, tuning_range_mean_num_points):
            for tuning_range_std in np.linspace(tuning_range_std_min, tuning_range_std_max, tuning_range_std_num_points):
                self.design_sweep_params.append(
                        RingDesignParams(fsr, tuning_range_mean, tuning_range_std)
                        )



