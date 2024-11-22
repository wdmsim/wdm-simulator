"""
Yaml Config File Parser

"""
import configparser
from enum import Enum, auto
from typing import NamedTuple, Union, List, Dict
import numpy as np
from abc import ABC, abstractmethod
import yaml

from cerberus import Validator

from wdmsim.schemas.design_params import (
    LaserDesignParams, 
    RingDesignParams, 
    LaneOrderParams,
)
from wdmsim.schemas.base_config import ConfigFile, RunType, SimType

ALLOWED_DISTRIBUTIONS = ["UNIFORM", "GAUSSIAN", "GAUSSIAN_TRIMMED"]


class ConfigYAML(ConfigFile, ABC):
    
    def __init__(self, file: str, section: str):
        super().__init__(file, section)

        # Load the config dict
        self.config_dict = self.load()

        # Validate the config dict
        self._validate_type_config(self.config_dict, self.SIMTYPE)
        self._validate_run_config(self.config_dict, self.RUN)
        self._validate_design_config(self.config_dict)

    @property
    @abstractmethod
    def RUN(self) -> RunType:
        raise NotImplementedError

    @property
    @abstractmethod
    def SIMTYPE(self) -> SimType:
        raise NotImplementedError

    @property
    @abstractmethod
    def SCHEMA(self) -> Dict:
        raise NotImplementedError

    def load(self):
        with open(self.file, 'r') as f:
            # Load the yaml file and check if its dictionary key is 'ring' or 'laser'
            return yaml.load(f, Loader=yaml.FullLoader)[self.section]

    def _validate_type_config(self, data: dict, config_type: SimType):
        """
        Validate type type from the yaml file
        """
        if config_type == SimType.RING:
            if not data['type'] == 'RING':
                raise ValueError("Invalid yaml file. Expected RING type and got {data['run']}")
            else:
                return True
        elif config_type == SimType.LASER:
            if not data['type'] == 'LASER':
                raise ValueError("Invalid yaml file. Expected LASER type and got {data['run']}")
            else:
                return True
        elif config_type == SimType.LANEORDER:
            if not data['type'] == 'LANEORDER':
                raise ValueError("Invalid yaml file. Expected LANEORDER type and got {data['run']}")
            else:
                return True
        else:
            raise ValueError(f"Invalid config type, {config_type}")

    def _validate_run_config(self, raw_data: dict, config_type: RunType):
        """
        Validate the yaml data
        """
        if config_type == RunType.SINGLE:
            if not raw_data['run'] == 'SINGLE':
                raise ValueError("Invalid yaml file. Expected SINGLE type and got {data['run']}")
            else:
                return True
        elif config_type == RunType.SWEEP:
            if not raw_data['run'] == 'SWEEP':
                raise ValueError("Invalid yaml file. Expected SWEEP type and got {data['run']}")
            else:
                return True
        else:
            raise ValueError("Invalid config type")

    def _validate_design_config(self, config_dict: dict):
        """Validate the config dict

        :param config_dict: Config dict
        :type config_dict: dict
        """
        v = Validator(self.SCHEMA, allow_unknown=True)
        if not v.validate(config_dict):
            raise ValueError("Invalid config file: {}".format(v.errors))

    @classmethod
    def get_config_cls(cls: "ConfigYAML", config_file: str, config_section: str) -> "ConfigYAML":
        """Parse the metadata from the config file
        """
        with open(config_file, 'r') as f:
            raw_config = yaml.load(f, Loader=yaml.FullLoader)[config_section]
            if raw_config['run'] == 'SINGLE' and raw_config['type'] == 'RING':
                return RingConfigYAML
            elif raw_config['run'] == 'SINGLE' and raw_config['type'] == 'LASER':
                return LaserConfigYAML
            elif raw_config['run'] == 'SWEEP' and raw_config['type'] == 'RING':
                return RingSweepConfigYAML
            elif raw_config['run'] == 'SWEEP' and raw_config['type'] == 'LASER':
                return LaserSweepConfigYAML
            elif raw_config['run'] == 'SINGLE' and raw_config['type'] == 'LANEORDER':
                return LaneOrderConfigYAML
            elif raw_config['run'] == 'SWEEP' and raw_config['type'] == 'LANEORDER':
                raise NotImplementedError("LaneOrderSweepConfigYaml not implemented yet")
            else:
                raise ValueError(f"Invalid config file: {config_file}")


