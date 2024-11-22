

from typing import List, Optional, Union
from enum import Enum, auto

from wdmsim.models.optical_wave import OpticalWave
from wdmsim.models.sim_instance import SimInstance

class OpticalPortType(Enum):
    """Enum for optical port types."""
    IN = auto()
    OUT = auto()

class OpticalPort:
    """
    This class defines an optical port of an instance of a device.
    It only needs to establish the logical connectivity between the ports
    and carry the optical signals.
    Currently assuming point-to-point and unidirectional connection.
    """
    def __init__(self, device: SimInstance, name: str, port_type: OpticalPortType) -> 'OpticalPort':
        self.name : str = name
        self.device = device
        self.port_type = port_type

        self.port_conn : Optional[OpticalPort] = None
        self.is_connected : bool = False

        self.wave : OpticalWave = OpticalWave()

    def __str__(self):
        return f"OpticalPort({self.device}:{self.name})"

    def __repr__(self):
        return f"OpticalPort({self.device}:{self.name})"

    @property
    def wavelengths(self) -> List[float]:
        """
        Return the wavelengths of the wave
        """
        return self.wave.wavelengths

    def conn(self, from_port: 'OpticalPort') -> None:
        """
        Connection setter
        It establishes unidirectional connectivity.
        """
        assert from_port.port_type == OpticalPortType.OUT, "Only OUT port can be connected"
        assert self.port_type == OpticalPortType.IN, "Only IN port can be connected"

        self.port_conn = from_port
        self.is_connected = True
    
    def propagate_wave_from_conn(self) -> None:
        """
        Propagate the wave to the connected port
        """
        if self.is_connected:
            self.wave = self.port_conn.wave

    # @property
    # def wave(self) -> OpticalWave:
    #     """
    #     Waves property getter.
    #     """
    #     return self.wave
    #
    # @wave.setter
    # def wave(self, wave: OpticalWave) -> None:
    #     """
    #     Waves property setter.
    #     If it has a connection, set waves at the connected port as well
    #     """
    #     self.wave = wave
   # 


    # @classmethod
    # def init_port_with_wavelengths(cls,
    #                                device: Union[Ring, Laser],
    #                                name: str,
    #                                wavelengths: Union[float, list]) -> 'OpticalPort':
    #     """
    #     Class method to initialize an optical port with a list of wavelengths.
    #     """
    #     port = cls(name, device)
    #     port.wave = OpticalWave(wavelengths)
    #     return port


# if __name__ == "__main__":
#     port_in = OpticalPort("in", Ring(1300e-9, 10e-9, 1e-9))
#     port_thru = OpticalPort("thru", Ring(1310e-9, 10e-9, 1e-9))
#
#     port_in.conn(port_thru)
#     import pdb; pdb.set_trace()
