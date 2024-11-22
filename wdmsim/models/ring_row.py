
from typing import List, Dict

from wdmsim.models.laser_grid import LaserGrid
from wdmsim.models.optical_wave import OpticalWave
from wdmsim.models.optical_port import OpticalPort, OpticalPortType
from wdmsim.models.sim_instance import SimInstance

# TODO: disabled drop port for now - roll back or fix if needed
class Ring:
    """Ring class
    Behavioral model of a ring with peak resonance wavelength, free spectral range and tuning range
    This class encapsulates the physical properties of a photonic microring (specifically of a voltage-tuned)
    This class is a unit component of a ring filter row and mainly interacts with tuner backend

    Attributes:
        wavelength: wavelength of the ring at voltage mid-code
        fsr: free spectral range of the ring
        tuning_range: the length of the tuning sweep range of the ring with full-scale voltage DAC
    """
    def __init__(self, wavelength: float, fsr: float, tuning_range: float) -> None:
        """
        :param wavelength: wavelength of the ring at voltage mid-code
        :param fsr: free spectral range of the ring 
        :param tuning_range: the length of the tuning sweep range of the ring with full-scale voltage DAC
        :type wavelength: float
        :type fsr: float
        :type tuning_range: float
        """
        self.wavelength    = wavelength
        self.fsr           = fsr
        self.tuning_range = tuning_range 

    def __str__(self) -> str:
        return f"Ring(wavelength={self.wavelength}, fsr={self.fsr}, sweep_length={self.tuning_range})"

    def __repr__(self) -> str:
        return f"Ring(wavelength={self.wavelength}, fsr={self.fsr}, sweep_length={self.tuning_range})"

    # def update_wavelength(self, wavelength: float) -> None:
    #     """Ring resonance wavelength modulation by thermal activities
    #     Currently not used
    #     :param wavelength: wavelength of the ring at voltage mid-code
    #     """
    #     self.wavelength = wavelength


