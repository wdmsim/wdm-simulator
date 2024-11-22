import logging
from enum import Enum
from typing import Dict, List, Optional, Tuple

from wdmsim.models.laser_grid import LaserGrid
from wdmsim.models.ring_row import RingRxWDM
# from wdmsim.models.tuner_policy import (
#     find_lock_to_least_significant,
#     find_lock_to_middle,
#     find_lock_to_most_significant,
#     find_lock_to_nearest,
# )

from wdmsim.exceptions import ZeroLockException
from wdmsim.utils.pretty_print import format_wavelengths
# import wdmsim.utils.logger as logger
from wdmsim.utils.logger import _VERBOSE

logger = logging.getLogger(__name__)


# TODO: default search_table is set() and lock_code is -1, but this is VERY IMPLICIT at this point
# refactor so that this becomes explicit and can share with arbiter

# TODO: lock_to_nearest -- make it so that it's only updated when all the tuners are locked (by arbiter)
# TODO: tuner modes to ENUM?
# TODO: least_significant -> first? most-signicant -> last?
class Tuner:
    """Tuner class
    Behavioral model of a tuner with single-ring digital backend and voltage-tuned sweep
    It models the idealized wavelength search and lock by mathematically calculating the wavelength sweep range
    and finding the optical wavelength that is within the sweep range to lock on 

    Keeping non-hardware parameters like search_data and lock_wavelength is essential for the simulation
    and executor to work more efficiently e.g., simulation can check duplicate lock cases by collecting
    the lock_wavelengths of all tuners and see if the tuners are locked to the different wavelengths
    Also, search_data is used to pass over the wave index from lock search function to lock acquire function
    so that the function can update lock_wavelength in time

    Attributes:
        mode: The mode of the tuner, either "lock_to_first/second/last" or "lock_to_nearest" (default: None)

        search_status: The status of the search function, 0 for not searching, 1 for searching
        lock_status: 1 if ring is locked, 0 if ring is unlocked
        lock_code_curr: The current lock code
        lock_code_prev: The previous voltage code of the laser that the tuner is locked onto

        search_data: The search data, a dictionary of wave idx and their corresponding tuner voltage codes
        lock_data: The lock data, a dictionary of wave idx and their corresponding tuner voltage codes
        lock_wavelength: The wavelength that the ring is locked onto
    """
    
    # Hardcoded VDAC Full Scale Range
    VDAC_FS = 2**8
    
    # Search state variables
    SEARCH_DONE         = 0
    SEARCH_NOT_STARTED  = 1
    SEARCH_NO_WAVE      = 2
    SEARCH_NOT_IN_RANGE = 3

    # Lock state variables
    LOCK_DONE           = 4
    LOCK_NOT_STARTED    = 5
    LOCK_NO_WAVE        = 6
    LOCK_NOT_IN_RANGE   = 7

    def __init__(self) -> None:
        """Constructor
        It defines config/state/master parameters of the tuner and placeholders for the ring 
        """
        # Config parameters

        # State variables
        self.search_table              = set()
        self.search_status             = self.SEARCH_NOT_STARTED
        self.lock_status               = self.LOCK_NOT_STARTED
        self.lock_code                 = -1
        self.lock_code_prev            = -1

        # Non-hardware parameters 
        self.search_data               = {}
        self.search_wavelength         = {}
        # self.search_wavelength_verbose = {}
        self.lock_data                 = {}
        self.lock_wavelength           = None
        self.lock_wavelength_verbose   = {}

    """
    Reset functions
    """
    def hard_reset(self) -> None:
        """Hard reset the tuner
        """
        # Reset Config parameters

        # Reset State variables
        self.search_table              = set()
        self.search_status             = self.SEARCH_NOT_STARTED
        self.lock_status               = self.LOCK_NOT_STARTED
        self.lock_code                 = -1
        self.lock_code_prev            = -1

        # Reset Non-hardware parameters
        self.search_data               = {}
        self.search_wavelength         = {}
        # self.search_wavelength_verbose = {}
        self.lock_data                 = {}
        self.lock_wavelength           = None
        self.lock_wavelength_verbose   = {}

    def soft_reset(self) -> None:
        """Soft reset the tuner
        It is used to model RTL reset between laser hot swappings or lock release
        """
        # Reset State variables
        # self.search_table    = set() # TODO: why do you want to comment this out?
        self.search_status             = self.SEARCH_NOT_STARTED
        self.lock_status               = self.LOCK_NOT_STARTED

        # Reset Non-hardware parameters
        self.search_data               = {}
        self.search_wavelength         = {}
        # self.search_wavelength_verbose = {}
        self.lock_data                 = {}
        self.lock_wavelength           = None
        self.lock_wavelength_verbose   = {}

    """
    Search functions
    """
    def get_sweep_range(self, ring: RingRxWDM) -> List[List[float]]:
        """Get the sweep range
        Ideally, the sweep range is the range of wavelengths that the ring can dial in
        It is by nature periodic with the ring fsr extending across the broadband
        Laser grid is defined within a single fsr, so sufficient to return the range by +- fsr

        :param ring: The ring to get the sweep range of
        :return: A list of the sweep range
        """
        wavelength = ring.wavelength
        tuning_range = ring.tuning_range
        fsr = ring.fsr

        # TODO: improve? -- how can I remove all the corner cases possible?
        # This causes the sweep range to be the range of wavelengths that the ring can dial in
        # But not enough range to steer away from all the corner cases
        # return [
        #         [wavelength - tuning_range / 2 - fsr, wavelength + tuning_range / 2 - fsr],
        #         [wavelength - tuning_range / 2      , wavelength + tuning_range / 2      ],
        #         [wavelength - tuning_range / 2 + fsr, wavelength + tuning_range / 2 + fsr],
        #        ]
        
        # return [
        #         [wavelength - tuning_range / 2 - 2 * fsr, wavelength + tuning_range / 2 - 2 * fsr],
        #         [wavelength - tuning_range / 2 - 1 * fsr, wavelength + tuning_range / 2 - 1 * fsr],
        #         [wavelength - tuning_range / 2           , wavelength + tuning_range / 2           ],
        #         [wavelength - tuning_range / 2 + 1 * fsr, wavelength + tuning_range / 2 + 1 * fsr],
        #         [wavelength - tuning_range / 2 + 2 * fsr, wavelength + tuning_range / 2 + 2 * fsr],
        #         ]

        # return [
        #         [wavelength - tuning_range / 2 - 4 * fsr, wavelength + tuning_range / 2 - 4 * fsr],
        #         [wavelength - tuning_range / 2 - 3 * fsr, wavelength + tuning_range / 2 - 3 * fsr],
        #         [wavelength - tuning_range / 2 - 2 * fsr, wavelength + tuning_range / 2 - 2 * fsr],
        #         [wavelength - tuning_range / 2 - 1 * fsr, wavelength + tuning_range / 2 - 1 * fsr],
        #         [wavelength - tuning_range / 2           , wavelength + tuning_range / 2           ],
        #         [wavelength - tuning_range / 2 + 1 * fsr, wavelength + tuning_range / 2 + 1 * fsr],
        #         [wavelength - tuning_range / 2 + 2 * fsr, wavelength + tuning_range / 2 + 2 * fsr],
        #         [wavelength - tuning_range / 2 + 3 * fsr, wavelength + tuning_range / 2 + 3 * fsr],
        #         [wavelength - tuning_range / 2 + 4 * fsr, wavelength + tuning_range / 2 + 4 * fsr],
        #         ]

        # change to red-shift only (thermal tuner case)
        # from (wavelength - n * fsr) to (wavelength - n * fsr + tuning_range)
        return [
                [wavelength - 4 * fsr, wavelength - 4 * fsr + tuning_range],
                [wavelength - 3 * fsr, wavelength - 3 * fsr + tuning_range],
                [wavelength - 2 * fsr, wavelength - 2 * fsr + tuning_range],
                [wavelength - 1 * fsr, wavelength - 1 * fsr + tuning_range],
                [wavelength           , wavelength           + tuning_range],
                [wavelength + 1 * fsr, wavelength + 1 * fsr + tuning_range],
                [wavelength + 2 * fsr, wavelength + 2 * fsr + tuning_range],
                [wavelength + 3 * fsr, wavelength + 3 * fsr + tuning_range],
                [wavelength + 4 * fsr, wavelength + 4 * fsr + tuning_range],
                ]

    def search_lock(self, ring: RingRxWDM) -> None:
        """Search for a wavelength lock
        :param ring: The ring to search on
        """
        # Get the sweep range
        sweep_range = self.get_sweep_range(ring)

        # Set target waves to incoming waves of the target ring
        waves = ring.ports['in'].wave

        # TODO: incoming waves empty implies duplicate lock has happened?
        # TODO: incoming waves meaning the simulator is acting out?!
        # If incoming waves is empty i.e. waves == OpticalWaves([]), set search status to 2
        if waves.wavelengths is None:
            self.search_status = self.SEARCH_NO_WAVE
            return

        # From target search range, find the wavelengths that are within the sweep range
        # and add them to the search data in a {'wave_idx': 'tuner_voltage_code'} format
        self.search_table = set()
        self.search_data = {}
        self.search_wavelength = {}
        _tmp_search_map = {}
        for wave_idx, wavelength in enumerate(waves):
            for sweep in sweep_range:
                if wavelength >= sweep[0] and wavelength <= sweep[1]:
                    voltage_code = int((wavelength - sweep[0]) / (sweep[1] - sweep[0]) * (self.VDAC_FS))
                    # Update main table
                    self.search_table.add(voltage_code)
                    # Auxillary data
                    self.search_data[wave_idx] = voltage_code

                    # Helper variable for ideal arbiter
                    _tmp_search_map[voltage_code] = wavelength
                    # # Verbose print
                    # self.search_wavelength_verbose[voltage_code] = f"{wave_idx} : {wavelength*1e9:.2f} nm"

        # Helper variable for ideal arbiter
        # Convert from {voltage_code: wavelength} to {peak_idx: wavelength} 
        # where idx is the index of the voltage code in the sorted list of voltage codes
        # self.search_wavelength = {peak_idx: _tmp_search_map[voltage_code] for peak_idx, voltage_code in enumerate(sorted(self.search_table))}
        self.search_wavelength = {peak_idx: {'code': voltage_code, 'wavelength':
                                             _tmp_search_map[voltage_code]} 
                                             for peak_idx, voltage_code in enumerate(sorted(self.search_table))}

        # Set search status
        if self.search_data: 
            self.search_status = self.SEARCH_DONE
        else:
            self.search_status = self.SEARCH_NOT_IN_RANGE

        # verbose print
        if logger.isEnabledFor(_VERBOSE):
            sweep_range_print = [format_wavelengths(sweep) for sweep in sweep_range]
            logger.info(f"sweep range: {sweep_range_print}")
            logger.info(f"incoming wavelengths {format_wavelengths(waves.wavelengths)}")

        # # Post-assertion
        # # See if voltage codes in self.search_table and self.search_wavelength are the same
        # assert self.search_table == set([self.search_wavelength[peak_idx]['code'] for peak_idx in
        #                                  self.search_wavelength]), "Search table and search \
        #                                     wavelength are not the same"

    """
    Lock acquire/release functions
    """
    def acquire_lock(self, ring: RingRxWDM, mode: str, select: int) -> None:
        """Search and Lock onto a wavelength
        Behavioral model of a tuner performing both lock search and lock-to-maximum track
        It chooses the wavelength from the search data and mode/select configuration
        and locks the ring to the wavelength
        
        Example state configuration:
        [tuner policy]          = [mode],               [select]
        lock-to-first           = "least_significant",  0
        lock-to-second          = "least_significant",  1
        lock-to-third           = "least_significant",  2
        lock-to-nearest         = "nearest",            0
        lock-to-second-nearest  = "nearest",            1
        lock-to-last            = "most_significant",   0
        lock-to-middle          = "middle",             0

        :param ring: The ring to lock on
        :param mode: The mode of lock
        :param select: The select index of lock
        """
        # Assert that the mode and select are valid
        assert mode in ["least_significant", "nearest", "most_significant", "middle"], "Invalid mode"
        assert select >= 0, "Select must be a positive integer"

        # Set lock status to the same value as search status if search is unsuccessful (status > 0)
        # This comprises search status 1 (search not started) and 2 (wavelength not found) 
        # and 3 (wavelength not within sweep range)
        # and exit the function
        if self.search_status != self.SEARCH_DONE:
            if self.search_status == self.SEARCH_NOT_STARTED:
                self.lock_status = self.LOCK_NOT_STARTED
            elif self.search_status == self.SEARCH_NO_WAVE:
                self.lock_status = self.LOCK_NO_WAVE
            elif self.search_status == self.SEARCH_NOT_IN_RANGE:
                self.lock_status = self.LOCK_NOT_IN_RANGE
            return

        # If search status is 0 (search complete), lock to the wavelength
        # lock to one of the wavelengths of incoming waves based on the mode
        do_lock = {
            "least_significant": find_lock_to_least_significant,
            "nearest": find_lock_to_nearest,
            "most_significant": find_lock_to_most_significant,
            "middle": find_lock_to_middle,
            }    

        # wave_idx, voltage_code = do_lock[mode](self, select)
        lock_table_entry = do_lock[mode](self, select)
        if lock_table_entry is None:
            # if the function finds nothing, just return
            if logger.isEnabledFor(_VERBOSE):
                logger.info(f"Lock search failed for mode {mode} and select {select}")
            return
        else:
            # if the function finds something, unpack the entry
            wave_idx, voltage_code = lock_table_entry

        # Set lock status and lock data
        self.lock_status = self.LOCK_DONE
        self.lock_data = {wave_idx: voltage_code}

        # Set lock code previous and lock code current
        self.lock_code_prev = self.lock_code
        self.lock_code = voltage_code

        # Set lock wavelength from the wave idx of the lock data
        self.lock_wavelength = ring.ports['in'].wave[wave_idx]

        # Tune the ring to the lock wavelength
        ring.acquire_lock_by_wave_idx(wave_idx)
        # ring.acquire_lock(self.lock_wavelength)

        # TODO: temporary edit
        self.lock_wavelength_verbose = {voltage_code: f"{self.lock_wavelength*1e9:.2f}"}
         
        # # Print lock status
        # logger.info(f"Lock status: {self.lock_status}")
        # logger.info(f"Lock data: {self.lock_data}")

    def search_and_acquire_lock(self, ring: RingRxWDM, mode: str, select: int) -> None:
        """Search and Lock onto a wavelength
        Behavioral model of a tuner performing both lock search and lock-to-maximum track
        It first runs lock search, chooses the wavelength from the search data and mode/select configuration
        and locks the ring to the wavelength
        
        Example state configuration:
        [tuner policy]          = [mode],               [select]
        lock-to-first           = "least_significant",  0
        lock-to-second          = "least_significant",  1
        lock-to-third           = "least_significant",  2
        lock-to-nearest         = "nearest",            0
        lock-to-second-nearest  = "nearest",            1
        lock-to-last            = "most_significant",   0
        lock-to-middle          = "middle",             0

        :param ring: The ring to lock on
        :param mode: The mode of lock
        :param select: The select index of lock
        """
        # Do lock search
        self.search_lock(ring)

        # Do lock acquire
        self.acquire_lock(ring, mode, select)
        
    def release_lock(self, ring: RingRxWDM) -> None:
        """Unlock the tuner
        Behavioral model of a tuner performing unlock, or lock-to-minimum track
        :param ring: The ring to unlock from
        """
        # Reset lock-related parameters
        self.lock_status = self.LOCK_NOT_STARTED
        self.lock_data = {}
        # self.lock_code_prev = -1
        # self.lock_code_curr = -1
        self.lock_wavelength = None
    
        # Reset lock code to -1
        self.lock_code = -1
        
        # Detune the ring
        ring.release_lock()

    """
    Getters for wavelength search/lock data
    """
    def get_search_wave_idx(self) -> List[int]:
        """Get the searched target wavelength idx from incoming waves
        :return: The search wave idx
        """
        return list(self.search_data.keys())

    def get_search_voltage_code(self) -> List[int]:
        """Get the search voltage code
        :return: The search voltage code
        """
        return list(self.search_data.values())
    
    def get_lock_wave_idx(self) -> int:
        """Get the lock wavelength idx from incoming waves
        :return: The lock wave index
        """
        assert self.lock_status == self.LOCK_DONE, "Tuner is not locked"
        return list(self.lock_data.keys())[0]

    def get_lock_voltage_code(self) -> int:
        """Get the lock voltage code
        :return: The lock voltage code
        """
        assert self.lock_status == self.LOCK_DONE, "Tuner is not locked"
        # return list(self.lock_data.values())[0]
        return self.lock_code

    def get_lock_idx(self) -> int:
        assert self.lock_status == self.LOCK_DONE, "Tuner is not locked"
        return sorted(self.search_table).index(self.get_lock_voltage_code())


    """
    Helper function for oracle-mode
    """
    def _check_wavelength_in_search_range(self, ring: RingRxWDM, wavelength: float) -> bool:
        """Check if the wavelength is within the search range
        :return: True if the wavelength is within the search range, False otherwise
        """
        sweep_range = self.get_sweep_range(ring)
        for sweep in sweep_range:
            if wavelength >= sweep[0] and wavelength <= sweep[1]:
                return True
        else:
            return False

