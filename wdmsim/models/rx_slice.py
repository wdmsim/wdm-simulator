
from typing import Dict

from wdmsim.models.ring_row import RingRxWDM
from wdmsim.models.tuner import Tuner

class RxSlice:
    """RxSlice class
    Behavioral model of an receiver slice consisting of a ring and a tuner
    Input of the functions are laser grid and its wavelengths to be searched and locked on
    _________________
    |                |
    |   RingRxWDM    |
    |________________|
        |       |
    ____|_______|____
    |                |
    |     Tuner      |
    |________________|

    Attributes:
        ring: ring object
        tuner: tuner object
    """
    def __init__(self, ring: RingRxWDM, tuner: Tuner) -> None:
        """
        At initialization, instantiate ring and tuner and reset the system
        
        :param ring: ring object
        :param tuner: tuner object
        """
        self.ring = ring
        self.tuner = tuner

        # reset the system at boot up
        self.hard_reset()

    def __str__(self) -> str:
        """String representation of the rx slice"""
        return "RxSlice: " + str(self.ring) + " " + str(self.tuner)

    def __repr__(self) -> str:
        """Representation of the rx slice"""
        return "RxSlice: " + repr(self.ring) + " " + repr(self.tuner)

    def hard_reset(self) -> None:
        """Hard reset the tuner
        It is used to reset the tuner at system boot up
        """
        self.tuner.hard_reset()

    def soft_reset(self) -> None:
        """Soft reset the tuner
        It is used to reset the tuner when laser hot swapping is performed
        """
        self.tuner.soft_reset()

    def search_lock(self) -> None:
        """Search wavelength lock for the given laser grid
        """
        self.tuner.search_lock(self.ring)

    def acquire_lock(self, mode: str, select: int) -> None:
        """Lock onto the given laser grid
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
        self.tuner.acquire_lock(ring=self.ring, mode=mode, select=select)

    def search_and_acquire_lock(self, mode: str, select: int) -> None:
        """Search and Lock onto the given laser grid
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
        self.tuner.search_and_acquire_lock(ring=self.ring, mode=mode, select=select)

    def release_lock(self) -> bool:
        """Unlock the tuner
        :return: True if lock is released, False otherwise
        """
        # self.tuner.release_lock(self.ring)
        # self.ring.release_lock()

        self.tuner.release_lock(self.ring)

