from abc import ABC, abstractmethod
from typing import Any, Dict, NamedTuple, List, Tuple
from enum import Enum, auto

from pathlib import Path
import json
from dataclasses import dataclass, asdict
from dataclasses import astuple as dataclasses_astuple

from wdmsim.schemas.design_params import LaserDesignParams, RingDesignParams, LaneOrderParams


@dataclass(frozen=True)
class SimJsonizer(ABC):
    """Simulation Config Format Json Serializer/Deserializer
    """

    @abstractmethod
    def _convert_to_dict(self) -> Dict[str, Any]:
        """Convert the instance to a dictionary"""
        pass

    @classmethod
    @abstractmethod
    def _convert_from_dict(cls, data: Dict[str, Any]) -> "SimJsonizer":
        """Create an instance from a dictionary"""
        pass

    def record_json(self, json_path: Path, overwrite: bool = False) -> None:
        if json_path.exists():
            if not overwrite:
                with open(json_path, "r") as file:
                    data = json.load(file)
            else:
                data = []
        else:
            data = []

        # if json_path.exists():
        #     with open(json_path, "r") as file:
        #         data = json.load(file)
        # else:
        #     data = []
        
        # Convert the current instance to a dictionary and append to the list
        # instance_data = self._asdict()
        instance_data = self._convert_to_dict()
        data.append(instance_data)
        
        with open(json_path, "w") as file:
            json.dump(data, file, indent=4)

    @classmethod
    def from_json(cls, json_path: Path, is_singleton: bool) -> List["SimJsonizer"]:
        with open(json_path, "r") as file:
            data_list = json.load(file)
            
        if not is_singleton:    
            experiments = []
            for data in data_list:
                # Deserialize custom types here if necessary before passing to cls()
                # experiments.append(cls(**data))
                experiments.append(cls._convert_from_dict(data))
            return experiments

        else:
            return cls._convert_from_dict(data_list[0])

    # TODO: move this to SimSweepRecord
    @classmethod
    def read_ptn_from_json(cls, json_path: Path, total_partition: int, partition_idx: int) -> List["SimJsonizer"]:
        """Assuming a json contains a huge list of experiments, this function reads a partition of the json file"""
        with open(json_path, "r") as file:
            data_list = json.load(file)

        if not isinstance(data_list, list):
            raise ValueError(f"Expected a list of experiments from {json_path}, but got {type(data_list)}")

        list_len = len(data_list)
        part_size = list_len // total_partition
        start_idx = part_size * partition_idx
        end_idx = start_idx + part_size if partition_idx < total_partition - 1 else list_len

        partition_data = data_list[start_idx:end_idx]
        experiments = []
        for data in partition_data:
            experiments.append(cls._convert_from_dict(data))
        
        return experiments

@dataclass(frozen=True)
class SimSweepRecord(SimJsonizer):
    # Base parameters 
    laser_config_file: str
    laser_config_section: str
    ring_config_file: str
    ring_config_section: str
    init_lane_order_config_file: str
    init_lane_order_config_section: str
    tgt_lane_order_config_file: str
    tgt_lane_order_config_section: str
    arbiter_str: str
    num_laser_swaps: int
    num_ring_swaps: int

    # Sweep parameters
    laser_design_sweep_params: List[LaserDesignParams]
    ring_design_sweep_params: List[RingDesignParams]
    init_lane_order_params: LaneOrderParams
    tgt_lane_order_params: LaneOrderParams

    def _convert_to_dict(self) -> Dict[str, Any]:
        return {
            "laser_config_file": self.laser_config_file,
            "laser_config_section": self.laser_config_section,
            "ring_config_file": self.ring_config_file,
            "ring_config_section": self.ring_config_section,
            "init_lane_order_config_file": self.init_lane_order_config_file,
            "init_lane_order_config_section": self.init_lane_order_config_section,
            "tgt_lane_order_config_file": self.tgt_lane_order_config_file,
            "tgt_lane_order_config_section": self.tgt_lane_order_config_section,
            "arbiter_str": self.arbiter_str,
            "num_laser_swaps": self.num_laser_swaps,
            "num_ring_swaps": self.num_ring_swaps,
            "laser_design_sweep_params": [param._asdict() for param in self.laser_design_sweep_params],
            "ring_design_sweep_params": [param._asdict() for param in self.ring_design_sweep_params],
            "init_lane_order_params": self.init_lane_order_params._asdict(),
            "tgt_lane_order_params": self.tgt_lane_order_params._asdict(),
        }

    @classmethod
    def _convert_from_dict(cls, data: Dict[str, Any]) -> "SimSweepRecord":
        return cls(
            laser_config_file=data["laser_config_file"],
            laser_config_section=data["laser_config_section"],
            ring_config_file=data["ring_config_file"],
            ring_config_section=data["ring_config_section"],
            init_lane_order_config_file=data["init_lane_order_config_file"],
            init_lane_order_config_section=data["init_lane_order_config_section"],
            tgt_lane_order_config_file=data["tgt_lane_order_config_file"],
            tgt_lane_order_config_section=data["tgt_lane_order_config_section"],
            arbiter_str=data["arbiter_str"],
            num_laser_swaps=data["num_laser_swaps"],
            num_ring_swaps=data["num_ring_swaps"],
            laser_design_sweep_params=[LaserDesignParams(**param) for param in data["laser_design_sweep_params"]],
            ring_design_sweep_params=[RingDesignParams(**param) for param in data["ring_design_sweep_params"]],
            init_lane_order_params=LaneOrderParams(**data["init_lane_order_params"]),
            tgt_lane_order_params=LaneOrderParams(**data["tgt_lane_order_params"]),
        )

    # TODO: verify if is_singleton is True
    @classmethod
    def from_json(cls, json_path: Path) -> List["SimSweepRecord"]:
        return super().from_json(json_path, is_singleton=True)


