.. _first_script:


=========================
Running Your First Script
=========================


Understanding SUT Parameters
============================

We first briefly explain the parameters of your system-under-test (SUT).
For microrings:

- `ring_wavelength`: resonant wavelength of the microring (post-fabrication)
- `fsr`: free spectral range of the microring
- `tuning_range`: tuning range of the microring

For now, we assume the red-shift tuning mechanism (i.e., tuning range is single-sided) and ignore the fsr variation by dispersion.
Since we only consider the wavelength-domain, any coupling conditions or power levels are not included as parameters.

For lasers:

- `laser_wavelength`: target laser grid wavelengths

A unique system-level parameter we introduce here is *initial/target lane order* which defines the spectral ordering of microrings.
We assume a simple bus topology with a single shared waveguide bus, and microrings are indexed from 0 to N-1 counted from the light input side.

- `initial_lane_order`:  spectral ordering of microrings at the beginning of the simulation (== post-fabrication)
- `target_lane_order`: spectral ordering of microrings at the end of the simulation (== post-tuning)

For example, if you have 4 microrings and the initial lane order is [0, 1, 2, 3], then the initial wavelengths are in the monotonic order from the input side.
If the target lane order is [3, 2, 1, 0], then the final wavelengths are in the reverse order.


Understanding Run Script
============================

After defining the parameters, instantiate the system under test (sut) object and the laser grid object.
Note that the system under test should be instantiated with the arbiter algorithm class, which implements the algorithm of interest.
Then, calling the :func:`SystemUnderTest.run_lock_sequence` will run the experiment at the specified verbosity level.

See ``examples/run_arbiter.py`` for the full script.

.. code-block:: python

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


Verbose flag is set to True to print the detailed log messages in the terminal (:func:`setup_logger`).


Understanding Arbiter Definition
================================

We provide the example arbiter definition under ``examples`` directory.

.. code-block:: python

    # example_arbiter.py

    from wdmsim.arbiter.base_arbiter import BaseArbiter
    from wdmsim.arbiter.arbiter_factory import arbiter_factory
    from wdmsim.arbiter.arbiter_instr import SearchInst, LockInst, UnlockInst

    # register the arbiter class to the factory
    # the register_str_id is the string id that will be used to refer to this arbiter in the CLI
    @arbiter_factory(register_str_id="example_one_by_one")
    class SimpleArbiter(BaseArbiter):
        # override algorithm function to implement the arbiter algorithm
        def algorithm(self):
            # set lock sequence before start running an algorithm
            if self.target_lane_order:
                slice_lock_sequence = [self.target_lane_order.index(lane) for lane in self.target_lane_order]
            else:
                slice_lock_sequence = list(range(self.num_slices))

            # loop through the lock sequence and issue LockInst to each slice
            # for each iteration, yield to update the lock-step
            for rx_idx in slice_lock_sequence:
                LockInst(self, rx_idx, "least_significant", 0).run()
                if self.check_lock_done(rx_idx) and not self.check_zero_lock(rx_idx):
                    yield
                else:
                    self.lock_error_state = True
                    yield

            # if the sequence is done and not in error state, set end_state to True
            self.end_state = True
            yield


As explained in the previous section, the arbiter class subclasses BaseArbiter and overrides the algorithm function to implement the algorithm.
Also, if you are implementing your own algorithm, then it should be registered to the arbiter factory using the decorator :func:`arbiter_factory` with the ``register_str_id`` argument.
It is then usable by the CLI (which is explained in the next section), and the string id is used to refer to the arbiter in the CLI.

In your python code, you can instantiate the arbiter class and feed into the system under test object constructor as shown in the run script.


Run Your First Script
=====================


Now, run the script:

.. code-block:: console

    $ cd <repo>/examples
    $ python run_arbiter.py


And it will display the following message:

