"""
Base Design Params Schema
"""

from typing import NamedTuple, Optional

class LaserDesignParams(NamedTuple):
    """Laser design parameters."""
    num_channel: int
    center_wavelength: float
    grid_spacing: float
    grid_variance: float
    grid_max_offset: float

class RingDesignParams(NamedTuple):
    """Ring design parameters."""
    fsr_mean: float               
    fsr_variance: float               
    tuning_range_mean: float 
    tuning_range_variance:  float 
    inherit_laser_variance: bool
    resonance_variance: float

class LaneOrderParams(NamedTuple):
    """Lane order parameters."""
    lane: Optional[dict]
    alias: str