"""
Tuner Policies
"""

def find_lock_to_least_significant(tuner: Tuner, select: int) -> Optional[Tuple[int, int]]:
    """find the wavelength with nth lowest voltage code

    Sort the search data by voltage code and select the nth lowest voltage code
    For example, if select = 0, it will select the lowest voltage code i.e. lock-to-first
    If select = 1, it will select the second lowest voltage code i.e. lock-to-second

    :param select: n in nth lowest voltage code
    :return: tuple of target idx from incoming waves and the corresponding voltage code
    :rtype: (int, int)
    """
    assert select >= 0, "Select must be a positive integer"

    tuner_search_data = tuner.search_data

    # If select is out of range, return None (find nothing)
    if select >= len(tuner_search_data):
        return None

    # Sort the search data by voltage code from low to high
    sorted_search_data = sorted(tuner_search_data.items(), key=lambda x: x[1])

    # return the search data tuple with nth lowest voltage code
    return sorted_search_data[select]

def find_lock_to_nearest(tuner: Tuner, select: int) -> Optional[Tuple[int, int]]:
    """find the nearest wavelength found

    Sort the search data by voltage code and select the nth nearest voltage code to the previous lock code
    For example, if select = 0, it will select the nearest voltage code i.e. lock-to-nearest
    If select = 1, it will select the second nearest voltage code i.e. lock-to-second-nearest

    :param select: n in nth nearest voltage code
    :return: tuple of target idx from incoming waves and the corresponding voltage code
    :rtype: (int, int)
    """
    # # If previous lock code is set, find the nearest laser index and voltage code
    # if self.lock_code_prev >= 0:
    #
    #     # Sort the search data by voltage code from low to high to previous lock code
    #     sorted_search_data = sorted(self.search_data.items(), key=lambda x: abs(x[1] - self.lock_code_prev))
    #
    #     # Get the first laser index and voltage code from sorted search data
    #     return sorted_search_data[0]
    #
    # # If previous lock code is not set, find the first laser index and voltage code
    # else:
    #     return self._do_lock_to_first()

    assert select >= 0, "Select must be a positive integer"

    # If previous lock code is set, find the nearest laser index and voltage code
    # TODO: refactor or fix?
    if tuner.lock_code_prev < 0: tuner.lock_code_prev = int(0.5 * (tuner.VDAC_FS))

    tuner_search_data = tuner.search_data

    # If select is out of range, return None (find nothing)
    # TODO: improve
    if select >= len(tuner_search_data):
        return None

    # Sort the search data by voltage code from low to high to previous lock code
    sorted_search_data = sorted(tuner_search_data.items(), key=lambda x: abs(x[1] - tuner.lock_code_prev))

    # return the search data tuple with nth nearest voltage code
    return sorted_search_data[select]

