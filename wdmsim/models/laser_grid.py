
from typing import List, Union

from wdmsim.models.optical_wave import OpticalWave
from wdmsim.models.optical_port import OpticalPort, OpticalPortType
from wdmsim.models.sim_instance import SimInstance

from wdmsim.models.sysclk import execute_at_init

class Laser:
    """Laser class
    Abstract behavioral model of a laser input to the system
    Expressed in terms of wavelength of the laser and lock status in the context of ring filter row
    Lock status is a synthetic concept that does not reflect the nature of the laser
    However, lock experiments of interest should keep track of laser filter status by ring alignment
    especially when lock procedures are done in multiple time steps and 
    filtered laser grids at previous time steps are not visible at current time step

    Attributes:
        wavelength: wavelength of the laser in nm
    """
    def __init__(self, wavelength: float):
        """Inits Laser with wavelength and lock status
        
        Implementation of lock status in Laser class can be put this way:
        Following Observer design pattern, Laser class is the subject, and Tuner/Ring class is the observer
        When a laser is locked to a ring, tuner notifies the laser that it is locked
        At later time steps, subscribed tuners can be notified of the lock status of the laser

        :param wavelength: wavelength of the laser in nm
        """
        self.wavelength = wavelength


class LaserGrid(SimInstance):
    """LaserGrid class

    It initializes waves at the output port of the laser grid at startup

    Attributes:
        lasers: list of lasers in the grid
    """
    def __init__(self, lasers: Union[Laser, List[Laser]]) -> None:
        """
        :param laser_id: id of the laser grid
        :param lasers: list of lasers in the grid
        """
        if isinstance(lasers, Laser):
            lasers = [lasers]

        self.lasers = lasers

        # Collect wavelengths of lasers in the grid
        self.wavelengths = [laser.wavelength for laser in lasers]

        # Initialize ports
        self._init_ports()

        # Initialize sysclk
        self._sysclk = 0

        # Initialize laser id
        self._laser_id = 0

        # # Initialize output wave at startup
        # self.initialize_wave()

    def __str__(self):
        return f"LaserGrid {self.laser_id}: {self.lasers}"

    def __repr__(self):
        return f"LaserGrid({self.laser_id}, {self.lasers})"

    @classmethod
    def from_wavelengths(cls, wavelengths: Union[float, List[float]]) -> 'LaserGrid':
        """
        :param laser_id: id of the laser grid
        :param wavelengths: list of wavelengths in nm
        :return: LaserGrid instance
        """
        if isinstance(wavelengths, float):
            wavelengths = [wavelengths]

        return cls([Laser(wavelength) for wavelength in wavelengths])

    @property
    def num_channels(self) -> int:
        """Returns number of channels in the grid

        :return: number of channels in the grid
        """
        return len(self.lasers)

    @property
    def laser_id(self) -> int:
        """Returns laser id

        :return: laser id
        """
        return self._laser_id
    
    @property
    def ports(self) -> OpticalPort:
        """Returns output port of the laser grid

        :return: output port of the laser grid
        """
        return self._ports

    def _init_ports(self):
        """Initialize ports of the laser
        """
        self._ports = {}
        self._ports['out'] = OpticalPort(self, 'out', OpticalPortType.OUT)

    def shuffle_wavelengths(self, wavelengths: Union[float, List[float]]) -> None:
        """Shuffles new wavelengths of lasers into the grid

        Emulate the new laser grid by shuffling new wavelengths into the grid
        Mainly to save the simulation cost of re-instantiating a new LaserGrid instance
        :param wavelengths: list of wavelengths in nm
        """
        # Update wavelengths
        self.update_wavelengths(wavelengths)

        # Reset sysclk
        self.rst_sysclk()

        # Update laser id
        self._laser_id += 1

    # TODO: refactor?
    def update_wavelengths(self, wavelengths: Union[float, List[float]]) -> None:
        """Updates wavelengths of lasers in the grid

        :param wavelengths: list of wavelengths in nm
        """
        if isinstance(wavelengths, float):
            wavelengths = [wavelengths]
        self.wavelengths = wavelengths
    
        for laser_idx, laser in enumerate(self.lasers):
            laser.wavelength = wavelengths[laser_idx]

        # self.initialize_wave()

    def initialize_wave(self) -> None:
        """Initialize output wave of the laser grid
        Turn on all lasers in the grid
        """
        self.ports['out'].wave = OpticalWave(self.wavelengths)

    """
    Override built-in functions to achieve:
    - indexing (laser_grid[idx])
    - length (len(laser_grid))
    - iteration (for laser in laser_grid: ...)
    """
    def __getitem__(self, index: int) -> Laser:
        """
        :param index: index of laser in the grid
        :return: laser at index
        """
        return self.lasers[index]

    def __setitem__(self, index: int, laser: Laser) -> None:
        """
        :param index: index of laser in the grid
        :param laser: laser to set at index
        """
        self.lasers[index] = laser

    def __delitem__(self, index: int) -> None:
        """
        :param index: index of laser to delete
        """
        del self.lasers[index]

    def __len__(self) -> int:
        return len(self.lasers)

    def __iter__(self):
        return iter(self.lasers)

    def __next__(self):
        return next(self.lasers)