.. toggle:: run-log-first-script

    .. code-block:: console

        [wdmsim.models.tuner] sweep range: [[1259.68, 1264.16], [1268.64, 1273.12], [1277.6, 1282.08], [1286.56, 1291.04], [1295.52, 1300.0], [1304.48, 1308.96], [1313.44, 1317.92], [1322.4, 1326.88], [1331.36, 1335.84]]
        [wdmsim.models.tuner] incoming wavelengths [1305.52, 1307.76, 1310.0, 1312.24]
        [wdmsim.models.tuner] sweep range: [[1262.02, 1266.5], [1270.98, 1275.46], [1279.94, 1284.42], [1288.9, 1293.38], [1297.86, 1302.34], [1306.82, 1311.3], [1315.78, 1320.26], [1324.74, 1329.22], [1333.7, 1338.18]]
        [wdmsim.models.tuner] incoming wavelengths [1305.52, 1307.76, 1310.0, 1312.24]
        [wdmsim.models.tuner] sweep range: [[1264.16, 1268.64], [1273.12, 1277.6], [1282.08, 1286.56], [1291.04, 1295.52], [1300.0, 1304.48], [1308.96, 1313.44], [1317.92, 1322.4], [1326.88, 1331.36], [1335.84, 1340.32]]
        [wdmsim.models.tuner] incoming wavelengths [1305.52, 1307.76, 1310.0, 1312.24]
        [wdmsim.models.tuner] sweep range: [[1266.3, 1270.78], [1275.26, 1279.74], [1284.22, 1288.7], [1293.18, 1297.66], [1302.14, 1306.62], [1311.1, 1315.58], [1320.06, 1324.54], [1329.02, 1333.5], [1337.98, 1342.46]]
        [wdmsim.models.tuner] incoming wavelengths [1305.52, 1307.76, 1310.0, 1312.24]
        [wdmsim.models.system_under_test] Target Ring->Laser ordering
        R0 -> L0, R1 -> L1, R2 -> L2, R3 -> L3
        [wdmsim.models.system_under_test] Target Laser->Ring ordering
        L0 -> R0, L1 -> R1, L2 -> R2, L3 -> R3
        [wdmsim.models.system_under_test] Search Table
        +----+---------+--------+--------+---------+--------+--------+---------+--------+--------+---------+--------+--------+
        |    |    R0/W |   R0/C |   R0/L |    R1/W |   R1/C |   R1/L |    R2/W |   R2/C |   R2/L |    R3/W |   R3/C |   R3/L |
        +====+=========+========+========+=========+========+========+=========+========+========+=========+========+========+
        |  0 | 1305.52 |     59 |      - | 1307.76 |     53 |      - | 1310.00 |     59 |      - | 1312.24 |     65 |      - |
        +----+---------+--------+--------+---------+--------+--------+---------+--------+--------+---------+--------+--------+
        |  1 | 1307.76 |    187 |      - | 1310.00 |    181 |      - | 1312.24 |    187 |      - | 1305.52 |    193 |      - |
        +----+---------+--------+--------+---------+--------+--------+---------+--------+--------+---------+--------+--------+
        [wdmsim.models.tuner] sweep range: [[1259.68, 1264.16], [1268.64, 1273.12], [1277.6, 1282.08], [1286.56, 1291.04], [1295.52, 1300.0], [1304.48, 1308.96], [1313.44, 1317.92], [1322.4, 1326.88], [1331.36, 1335.84]]
        [wdmsim.models.tuner] incoming wavelengths [1305.52, 1307.76, 1310.0, 1312.24]
        [wdmsim.models.tuner] sweep range: [[1262.02, 1266.5], [1270.98, 1275.46], [1279.94, 1284.42], [1288.9, 1293.38], [1297.86, 1302.34], [1306.82, 1311.3], [1315.78, 1320.26], [1324.74, 1329.22], [1333.7, 1338.18]]
        [wdmsim.models.tuner] incoming wavelengths [1307.76, 1310.0, 1312.24]
        [wdmsim.models.tuner] sweep range: [[1264.16, 1268.64], [1273.12, 1277.6], [1282.08, 1286.56], [1291.04, 1295.52], [1300.0, 1304.48], [1308.96, 1313.44], [1317.92, 1322.4], [1326.88, 1331.36], [1335.84, 1340.32]]
        [wdmsim.models.tuner] incoming wavelengths [1310.0, 1312.24]
        [wdmsim.models.tuner] sweep range: [[1266.3, 1270.78], [1275.26, 1279.74], [1284.22, 1288.7], [1293.18, 1297.66], [1302.14, 1306.62], [1311.1, 1315.58], [1320.06, 1324.54], [1329.02, 1333.5], [1337.98, 1342.46]]
        [wdmsim.models.tuner] incoming wavelengths [1312.24]
        [wdmsim.models.system_under_test] Target Ring->Laser ordering
        R0 -> L0, R1 -> L1, R2 -> L2, R3 -> L3
        [wdmsim.models.system_under_test] Target Laser->Ring ordering
        L0 -> R0, L1 -> R1, L2 -> R2, L3 -> R3
        [wdmsim.models.system_under_test] Lock Allocation Table
        +----+---------+--------+--------+---------+--------+--------+---------+--------+--------+---------+--------+--------+
        |    |    R0/W |   R0/C |   R0/L |    R1/W |   R1/C |   R1/L |    R2/W |   R2/C |   R2/L |    R3/W |   R3/C |   R3/L |
        +====+=========+========+========+=========+========+========+=========+========+========+=========+========+========+
        |  0 | 1305.52 |     59 |      L | 1307.76 |     53 |      L | 1310.00 |     59 |      L | 1312.24 |     65 |      L |
        +----+---------+--------+--------+---------+--------+--------+---------+--------+--------+---------+--------+--------+
        |  1 | 1307.76 |    187 |      - | 1310.00 |    181 |      - | 1312.24 |    187 |      - | 1305.52 |    193 |      - |
        +----+---------+--------+--------+---------+--------+--------+---------+--------+--------+---------+--------+--------+
        [wdmsim.models.system_under_test] lock_wavelengths: [1305.52, 1307.76, 1310.0, 1312.24]
        [wdmsim.models.system_under_test] System is locked: 0, return with status code 0

        [wdmsim.models.system_under_test] Arbiter: SimpleArbiter
        [wdmsim.models.system_under_test]
         _       ___    ____  _  __  ____   _   _   ____   ____  _____  ____   ____
        | |     / _ \  / ___|| |/ / / ___| | | | | / ___| / ___|| ____|/ ___| / ___|
        | |    | | | || |    | ' /  \___ \ | | | || |    | |    |  _|  \___ \ \___ \
        | |___ | |_| || |___ | . \   ___) || |_| || |___ | |___ | |___  ___) | ___) |
        |_____| \___/  \____||_|\_\ |____/  \___/  \____| \____||_____||____/ |____/


Log message will display:

- Sweep range and incoming wavelengths for each microring (from the first to the last in the bus)
- Target ring-to-laser and laser-to-ring ordering
- Microring search table and lock allocation table

  - Visible wavelengths within the tuning range and the incoming wavelengths (W)
  - Corresponding tuner codes (C)
  - Microring lock status (L)


What's Next?
============

In the next section, we will explain a batch simulation mode which is one of the powerful features of the WDMSim.