class RingRxWDM(Ring, SimInstance):
    """Rx WDM Ring class
    Behavioral model of a receive ring for WDM row
    This class extends the ring model by adding pointers to the previous and the next ring in a row
    to enable the model capability of laser grabbing prioritization property of WDM ring row 
    Laser grabbing prioritization refers to the receive ring's specific behavior where laser wavelengths 
    absorbed by the previous rings are not visible to the current ring
    Moreover, this class keeps a parameter to track the update status of the waves in the ring
    to enable the model capability of event-driven wave propagation

    Attributes:
        wavelength: wavelength of the ring at voltage mid-code
        fsr: free spectral range of the ring
        tuning_range: the length of the tuning sweep range of the ring with full-scale voltage DAC

        inst_prev: pointer to the previous ring in the row
        inst_next: pointer to the next ring in the row

        waves_in: optical waves with the list of wavelengths input to the ring
        waves_thru: optical waves with the list of wavelengths transmitted through the ring
        waves_drop: optical waves with the list of wavelengths dropped by the ring

        waves_updated: flag to track the update status of the waves in the ring

        curr_wavelength: current wavelength of the ring (used only for visualization/debugging purposes)
    """
    def __init__(self, wavelength: float, fsr: float, tuning_range: float) -> None:
        """
        :param wavelength: wavelength of the ring at voltage mid-code
        :param fsr: free spectral range of the ring 
        :param tuning_range: the length of the tuning sweep range of the ring with full-scale voltage DAC
        :type wavelength: float
        :type fsr: float
        :type tuning_range: float
        """
        super().__init__(wavelength, fsr, tuning_range)

        # Initialize ports
        self._init_ports()

        # Initialize sysclk
        self._sysclk = 0

        # this variable is used only for visualization/debugging purposes
        self.curr_wavelength : float = wavelength

    def __str__(self) -> str:
        return f"Ring(wavelength={self.wavelength}, fsr={self.fsr}, sweep_length={self.tuning_range})"

    def __repr__(self) -> str:
        return f"Ring(wavelength={self.wavelength}, fsr={self.fsr}, sweep_length={self.tuning_range})"

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
        self._ports['in'] : OpticalPort = OpticalPort(self, 'in', OpticalPortType.IN)
        self._ports['thru'] : OpticalPort = OpticalPort(self, 'thru', OpticalPortType.OUT)
        # self._ports['drop'] : OpticalPort = OpticalPort(self, 'drop', OpticalPortType.OUT)

    def passthrough_wave(self) -> None:
        """
        This function initializes the waves in the ring as pass-through
        """
        if self.ports['in'].is_connected:
            self.ports['in'].propagate_wave_from_conn()
        self.ports['thru'].wave : OpticalPort = self.ports['in'].wave
        # self.ports['drop'].wave : OpticalPort = OpticalWave()

    def propagate_wave(self) -> None:
        """
        This function propagates the waves into the ring from the input port
        """

        # THRU -> IN and IN -> THRU is only propagated at time step
        # Say, if Slice A sees 1300nm at 2rd peak (wave index 2), and Slice B sees 1305nm at 3nd peak (wave index 3)
        # Slice A and Slice B tries to acquire lock at the same time and A locks at 2nd peak
        # If the change is applied at the same time step, Slice B will see 1300nm at 2nd peak
        # Meaning wave index based lock calculation is not feasible
        # This should be the case since it is precisely how the tuner backend would work
        #
        # Also, it is easier to logically define the Duplicate Lock by parsing the lock wavelength list from the rings
        # Duplicate lock will be accounted for at the SUT level
        #
        # TODO: this is very tricky, but good to keep this way (for now, sv would behave differently)
        if self.ports['in'].is_connected:
            self.ports['in'].propagate_wave_from_conn()

        # IN -> THRU is propagated at every time step
        self.ports['thru'].wave = self.ports['in'].wave.filter_by_wavelength(self.curr_wavelength, invert=True)
        # self.ports['drop'].wave = self.ports['in'].wave.filter_by_wavelength(self.curr_wavelength, invert=False)

    def acquire_lock(self, wavelength: float) -> None:
        """
        Experimental function
        Not sure if working well due to floating point comparison errors (reltol~1e-16?)
        """
        # Update the waves in the ring
        self.ports['thru'].wave = self.ports['in'].wave.filter_by_wavelength(wavelength, invert=True)
        # self.ports['drop'].wave = self.ports['in'].wave.filter_by_wavelength(wavelength, invert=False)

        # Update the current wavelength for visualization
        self.set_curr_wavelength(wavelength)

    def acquire_lock_by_wave_idx(self, wave_idx: int) -> None:
        """
        This function models the wavelength lock acquisition and resulting wavelength drop by the ring
        The waves at thru and drop ports of the ring are modulated by ring by dropping the target wavelength at lock 
        to the drop port and propagating the rest of the wavelengths to the thru port
        :param wave_idx: wavelength index
        """
        # Update the waves in the ring
        self.ports['thru'].wave = self.ports['in'].wave.filter_by_wave_idx(wave_idx, invert=True)
        # self.ports['drop'].wave = self.ports['in'].wave.filter_by_wave_idx(wave_idx, invert=False)

        # Update the current wavelength for visualization
        self.set_curr_wavelength(self.ports['in'].wave.wavelengths[wave_idx])
    
    def release_lock(self) -> None:
        """
        This function models the wavelength lock release and resulting wavelength restore by the ring
        The waves at thru and drop ports of the ring are modulated by ring by restoring the target wavelength at lock
        to the thru port and removing the drop port waves
        """
        # Let the waves in the ring pass through
        self.passthrough_wave()

        # Update the current wavelength for visualization
        self.reset_curr_wavelength()

    """
    Visualization functions
    For now, curr_wavelength attribute is only used for visualization purposes 
    - to show the current wavelength of the ring set by tuner at lock acquisition
    - to show the current wavelength of the ring set by tuner at lock release
    """
    def set_curr_wavelength(self, wavelength: float) -> None:
        """
        This function sets the current wavelength of the ring updated by the tuner (acquire_lock)
        This function is only used for visualization purposes
        :param wavelength: wavelength of the ring updated by the tuner
        :type wavelength: float
        """
        self.curr_wavelength = wavelength
    
    def reset_curr_wavelength(self) -> None:
        """
        This function resets the current wavelength of the ring updated by the tuner (release_lock)
        This function is only used for visualization purposes
        """
        self.curr_wavelength = self.wavelength
    