@dataclass(frozen=True)
class SimReplay(SimJsonizer):
    laser_design_params: LaserDesignParams
    ring_design_params: RingDesignParams
    init_lane_order_params: LaneOrderParams
    tgt_lane_order_params: LaneOrderParams
    arbiter_str: str

    laser_wavelengths: List[float]
    ring_wavelengths: List[float]
    ring_row_params: List[dict]
    
    exit_status: int

    def _convert_to_dict(self):
        """Convert the instance to a dictionary"""
        return {
            "laser_design_params": self.laser_design_params._asdict(),
            "ring_design_params": self.ring_design_params._asdict(),
            "init_lane_order_params": self.init_lane_order_params._asdict(),
            "tgt_lane_order_params": self.tgt_lane_order_params._asdict(),
            "arbiter_str": self.arbiter_str,
            "laser_wavelengths": self.laser_wavelengths,
            "ring_wavelengths": self.ring_wavelengths,
            "ring_row_params": self.ring_row_params,
            "exit_status": self.exit_status
        }

    @classmethod
    def _convert_from_dict(cls, data: Dict[str, Any]):
        """Create an instance from a dictionary"""
        return cls(
            laser_design_params=LaserDesignParams(**data["laser_design_params"]),
            ring_design_params=RingDesignParams(**data["ring_design_params"]),
            init_lane_order_params=LaneOrderParams(**data["init_lane_order_params"]),
            tgt_lane_order_params=LaneOrderParams(**data["tgt_lane_order_params"]),
            arbiter_str=data["arbiter_str"],
            laser_wavelengths=data["laser_wavelengths"],
            ring_wavelengths=data["ring_wavelengths"],
            ring_row_params=data["ring_row_params"],
            exit_status=data["exit_status"]
        )

    @classmethod
    def from_json(cls, json_path: Path) -> List["SimReplay"]:
        return super().from_json(json_path, is_singleton=False)

    def astuple(self) -> Tuple:
        return dataclasses_astuple(self)

    # def astuple(self, overrides: Dict[str, Any] = None):
    #     if overrides is None:
    #         return dataclasses_astuple(self)
    #     else:
    #         # first, check if the overrides are valid
    #         for key in overrides:
    #             if key not in self.__annotations__:
    #                 raise ValueError(f"Invalid key {key} in overrides")
    #         # then, create a new instance with the overrides
    #         new_inst_attr = asdict(self).update(overrides)
    #         return dataclasses_astuple(self.__class__(**new_inst_attr))
    #         # return dataclasses_astuple(self, **overrides)

        # return dataclasses_astuple(self)

    # def record_json(self, json_path: Path):
    #     if json_path.exists():
    #         with open(json_path, "r") as file:
    #             data = json.load(file)
    #     else:
    #         data = []
    #
    #     # Convert the current instance to a dictionary and append to the list
    #     # instance_data = self._asdict()
    #     instance_data = self._convert_to_dict()
    #     data.append(instance_data)
    #
    #     with open(json_path, "w") as file:
    #         json.dump(data, file, indent=4)
    #
    # @classmethod
    # def from_json(cls, json_path: Path) -> List["SimReplay"]:
    #     with open(json_path, "r") as file:
    #         data_list = json.load(file)
    #
    #     # Assuming LaserDesignParams and RingDesignParams have from_dict or similar methods for deserialization
    #     experiments = []
    #     for data in data_list:
    #         # Deserialize custom types here if necessary before passing to cls()
    #         # experiments.append(cls(**data))
    #         experiments.append(cls._convert_from_dict(data))
    #     return experiments
