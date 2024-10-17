

.. image:: ../../.github/images/wdmsim_logo_white.png
	:alt: wdmsim-logo
	:width: 70%

*WDM-Simulator* is a simulator framework for multi-microring wavelength allocation in the context of Dense Wavelength Division Multiplexing (DWDM) transceivers.
With the technology presenting a unique challenge of microring arbitration, the simulator attempts to fill a gap between the conventional PHY-level link simulators and high-level architectural explorations.
The goal is to provide a modular and scalable simulation framework for the evaluation of microring arbitration strategies. 



What does it solve?
===================

A microring-based DWDM transceiver facilitates the scaling of bandwidth density by allowing a PHY-level serialization/deserialization (SERDES) of data streams in the optical *wavelength* domain.
It does so by using a narrow-band optical resonator, called a microring, to modulate and demodulate the data selectively at a target wavelength, while a split-and-combine is done naturally via optics.
A typical architecture thus assumes a high degree of waveguide bus sharing, where multiple microrings are connected to a common waveguide and share the same optical path, maximizing the spatial/spectral efficiency of the transceiver.

However, a challenge arises due to the physical bus sharing that causes a contention for the shared resource, which in this case is a set of available wavelengths.
Microring is prone to high process variations; its resonance should be tuned to a specific wavelength.
Multiple microrings can be tuned to the same wavelength, which can be viewed as a contention for the same wavelength resource. 
Furthermore, microrings closer to the light source have a higher priority in accessing the shared bus, which then leads to a *wavelength stealing* problem, adding non-trivial complexity to the arbitration strategy.

Thus, a multi-microring design calls for a sophisticated arbitration strategy that is robust and scalable, and this is where *WDM-Simulator* comes in.



.. toctree::
   :maxdepth: 3
   :caption: Contents:

   arch

.. getting started
.. arch
.. prg model


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