class RingRxWDMRow(SimInstance):
    """Ring Row class for Rx WDM

    Attributes:
        rings: list of rings
        wavelengths: list of wavelengths of the rings
    """
    def __init__(self, rings: List[RingRxWDM]) -> None:
        """
        :param rings: list of rings
        """
        # Check if the list of rings is not empty
        if len(rings) == 0:
            raise ValueError("The list of rings is empty")
        self.rings = rings

        # Connect the rings
        self.connect_rings()

        # helper list of wavelengths
        self.wavelengths = [ring.wavelength for ring in self.rings]

        # Initialize ports
        self._init_ports()

        # Initialize sysclk
        self._sysclk = 0

        # Boolean variable to check if laser grid is connected
        self._is_laser_connected = False

    def __str__(self) -> str:
        return f"RingRxWDMRow(rings={self.rings})"

    def __repr__(self) -> str:
        return f"RingRxWDMRow(rings={self.rings})"

    @property
    def ports(self) -> OpticalPort:
        """Returns output port of the laser grid

        :return: output port of the laser grid
        """
        return self._ports

    @property
    def ring_row_params(self) -> Dict[str, float]:
        return [{'fsr': ring.fsr, 'tuning_range': ring.tuning_range} for ring in self.rings]

    def _init_ports(self):
        """Initialize ports of the laser
        """
        self._ports = {}
        self._ports['in'] = self.rings[0].ports['in']
        self._ports['thru'] = self.rings[-1].ports['thru']

        # self._ports['drop'] = {}
        # for idx, ring in enumerate(self.rings):
        #     self._ports['drop'][idx] = ring.ports['drop']

    def connect_rings(self) -> None:
        """
        This function defines the geometric connection between the rings in the row
        In the ascending order of the ring indices, the thru ports are connected to the input ports of the next ring
        It is used to model the laser grabbing priority where the rings nearer to the laser can grab the laser wavelengths first

        Connectivity of the rings in the row:
           _____________   _____________           _______________ 
           |           |   |           |           |             |
        --- RingRxWDM 0 --- RingRxWDM 1 --- ... --- RingRxWDM N-1 --- None
           |___________|   |___________|           |_____________|

        Notable features include:
        - The first ring in the row is connected to the laser grid
        - The last ring in the row is connected to None
        - The rings nearer to the laser can grab the laser wavelengths first (laser grabbing priority)

        :param inst_prev: pointer to the previous ring in the row
        :param inst_next: pointer to the next ring in the row
        """
        for i in range(1, len(self.rings)):
            # important to make a correct unidirectional connection!
            self.rings[i].ports['in'].conn(from_port=self.rings[i-1].ports['thru'])

    def connect_laser_grid(self, laser_grid: LaserGrid) -> None:
        """
        This function connects the laser grid to the first ring in the row

        Connectivity of the laser grid and the first ring in the row:
        _____________   _____________   _____________           _______________
        |           |   |           |   |           |           |             |
        | LaserGrid |--- RingRxWDM 0 --- RingRxWDM 1 --- ... --- RingRxWDM N-1 --- None
        |___________|   |___________|   |___________|           |_____________|

        :param laser_grid: LaserGrid object
        """
        # important to make a correct unidirectional connection!
        self.rings[0].ports['in'].conn(from_port=laser_grid.ports['out'])
        self._is_laser_connected = True

    def passthrough_wave(self) -> None:
        """
        Run at initialization
        This function initializes the waves in the row with the waves in the laser grid
        :param laser_grid: LaserGrid object
        """
        # if not self._is_laser_connected:
            # raise ValueError("Laser grid is not connected to the row")

        # Initialize the waves in the row
        for ring in self.rings:
            ring.passthrough_wave()

    def propagate_wave(self) -> None:
        """
        This function models the time evolution of the row by propagating the waves through the rings
        At each time step, thru port waves are modulated externally by tuner lock acquisition and release
        The updated thru port waves are then propagated downstream to the next rings which is modeled by the function
        The waves are propagated by grabbing the waves from the thru port of the previous ring to the input port of the ring
        If the previous instance is a laser grid, the waves are grabbed from the laser grid to the input port of the ring
        """
        # Starting from the second ring in the row, propagate the waves from the previous ring to the input port of the ring
        # Skip the first ring in the row because the waves are already propagated to the input port of the first ring
        # at the wave initialization of the row
        # for ring in self.rings[1:]:
        for ring in self.rings:
            ring.propagate_wave()
