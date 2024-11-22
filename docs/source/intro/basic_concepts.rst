.. _basic_concepts:

==============
Basic Concepts
==============

WDMSim provides a platform for multi-microring lock sequence defined by the user - as we call it a custom **arbiter**. 
From a simplified OOP perspective, the simulator models each component with a dedicated class, such as microrings, lasers, arbiters, system-under-test, etc.


System Components
=================

Each component in the system is designed to retain its local view of the system, and interact with other components through a logical interface.
WDMSim provides a set of pre-defined model templates that are used to assemble the system-under-test during the simulation runtime.
We explain the different tiers of system components below:

Barebone components are defined to encapsulate the core parameters, and are more for the stricter object-orientedness.

* Microring: barebone microring parameter capsule (:class:`wdmsim.models.ring_row.Ring`)
* Laser: barebone laser parameter capsule (:class:`wdmsim.models.laser_row.Laser`)

Functional unit components model the component-level behaviors, mostly centric to updating the wavelength states (:class:`wdmsim.models.optical_wave.OpticalWave`).
Optical ports are defined for the directivity of the light propagation (:class:`wdmsim.models.optical_port.OpticalPort`).

* Microring Row: microring array with ports (:class:`wdmsim.models.ring_row.RingRxWDM` and :class:`wdmsim.models.ring_row.RingRxWDMRow`)
* Laser Grid: aggregated CW laser array with ports (:class:`wdmsim.models.laser_row.LaserGrid`)
* Tuner: local tuner for a single microring control (:class:`wdmsim.models.tuner.Tuner`)

System components are the top-level components that are built off the functional units or their interfaces.
Note that some of the definitions may seem redundant, they are kept for the sake of modularity *idiom* where no single components overstep their physical boundaries.

* RxSlice: microring + tuner slice (:class:`wdmsim.models.rx_slice.RxSlice`)
* Arbiter: arbiter controlling the slices with the implementing algorithm, see next section
* System-Under-Test: assembled system-under-test for the allocation experiments (:class:`wdmsim.models.system_under_test.SystemUnderTest`)


Defining Arbiter
================

While other components are mostly passive in their interfaces, the arbiter has the distinct features of 1) controlling the system components, and 2) implementing the lock-step algorithm.
Subclassing the base arbiter class (:class:`wdmsim.arbiter.base_arbiter.BaseArbiter`), the user can define their own algorithm.
In particular, a predefined set of instructions (:class:`wdmsim.arbiter.arbiter_instr.InstTemplate`) provides a closed interface for the arbiter to interact with the attached slices.
This includes `SearchInst`, `LockInst` and `UnlockInst` instructions:

* `SearchInst`: issues wavelength sweep on the target slice and updates the search table
* `LockInst`: locks the slice to the target wavelength
* `UnlockInst`: unlocks the slice

To implement a custom arbiter, the user can simply:

1. Subclass the `BaseArbiter` class
2. Override the :func:`algorithm` method to implement the lock-step algorithm
3. Set :attr:`end_state` or :attr:`lock_error_state` to True to indicate the end of the lock sequence


After such instructions are issued in :func:`algorithm`, corresponding information is updated in the arbiter's internal state (as `ArbiterMemory`) which the arbiter can decide the final allocation.
Using the interface allows the arbiter to operate without knowing the "absolute" wavelength state in floating-point values, and instead rely on the logical state of the system only.
However, as python allows any objects' internals to be accessed, and as we also implemented a "backdoor" access to the tuner state (:attr:`Tuner.search_wavelength`), it is possible to write a code that operates on the absolute wavelength numbers.


Simulator Lock-Step Update
==========================

Lastly, we explain the lock-step update mechanism.

It is non-trivial to write an efficient state update mechanism, our update mechanism is designed to be simplistic since the major state update is only native to the system-level.
A relaxed form of lock-step update is implemented in the `SystemUnderTest` and the `BaseArbiter.`
Note that WDMSim is not designed to be waveform-accurate; if the user needs to simulate those details, they should consider using a more detailed simulator.

For example, inside :func:`SystemUnderTest.run_lock_sequence`:

.. code-block:: python

    # First, arbiter advances by a tick
    # Then, the internal wavelength state is updated by light propagation in the microrings
    # which is then polled/used by any other components in the system
    while self.arbiter.tick():
        self.ring_wdm_row.propagate_wave()


At update, the arbiter should advance its FSM state by a tick. 
There are many ways to implement this state-machine behaviors in python, one of which is the state-machine pattern.
However, we observed that the state-machine pattern easily becomes cumbersome and hard to write (with possible bloating classes corresponding to the number of states).
Instead, we opted for a simpler approach: using `yield` to pause the execution of the algorithm at each tick.

See below snippets as an example implementation:

.. code-block:: python

    class ArbiterA(BaseArbiter):
        def algorithm(self):
            slice_sequence = [i for i in range(8)]
            for slice_idx in slice_sequence:
                # Issue a lock instruction to the target slice
                LockInst(self, slice_idx, "least_significant", 0).run()
                # Pause the execution and let the system update the wavelength states
                yield

    class ArbiterB(BaseArbiter):
        def algorithm(self):
            slice_sequence = [i for i in range(8)]
            # Issue lock instructions to all slices at once
            for slice_idx in slice_sequence:
                LockInst(self, slice_idx, "least_significant", 0).run()
            # System update is done at the end
            yield       


The `yield` statement marks the point where the arbiter pauses its execution and returns to the :class:`SystemUnderTest` to update the wavelength states. 
Here, :class:`ArbiterA` locks the slices one by one, while :class:`ArbiterB` locks all slices at once.
Using this style, a more complicated algorithm along with the arbitraty mix of `SearchInst`, `LockInst` and `UnlockInst` can be implemented in a more readable manner.
Better off, the user can freely use function-local variables and share between states, and implement a multi-level FSM using nested generators (in this case, caller should use **yield from** to call the callee, while callee should use either **yield** or **return** to return to the caller).


What's Next?
============

In the next section, we will walk-through a simple run example of the WDMSim.