def find_lock_to_most_significant(tuner: Tuner, select: int) -> Optional[Tuple[int, int]]:
    """find the wavelength with nth highest voltage code

    Sort the search data by voltage code and select the nth highest voltage code
    For example, if select = 0, it will select the highest voltage code i.e. lock-to-last
    If select = 1, it will select the second highest voltage code i.e. lock-to-second-last

    :param select: n in nth highest voltage code
    :return: tuple of target idx from incoming waves and the corresponding voltage code
    :rtype: (int, int)
    """
    assert select >= 0, "Select must be a positive integer"

    tuner_search_data = tuner.search_data

    # If select is out of range, return None (find nothing)
    if select >= len(tuner_search_data):
        return None

    # Sort the search data by voltage code from low to high
    sorted_search_data = sorted(tuner_search_data.items(), key=lambda x: x[1])

    # return the search data tuple with nth highest voltage code
    return sorted_search_data[-1-select]

def find_lock_to_middle(tuner: Tuner, select: int) -> Optional[Tuple[int, int]]:
    """find the wavelength with nth middle voltage code

    Sort the search data by voltage code and select the nth middle voltage code
    For example, if select = 0, it will select the middle voltage code i.e. lock-to-middle
    If select = 1, it will select the second middle voltage code i.e. lock-to-second-middle

    :param select: n in nth middle voltage code
    :return: tuple of target idx from incoming waves and the corresponding voltage code
    :rtype: (int, int)
    """
    tuner_search_data = tuner.search_data

    # If select is out of range, return None (find nothing)
    if select >= len(tuner_search_data):
        return None

    # # Sort the search data by voltage code from low to high to mid-code
    # sorted_search_data = sorted(self.search_data.items(), key=lambda x: abs(x[1]-int(0.5*(self.VDAC_FS))))
    # TODO: for now, change to lock-to-nearest-to-zero which should be the same as lock-to-middle
    sorted_search_data = sorted(tuner_search_data.items(), key=lambda x: abs(x[1]))

    # # Get the middle laser index and voltage code from sorted search data
    # return sorted_search_data[int(len(sorted_search_data) // 2)]

    # return the search data tuple with nth middle voltage code
    return sorted_search_data[select]


