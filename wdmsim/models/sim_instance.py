

from abc import ABC, abstractmethod


class SimInstance(ABC):
    """Simulator Instance class
    It is a base class for instances used for simulations.
    It keeps the base properties as port, sysclk
    
    """

    @property
    @abstractmethod
    def ports(self):
        """Port of the instance
        """
        raise NotImplementedError

    @property
    def sysclk(self):
        """System clock of the instance
        """
        return self._sysclk

    @sysclk.setter
    def sysclk(self, value: int):
        self._sysclk = value

    def incr_sysclk(self):
        """Increment the system clock
        """
        self._sysclk += 1

    def rst_sysclk(self):
        """Reset the system clock
        """
        self._sysclk = 0
