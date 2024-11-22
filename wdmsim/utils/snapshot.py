"""
A suite of debuggers
This includes
- snapshot

In future,
- trace
- breakpoint
- watch
"""

from copy import deepcopy

from wdmsim.models.laser_grid import LaserGrid
from wdmsim.models.ring_row import RingRxWDMRow
# from wdmsim.state_machines.base_arbiter import BaseArbiter
# from wdmsim.state_machines.arbiter_state import ArbiterState


class Snapshot:
    """snapshots class
    This class implements a simulation snapshot capture to record the state of the simulation at each time step
    It is not intended to be handling a variety of functions, rather a simple data encapsulation and type checks

    Attributes:
        sut (SystemUnderTest): The system under test
        laser_grid (LaserGrid): The laser grid
        system_clock (int): The system clock
        ring_wdm_row (RingRxWDMRow): The ring WDM row
        arbiter (AbstractArbiter): The arbiter
    """
    def __init__(self, system_clock: int, ring_wdm_row: RingRxWDMRow, arbiter: BaseArbiter, laser_grid: LaserGrid):
        """Constructor for the snapshot class
        """
        self.laser_grid = laser_grid
        self.system_clock = system_clock

        # do a deep copy of the ring row to avoid any reference issues
        self.ring_wdm_row = deepcopy(ring_wdm_row)

        # Get arbiter states
        self.arbiter_state = {'state_name': f"{arbiter.state}"}
        # if arbiter has rx_slice_indices variable, then add it to the arbiter state
        if hasattr(arbiter.state, "rx_idx"):
            self.arbiter_state.update({'target_slices': arbiter.state.rx_idx})
        
        

    