class ConfigSingleYAML(ConfigYAML):
    """Yaml file class
    """
    RUN = RunType.SINGLE

    @property
    @abstractmethod
    def design_params(self) -> Union[LaserDesignParams, RingDesignParams]:
        raise NotImplementedError


class ConfigSweepYAML(ConfigYAML):
    """Yaml file class
    """
    RUN = RunType.SWEEP

    @property
    @abstractmethod
    def design_sweep_params(self) -> Union[List[LaserDesignParams], List[RingDesignParams]]:
        raise NotImplementedError


class LaserConfigYAML(ConfigSingleYAML):
    """Laser parameters class

    :param file: INI file name
    :type file: str
    :param section: INI section name
    :type section: str
    :param design_params: Laser design parameters
    :type design_params: LaserDesignParams
    """

    SIMTYPE = SimType.LASER

    SCHEMA = {
        'run': {'type': 'string', 'allowed': ['SINGLE'], 'required': True},
        'type': {'type': 'string', 'allowed': ['LASER'], 'required': True},
        # 'initialize': {'type': 'string', 'allowed': ['GRID', 'RANDOM'], 'required': True},
        'attribute': {
            'type': 'dict',
            'schema': {
                'num_channel': {'type': 'integer', 'min': 1},
                'center_wavelength': {'type': 'float', 'min': 0.0},
                'grid_spacing': {'type': 'float', 'min': 0.0},
                'grid_max_offset': {'type': 'float', 'min': 0.0},
                'grid_variance': {'type': 'float', 'min': 0.0, 'max': 1.0},
                # 'grid_variance_distr': {'type': 'string', 'allowed': ALLOWED_DISTRIBUTIONS},
            }
        }
    }

    @property
    def design_params(self) -> LaserDesignParams:
        """
        Laser design parameters
        """
        # Set the laser design params
        return LaserDesignParams(**self.config_dict['attribute'])


class RingConfigYAML(ConfigSingleYAML):
    """Ring row parameters class

    :param file: INI file name
    :type file: str
    :param section: INI section name
    :type section: str
    :param design_params: Ring design parameters
    :type design_params: RingDesignParams
    """

    SIMTYPE = SimType.RING

    SCHEMA = {
        'run': {'type': 'string', 'allowed': ['SINGLE'], 'required': True},
        'type': {'type': 'string', 'allowed': ['RING'], 'required': True},
        # 'initialize': {'type': 'string', 'allowed': ['GRID', 'RANDOM'], 'required': True},
        'attribute': {
            'type': 'dict',
            'schema': {
                'fsr_mean': {'type': 'float', 'min': 0.0},
                'fsr_variance': {'type': 'float', 'min': 0.0, 'max': 1.0},
                'tuning_range_mean': {'type': 'float', 'min': 0.0},
                'tuning_range_variance': {'type': 'float', 'min': 0.0, 'max': 1.0},
                # 'tuning_range_variance_distr': {'type': 'string', 'allowed': ALLOWED_DISTRIBUTIONS},
                'inherit_laser_variance': {'type': 'boolean'},
                'resonance_variance': {'type': 'float', 'min': 0.0}, # in nm unit
                # 'resonance_variance_distr': {'type': 'string', 'allowed': ALLOWED_DISTRIBUTIONS},
            }
        }
    }

    @property
    def design_params(self) -> RingDesignParams:
        """
        Ring design parameters
        """
        # Parse design params
        return RingDesignParams(**self.config_dict['attribute'])


