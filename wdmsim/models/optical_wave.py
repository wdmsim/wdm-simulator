
from typing import List, Optional, Set, Union

from wdmsim.utils.pretty_print import format_wavelengths

class OpticalWave:
    """Optical Waves class
    It models continuous wave optical signal as a set of wavelengths
    It defines a convenient algebra for signal propagation and filtering by set operations

    >> OpticalWaves({1310, 1311, 1312})
    >> OpticalWaves({1310, 1311})[0]
    >> OpticalWaves({1310, 1311})[0] = 1310.5
    >> len(OpticalWaves({1310, 1311}))
    >> for wavelength in OpticalWaves({1310, 1311}): print(wavelength)

    :param wavelengths: set of wavelengths by list
    :type wavelengths: List[float]
    """
    def __init__(self, wavelengths: Optional[Union[float, Set[float], List[float]]] = None):
        """Optical Waves class
        It models continuous wave optical signal as a set of wavelengths
        It defines a convenient algebra for signal propagation and filtering by set operations

        :param wavelengths: set of wavelengths by list
        :type wavelengths: List[float]
        """
        # wavelengths can be a single float, a set of floats or a list of floats, or None by default
        if wavelengths is None:
            wavelengths = []
        elif isinstance(wavelengths, float):
            wavelengths = [wavelengths]
        elif isinstance(wavelengths, int):
            wavelengths = [float(wavelengths)]
        elif isinstance(wavelengths, set):
            wavelengths = list(wavelengths)
            
        # Initialize the set of wavelengths as sorted
        self.wavelengths = sorted(wavelengths)

    def __add__(self, other) -> "OpticalWave":
        """Addition operator
        It models wave combination

        """
        if isinstance(other, OpticalWave):
            return OpticalWave(set(self.wavelengths).union(set(other.wavelengths)))
        else:
            raise TypeError("Unsupported operand type(s) for +: 'OpticalWaves' and '{}'".format(type(other)))

    def __sub__(self, other) -> "OpticalWave":
        """Subtraction operator
        It models wave filtering

        >> OpticalWaves({1310, 1311, 1312}) - OpticalWaves({1311})
        >> OpticalWaves({1310, 1312})
        """
        if isinstance(other, OpticalWave):
            return OpticalWave(set(self.wavelengths) - set(other.wavelengths))
        else:
            raise TypeError("Unsupported operand type(s) for -: 'OpticalWaves' and '{}'".format(type(other)))

    def __repr__(self):
        # return f"OpticalWaves({self.wavelengths})"
        return f"OpticalWaves({format_wavelengths(self.wavelengths)})"

    def __str__(self):
        # return f"{self.wavelengths}"
        return f"{format_wavelengths(self.wavelengths)}"

    """
    Override built-in methods to achieve:
    - indexing (self[0])
    - length (len(self))
    - iteration (for w in self)
    - membership (w in self)
    - equality (self == other)
    """
    def __getitem__(self, index: int) -> float:
        return self.wavelengths[index]

    def __setitem__(self, index: int, value: float):
        self.wavelengths[index] = value

    def __len__(self):
        return len(self.wavelengths)

    def __iter__(self):
        return iter(self.wavelengths)

    def __next__(self):
        return next(self.wavelengths)

    def __contains__(self, item):
        return item in self.wavelengths

    def __eq__(self, other):
        if other is None:
            return len(self.wavelengths) == 0
        return self.wavelengths == other.wavelengths

    def filter_by_wavelength(self, wavelength: float, invert: bool) -> "OpticalWave":
        """Filter by wavelength
        Experimental function: Not sure if floating number comparison is reliable
        It models wavelength filtering

        >> OpticalWaves({1310, 1311, 1312}).filter_by_wavelength(1311, invert=False)
        >> OpticalWaves({1311})
        >> OpticalWaves({1310, 1311, 1312}).filter_by_wavelength(1311, invert=True)
        >> OpticalWaves({1310, 1312})
        """
        if invert:
            return OpticalWave(set(self.wavelengths) - set([wavelength]))
        else:
            if wavelength in self.wavelengths:
                return OpticalWave(wavelength)
            else:
                return OpticalWave([])
                # return None

    def filter_by_wavelength_range(self, wavelength_min: float, wavelength_max: float) -> "OpticalWave":
        """Filter by wavelength range
        It models wavelength filtering

        >> OpticalWaves({1310, 1311, 1312}).filter_by_wavelength_range(1311, 1312)
        >> OpticalWaves({1311, 1312})
        """
        return OpticalWave({wavelength for wavelength in self.wavelengths if wavelength_min <= wavelength <= wavelength_max})

    def filter_by_wave_idx(self, wave_idx: int, invert: bool) -> "OpticalWave":
        """Filter by wave index
        It models wavelength filtering with the wave index as a reference when the wavelength is not known
        In the case of tuner lock search, tuner only acknowledges wave index from lock search
        Invert option is useful to filter out the wave index of interest

        >> OpticalWaves({1310, 1311, 1312}).filter_by_wave_idx(1)
        >> OpticalWaves({1311})
        >> OpticalWaves({1310, 1311, 1312}).filter_by_wave_idx(1, invert=True)
        >> OpticalWaves({1310, 1312})
        """
        # TODO: better way to do this?
        if invert:
            return OpticalWave(set(self.wavelengths) - set([self.wavelengths[wave_idx]]))
        else:
            return OpticalWave(self.wavelengths[wave_idx])
    
    def get_wavelength(self, wave_idx: int) -> float:
        """Get wavelength by wave index
        It models wavelength retrieval with the wave index as a reference when the wavelength is not known
        In the case of tuner lock search, tuner only acknowledges wave index from lock search

        >> OpticalWaves({1310, 1311, 1312}).get_wavelength(1)
        >> 1311
        """
        return self.wavelengths[wave_idx]

    #  def pop(self, index: int = -1) -> float:
    #      """Pop a wavelength from the set of wavelengths
    #      Nasty override pop method to model wavelength filtering with index operator
    #      Useful when defining a tuner behavior where search operation finds the index of the wavelength from incoming waves
    #      and then the tuner filters the wavelength from the set of incoming waves with the index operator
    #
    #      >> waves = OpticalWaves({1310, 1311, 1312})
    #      >> waves.pop(0)
    #      >> waves
    #      >> OpticalWaves({1311, 1312})
    #      """
    #      return self.wavelengths.pop(index)
    


if __name__ == "__main__":
    optical_waves = OpticalWave({1310, 1311, 1312})
    for w in optical_waves:
        print(w)

    optical_waves_empty = OpticalWave()
    if optical_waves_empty.wavelengths is None:
        print("Empty optical waves")






