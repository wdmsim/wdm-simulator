

import logging

from wdmsim.models.system_under_test import SystemUnderTest
from wdmsim.models.laser_grid import LaserGrid
from wdmsim.utils.logger import setup_logger
from examples.example_arbiter import SimpleArbiter

logger = logging.getLogger(__name__)

# Define the parameters for the devices and the system
simple_ring_params = {"fsr": 8.96e-9, "tuning_range": 4.48e-9}

channel_spacing = 2.24e-9
resonance_wavelengths_postfab = [
    1300e-9 - 2 * channel_spacing,
    1300e-9 - 1 * channel_spacing + 0.1e-9,
    1300e-9 + 0 * channel_spacing,
    1300e-9 + 1 * channel_spacing - 0.1e-9,
]

laser_wavelengths = [
    1310e-9 - 2 * channel_spacing,
    1310e-9 - 1 * channel_spacing,
    1310e-9 + 0 * channel_spacing,
    1310e-9 + 1 * channel_spacing,
]

init_lane_order = [i for i in range(4)]
target_lane_order = init_lane_order
# target_lane_order = None


if __name__ == "__main__":

    # define verbosity
    setup_logger(log_fpath=None, verbose=True)

    # Build the system under test
    dwdm_under_test = SystemUnderTest.construct_slices_and_arbiter(
        ring_row_params = [simple_ring_params] * 4,
        ring_wavelengths = resonance_wavelengths_postfab,
        init_lane_order = init_lane_order,
        arbiter_cls = SimpleArbiter,
        tgt_lane_order = target_lane_order,
    )

    # Define the target laser grid
    laser_target = LaserGrid.from_wavelengths(laser_wavelengths)

    # Run the lock sequence
    dwdm_under_test.run_lock_sequence(
        laser_grid=laser_target, 
        plot_snapshot=False, 
        plot_statistics=False,
    )