class LaneOrderConfigYAML(ConfigSingleYAML):
    """lane ordering parameters class

    :param file: INI file name
    :type file: str
    :param section: INI section name
    :type section: str
    :param design_params: Ring design parameters
    :type design_params: RingDesignParams
    """

    SIMTYPE = SimType.LANEORDER

    SCHEMA = {
        'run': {'type': 'string', 'allowed': ['SINGLE'], 'required': True},
        'type': {'type': 'string', 'allowed': ['LANEORDER'], 'required': True},
        'attribute': {
            'type': 'dict',
            'required': True,
            'schema': {
                'lane': {
                    # TODO: Add validation for None type lane ordering for the case of lock-to-any tgt lane
                    # 'oneof': [
                    #     {'type': 'dict'},
                    #     {'type': 'none'} # if none then it will be "lock-to-any" - only allowed for target LO
                    # ],
                    # 'type': 'dict',
                    'type': 'dict',
                    'required': True,
                    'nullable': True, # Allow None when "lock-to-any" - only allowed for target LO
                },
                'alias': {'type': 'string', 'required': True}, # Much useful to have a name for the lane order
            },
        }
    }

    @property
    def design_params(self) -> LaneOrderParams:
        """
        Ring design parameters
        """
        # Parse design params
        return LaneOrderParams(**self.config_dict['attribute'])


class LaserSweepConfigYAML(ConfigSweepYAML):
    """Laser parameters class

    :param file: INI file name
    :type file: str
    :param section: INI section name
    :type section: str
    :param design_params: Laser design parameters
    :type design_params: LaserDesignParams
    """

    SIMTYPE = SimType.LASER

    SCHEMA = {
        'run': {'type': 'string', 'allowed': ['SWEEP'], 'required': True},
        'type': {'type': 'string', 'allowed': ['LASER'], 'required': True},
        # 'initialize': {'type': 'string', 'allowed': ['GRID', 'RANDOM'], 'required': True},
        'attribute': {
            'type': 'dict',
            'required': True,
            'schema': {
                'num_channel': {'type': 'integer', 'min': 1},
                'center_wavelength': {'type': 'float', 'min': 0.0},
                'grid_spacing': {'type': 'float', 'min': 0.0},
                'grid_max_offset': {
                    'type': ['float', 'list', 'dict'],
                    'required': True,
                    'oneof': [
                        {'type': 'float', 'min': 0.0},
                        {'type': 'list', 'schema': {'type': 'float', 'min': 0.0}},
                        {
                            'type': 'dict', 
                            'schema': {
                                'type': {'type': 'string', 'allowed': ['LINEAR']},
                                'start': {'type': 'float', 'min': 0.0},
                                'stop': {'type': 'float', 'min': 0.0},
                                'num': {'type': 'integer', 'min': 1},
                            }
                        }
                    ]
                },
                'grid_variance': {
                    'type': ['float', 'list', 'dict'],
                    'required': True,
                    'oneof': [
                        {'type': 'float', 'min': 0.0},
                        {'type': 'list', 'schema': {'type': 'float', 'min': 0.0}},
                        {
                            'type': 'dict', 
                            'schema': {
                                'type': {'type': 'string', 'allowed': ['LINEAR']},
                                'start': {'type': 'float', 'min': 0.0},
                                'stop': {'type': 'float', 'min': 0.0},
                                'num': {'type': 'integer', 'min': 1},
                            }
                        }
                    ]
                },
                # 'grid_variance_distr': {'type': 'string', 'allowed': ALLOWED_DISTRIBUTIONS},
            }
        }
    }

        
    @property
    def design_sweep_params(self) -> List[LaserDesignParams]:
        """
        List of laser design parameters
        """
        # Parse raw design params
        raw_design_params = self.config_dict['attribute']

        # Get laser design params
        # If there are multiple values, then create a list of LaserDesignParams

        # Gather the grid_max_offset values and grid_variance values into list
        grid_max_offset_list = self._tolist(raw_design_params['grid_max_offset'])
        grid_variance_list = self._tolist(raw_design_params['grid_variance'])

        # Create a list of LaserDesignParams
        design_sweep_params = []
        for grid_max_offset in grid_max_offset_list:
            for grid_variance in grid_variance_list:
                design_sweep_params.append(
                    LaserDesignParams(
                        num_channel=raw_design_params['num_channel'],
                        center_wavelength=raw_design_params['center_wavelength'],
                        grid_spacing=raw_design_params['grid_spacing'],
                        grid_max_offset=grid_max_offset,
                        grid_variance=grid_variance,
                    )
                )

        return design_sweep_params

    def _tolist(self, value: Union[float, List[float], Dict[str, float]]) -> List[float]:
        if isinstance(value, list):
            return value
        elif isinstance(value, dict):
            return np.linspace(value['start'], value['stop'], value['num'])
        else:
            return [value]

    @staticmethod
    def validator(laser_design_sweep_params: List[LaserDesignParams], num_laser_swaps: int) -> bool:
        # verify experiment parameters
        # parse max grid_variance and grid_max_offset from laser_design_sweep_params and 
        # check if they are 0, then num_laser_swaps should be 1
        max_grid_variance = max([laser_design_params.grid_variance for laser_design_params in laser_design_sweep_params])
        max_grid_max_offset = max([laser_design_params.grid_max_offset for laser_design_params in
                                   laser_design_sweep_params])
        if max_grid_variance == 0 and max_grid_max_offset == 0:
            if num_laser_swaps > 1:
                raise ValueError(f"Number of laser swaps should be 1 for a single experiment. \
                                    Current grid variance is {max_grid_variance} and \
                                    current grid max offset is {max_grid_max_offset} at max")


