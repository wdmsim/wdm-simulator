.. _pitch:

===============
What is WDMSim?
===============

What does it solve?
==================

A microring-based DWDM transceiver facilitates the scaling of bandwidth density by allowing a PHY-level serialization/deserialization (SERDES) of data streams in the optical *wavelength* domain.
It does so by using a narrow-band optical resonator, called a microring, to modulate and demodulate the data selectively at a target wavelength, while a split-and-combine is done naturally via optics.
A typical architecture thus assumes a high degree of waveguide bus sharing, where multiple microrings are connected to a common waveguide and share the same optical path, maximizing the spatial/spectral efficiency of the transceiver.

However, a challenge arises due to the physical bus sharing that causes a contention for the shared resource, which in this case is a set of available wavelengths.
Microring is prone to high process variations; its resonance should be tuned to a specific wavelength.
Multiple microrings can be tuned to the same wavelength, which can be viewed as a contention for the same wavelength resource. 
Furthermore, microrings closer to the light source have a higher priority in accessing the shared bus, which then leads to a *wavelength stealing* problem, adding non-trivial complexity to the arbitration strategy.

Thus, a multi-microring design calls for a sophisticated arbitration strategy that is robust and scalable, and this is where *WDM-Simulator* comes in.


How does it solve?
==================

Core abstraction to the simulator is the **wavelength-domain projection**, where microrings are controlled in a synchronized coarse-granular lock-step.
Lock-step is quantized to the major system state changes, such as wavelength search (sweep), wavelength lock and unlock.
For simplicity, we assume the intermediate control states are handled by the circuit-level details, which we set as beyond the scope of the simulator and the said abstraction.

However, to model the wavelength-domain interactions, we need to consider the following:

- wavelength contention: multiple microrings can be tuned to the same wavelength, and the arbitration strategy should resolve the contention.
- wavelength stealing: microrings closer to the light source have a higher priority in accessing the shared bus, and the arbitration strategy should handle this.
To account for these, we consider the spatial domain; microrings are placed in a row, and the simulator propagates the wavelength state along the row *at time-step update*.
Therefore, it updates the wavelength *state* with cognizance of both time and spatial domain.

This concept is implemented through the :class:`RingRxWDMRow` and :class:`SystemUnderTest` classes. 



Why does it solve?
==================

System designs require propagations of design parameters in a rightful way; in this case, one would either attempt to derive the system yield from a given specification or derive the specification for the target yield.
This simulator ties the two ends of the spectrum by providing a platform to 1) propagate the effect of the device variation parameters to the system-level, and 2) study the microring arbitration/allocation schemes in both system/device-level contexts.

To this end (and along with the various interactive/debug features), the simulator attempts to provide a comprehensive view on the microring arbitration/allocation in the context of DWDM transceivers.
