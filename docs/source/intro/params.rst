.. _params:


======================
Configuring Simulation
======================

In the next two sections, we explain the batch simulation mode through command-line interface (CLI).
Handful of parameters are required for the batch simulation due to the statistical nature of the target system.
We explain the parameters and their configurations in this section, and the next section explains how to run the simulation with the given parameters.


.. note::

    For now, we only support a uniform distribution for the statistical variations. We use this as a pessimistic estimation of the trimmed Gaussian. However, we plan to support user-defined variation statistics in the future.



Parameter Definitions
==========================

Note that our target system is fairly complex: it consists of multiple devices, each of which has multiple parameters.
Since a typical PIC environment is prone to fabrication/environmental variations, WDMSim's batch-mode configures their input statistics and tries to observe the output statistics of our interest.

For microrings:

- `fsr_mean` (floating point number, in nm unit)
- `fsr_variance` (floating point number, in %/100 unit)
- `tuning_range_mean` (floating point number, in nm unit)
- `tuning_range_variance` (floating point number, in %/100 unit) 
- `resonance_variance` (floating point number, in nm unit)
- `inherit_laser_variance` (boolean)

For lasers:

- `num_channel` (integer)
- `center_wavelength` (floating point number, in nm unit) 
- `grid_spacing` (floating point number, in nm unit)
- `grid_max_offset` (floating point number, in nm unit)
- `grid_variance` (floating point number, in %/100 unit)

For lane orderings:

- `alias` (string)
- `lane` (see below for details)


Most of the parameters are self-explanatory, and we explain in the next section how to configure them and pass to the simulator.
Note that `variance` sets the confidence interval bound of the statistical variation distribution, which we assume to be uniform for now.


.. caution::

    Namings are not mature at the time. For example, `variance` is rather a misnomer, and will be renamed to `variation` in the future. `num_channel`, `center_wavelength`, and `grid_spacing` is a DWDM parameter, which will be refactored into a separate group in the future. We will update the documentation accordingly.



Parameter Marshalling
=====================

Due to the complexity of the system, a YAML format will be used to pass the parameters to the simulator.

For example, we define a YAML format for the parameters in a following way:

.. code-block:: yaml

    # Laser Config Section 1 with Key "msa-8-grid-200G"
    msa-8-grid-200G:
      run: SINGLE
      type: LASER
      attribute:
        num_channel: 8
        center_wavelength: 1300.05e-9
        grid_spacing: 1.12e-9
        grid_max_offset: 15.0e-9
        grid_variance: 0.25

    # Laser Config Section 2 with Key "msa-8-grid-200G-sweep-var"
    msa-8-grid-200G-sweep-var:
      run: SWEEP
      type: LASER
      attribute:
        num_channel: 8
        center_wavelength: 1300.05e-9
        grid_spacing: 1.12e-9
        grid_max_offset: 15.0e-9
        grid_variance:
          run: 'LINEAR'
          start: 0.001  
          stop: 0.45
          num: 50

Each YAML file contains number of sections referenced by the key, which in this case is *msa-8-grid-200G* and *msa-8-grid-200G-sweep-var*.
Each section contains the following fields:

- `run`: The run mode of the simulation. It can be either `SINGLE` or `SWEEP`.
- `type`: The type of the device. It can be either `LASER` or `RING` or `LANEORDER`.
- `attribute`: The device-specific parameters. The parameters are defined in the previous section. 

Expected schema for the YAML file is as follows:

.. code-block:: yaml

    <section_key>:
      run: [SINGLE|SWEEP]
      type: [LASER|RING|LANEORDER]
      attribute:
        param1: value1
        param2: value2
        ...

For sweep variables, you can specify as either a list or a linear sweep.

.. code-block:: yaml

    # *Note* run key should be specified as 'SWEEP' if it contains attributes with sweep values.
    # Linear Sweep
    param1:
      run: 'LINEAR'
      start: <start_value>
      stop: <stop_value>
      num: <num_values>

    # List Sweep
    param2:
      - value1
      - value2
      ...

.. note::

    For now, we don't support sweep configs for LANEORDER. This will be supported in the future.


Below, we show an example of each configuration.

Laser Configurations
~~~~~~~~~~~~~~~~~~~~~

Example config section:

.. code-block:: yaml

    msa-8-grid-400G:
      run: SINGLE
      type: LASER
      initialize: GRID
      attribute:
        num_channel: 8
        center_wavelength: 1300.05e-9
        grid_spacing: 2.24e-9
        grid_max_offset: 15.0e-9
        grid_variance: 0.25

This will generate a DWDM laser grid device pool with 8 channels, centered at 1300.05 nm, with a grid spacing of 2.24 nm.
The grid variance is set to 0.25, which means the **local** grid variation is 25% of the grid spacing, both in the positive and negative directions.
The grid max offset is set to 15 nm, which means the **global** grid variation is 15 nm in the positive and negative directions.


Ring Configurations
~~~~~~~~~~~~~~~~~~~

Example config section:

.. code-block:: yaml

    msa-8:
      run: SINGLE
      type: RING  
      attribute:
        fsr_mean: 8.96e-9
        fsr_variance: 0.01
        tuning_range_mean: 4.48e-9
        tuning_range_variance: 0.10
        inherit_laser_variance: false
        resonance_variance: 2.0e-9

This will generate a ring device pool with a free spectral range of 8.96 nm, with a variance of 1%. The tuning range is 4.48 nm, with a variance of 10%. 
The resonance variance is the **local** ring resonance variation, which in this case is 2 nm in the positive and negative directions.
If inherit_laser_variance is set to true, the ring variation is overridden by the laser variation (`grid_variance` key in the laser configuration). In most cases, you want to set this to false.

.. note::

    One of the critical microring resonance variation factors is the global resonance variation. However, from the simulation perspective, laser and ring global variations are essentially indistinguishable. Therefore, we only specify the global variation in the laser configuration, which we assume to be considering 


Lane Order Configurations
~~~~~~~~~~~~~~~~~~~~~~~~~

Example config section:

.. code-block:: yaml

    any:
      run: SINGLE  
      type: LANEORDER  
      attribute:
        alias: 'ANY'
        lane: null
     

    linear_8:
      run: SINGLE
      type: LANEORDER  
      attribute:
        alias: 'LINEAR'
        lane:
          0: 0
          1: 1
          2: 2
          3: 3
          4: 4
          5: 5
          6: 6
          7: 7


This is used to define a microring spectral orderings, namely "initial" and "target" as we defined in the simulator.

Initial ordering is the microring spectral ordering at **design** time i.e., if initial ordering is [0, 1, 2, 3], the microring spectral ordering from the first to the last on the bus is 0, 1, 2, 3 (spaced by `grid_spacing` originally) which is then added by the microring local variation numbers.

Target ordering is the microring spectral ordering **post-arbitration** i.e., if target ordering is [3, 2, 1, 0], the microring spectral ordering from the first to the last on the bus will be aligned with the laser grids in [3, 2, 1, 0] order after arbitration.

Note that target ordering can be "any", which means that we don't specify a target lane ordering. This corresponds to the lane key being `null` as above snippet.


Two attributes are specified for the `LANEORDER` type: `alias` and `lane`. `alias` is a string that is only used for the log messages, whereas `lane` is a dictionary that specifies the initial or target spectral orderings.
The keys in `lane` corresponds to the microring indices in the bus (spatial domain, counted from the light input side), and the values are the corresponding spectral indices (wavelength domain, 0 being the lowest wavelength).



What's Next?
============

In the next section, we will explain how to run the batch simulation with parameters specified as above.