class RingSweepConfigYAML(ConfigSweepYAML):
    """Ring row parameters class

    :param file: INI file name
    :type file: str
    :param section: INI section name
    :type section: str
    :param design_params: Ring design parameters
    :type design_params: RingDesignParams
    """

    SIMTYPE = SimType.RING

    SCHEMA = {
        'run': {'type': 'string', 'allowed': ['SWEEP'], 'required': True},
        'type': {'type': 'string', 'allowed': ['RING'], 'required': True},
        # 'initialize': {'type': 'string', 'allowed': ['GRID', 'RANDOM'], 'required': True},
        'attribute': {
            'type': 'dict',
            'schema': {
                'fsr_mean': {
                    'type': ['float', 'list', 'dict'],
                    'required': True,
                    'oneof': [
                        {'type': 'float', 'min': 0.0},
                        {'type': 'list', 'schema': {'type': 'float', 'min': 0.0}},
                        {
                            'type': 'dict',
                            'schema': {
                                'type': {'type': 'string', 'allowed': ['LINEAR']},
                                'start': {'type': 'float', 'min': 0.0},
                                'stop': {'type': 'float', 'min': 0.0},
                                'num': {'type': 'integer', 'min': 1},
                            }
                        }
                    ],
                },
                'fsr_variance': {
                    'type': ['float', 'list', 'dict'],
                    'required': True,
                    'oneof': [
                        {'type': 'float', 'min': 0.0},
                        {'type': 'list', 'schema': {'type': 'float', 'min': 0.0}},
                        {
                            'type': 'dict',
                            'schema': {
                                'type': {'type': 'string', 'allowed': ['LINEAR', 'LOG']},
                                'start': {'type': 'float', 'min': 0.0},
                                'stop': {'type': 'float', 'min': 0.0},
                                'num': {'type': 'integer', 'min': 1},
                            }
                        }
                    ]
                },
                'tuning_range_mean': {
                    'type': ['float', 'list', 'dict'],
                    'required': True,
                    'oneof': [
                        {'type': 'float', 'min': 0.0},
                        {'type': 'list', 'schema': {'type': 'float', 'min': 0.0}},
                        {
                            'type': 'dict',
                            'schema': {
                                'type': {'type': 'string', 'allowed': ['LINEAR']},
                                'start': {'type': 'float', 'min': 0.0},
                                'stop': {'type': 'float', 'min': 0.0},
                                'num': {'type': 'integer', 'min': 1},
                            }
                        }
                    ]
                },
                'tuning_range_variance': {
                    'type': ['float', 'list', 'dict'],
                    'required': True,
                    'oneof': [
                        {'type': 'float', 'min': 0.0},
                        {'type': 'list', 'schema': {'type': 'float', 'min': 0.0}},
                        {
                            'type': 'dict',
                            'schema': {
                                'type': {'type': 'string', 'allowed': ['LINEAR', 'LOG']},
                                'start': {'type': 'float', 'min': 0.0},
                                'stop': {'type': 'float', 'min': 0.0},
                                'num': {'type': 'integer', 'min': 1},
                            }
                        }
                    ]
                },
                # 'tuning_range_variance_distr': {'type': 'string', 'allowed': ALLOWED_DISTRIBUTIONS},
                'inherit_laser_variance': {'type': 'boolean', 'required': True},
                'resonance_variance': {
                    'type': ['float', 'list', 'dict'],
                    'required': True,
                    'oneof': [
                        {'type': 'float', 'min': 0.0},
                        {'type': 'list', 'schema': {'type': 'float', 'min': 0.0}},
                        {
                            'type': 'dict',
                            'schema': {
                                'type': {'type': 'string', 'allowed': ['LINEAR', 'LOG']},
                                'start': {'type': 'float', 'min': 0.0},
                                'stop': {'type': 'float', 'min': 0.0},
                                'num': {'type': 'integer', 'min': 1},
                            }
                        }
                    ]
                }, # in nm unit
                # 'resonance_variance_distr': {'type': 'string', 'allowed': ALLOWED_DISTRIBUTIONS},
            }
        }
    }

    @property
    def design_sweep_params(self) -> List[RingDesignParams]:
        """
        List of RingDesignParams
        """
        # Parse design params
        self.design_params = RingDesignParams(**self.config_dict['attribute'])

        # Get ring design params
        # If there are multiple values, then create a list of RingDesignParams

        # Gather the fsr_mean, fsr_variance, tuning_range_mean, and tuning_range_variance into list
        fsr_mean_list = self._tolist(self.design_params.fsr_mean)
        fsr_variance_list = self._tolist(self.design_params.fsr_variance)
        tuning_range_mean_list = self._tolist(self.design_params.tuning_range_mean)
        tuning_range_variance_list = self._tolist(self.design_params.tuning_range_variance)
        resonance_variance_list = self._tolist(self.design_params.resonance_variance)

        # Create a list of RingDesignParams
        design_sweep_params = []
        for fsr_mean in fsr_mean_list:
            for fsr_variance in fsr_variance_list:
                for tuning_range_mean in tuning_range_mean_list:
                    for tuning_range_variance in tuning_range_variance_list:
                        for resonance_variance in resonance_variance_list:
                            design_sweep_params.append(
                                RingDesignParams(
                                    fsr_mean=fsr_mean,
                                    fsr_variance=fsr_variance,
                                    tuning_range_mean=tuning_range_mean,
                                    tuning_range_variance=tuning_range_variance,
                                    inherit_laser_variance=self.design_params.inherit_laser_variance,
                                    resonance_variance=resonance_variance,
                                )
                            )

        return design_sweep_params

    def _tolist(self, value: Union[float, List[float], Dict[str, float]]) -> List[float]:
        if isinstance(value, list):
            return value
        elif isinstance(value, dict):
            return np.linspace(value['start'], value['stop'], value['num'])
        else:
            return [value]

    @staticmethod
    def validator(ring_design_sweep_params: List[RingDesignParams], num_ring_swaps: int) -> None:
        # parse max fsr_variance and tuning_range_variance from ring_design_sweep_params and check if it is 0,
        # then num_ring_swaps should be 1
        max_fsr_variance = max([ring_design_params.fsr_variance for ring_design_params in ring_design_sweep_params])
        max_tuning_range_variance = max([ring_design_params.tuning_range_variance for ring_design_params in ring_design_sweep_params])
        max_resonance_variance = max([ring_design_params.resonance_variance for ring_design_params in ring_design_sweep_params])
        if max_fsr_variance == 0 and max_tuning_range_variance == 0 and max_resonance_variance == 0:
            if num_ring_swaps > 1:
                raise ValueError(f"Number of ring swaps should be 1 for a single experiment. \
                                    Current fsr variance is {max_fsr_variance} and \
                                    current tuning range variance is {max_tuning_range_variance} and \
                                    current ring resonance variance at {max_resonance_variance} at max")


