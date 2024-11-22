.. _install:

====================
Installation & Setup
====================


Installation
============

Clone this repo and pip install it in your environment.

.. code-block:: shell

    # WDMSim recommends 3.7 <= python <= 3.10, but also works with 3.6.9 (redhat default)
    git clone <this_repo>
    cd <this_repo>
    pip install -e .


Pypi index will be published as soon as the software reaches the stable version. 
Until then, please install it from the source.
As like other software packages, we recommend using conda or venv to create a clean environment for WDMSim.


Setup
=====

To enhance usability, we attach the algorithm codes at simulator runtime.
This allows the user to add or modify the algorithms without recompiling the simulator.
The added complexity is that the user should set the environment variable **WDMSIM_ARBITER_PATH** to the directory containing the arbitration codes.

**Run the following commands on your session before running WDMSim.**

.. code-block:: bash

    export WDMSIM_ARBITER_PATH=/path/to/your/arbiters/dir
    export PYTHONPATH=$WDMSIM_ARBITER_PATH/..:$PYTHONPATH


.. note::
    If you need to write an algorithm in C++ and plug to the simulator through pybind11, you need to add a specific entry to the `setup.py` and recompile the simulator. Please refer to the :ref:`advanced_setup` section for more information.


Check Your Setup
================

You can run WDMSim in your terminal.

.. code-block:: shell

    $ wdmsim --help

which will show you the following help message.

.. code-block::

    Usage: wdmsim [OPTIONS] COMMAND [ARGS]...

      CLI interface to the simulator

    Options:
      --help  Show this message and exit.

    Commands:
      run            Run a single experiment
      compare        Run a e2e comparison experiment
      stat           Run a statistics
      debug          Debug mode
      sweep          Run a sweep of experiments
      sweep-compare  Run a sweep of compare experiments
      plot           Plot from sweep
      plot-compare   Plot from sweep-compare
      record         Record a single experiment
      replay         Replay a single experiment
      list-arbiter   List available arbiters

``WDMSIM_ARBITER_PATH`` should setup your arbiters directory. To check this, run the following command.

.. code-block:: console

    $ export WDMSIM_ARBITER_PATH=<repo>/examples
    $ wdmsim list-arbiter
    Directories: (Set by $WDMSIM_ARBITER_PATH)
      /Users/sunjinchoi/workspace/wdmsim/release/wdm-simulator/examples
    Available arbiters: [index: arbiter]
       0: example_one_by_one

Also, add the parent directory of the arbiters to the PYTHONPATH.
This allows you to import the arbiters in your python code, with the namespace `<arbiter_directory>`.

.. code-block:: console

    $ export PYTHONPATH=$WDMSIM_ARBITER_PATH/..:$PYTHONPATH
    $ python
    >>> import examples.example_one_by_one


Advanced Setup
==============

Binding C++ code into the arbiter code requires a re-compilation of the simulator.
To do this, you need to add the C++ code to the ``setup.py`` file and recompile the simulator.

We provide a shortcut by adding the path to the environment variable and rebuilding the simulator.

.. code-block:: console

    $ export WDMSIM_ARBITER_PATH=/path/to/your/arbiters/dir
    $ # Make sure the C++ code is in the arbiter directory
    $ pip install -e .

This auto-searches the C++ code in the arbiter directory and compiles it into the simulator.

If you binded the C++ code in this way, you can import the C++ code in the python code as follows.

.. code-block:: console

    $ export PYTHONPATH=$WDMSIM_ARBITER_PATH/..:$PYTHONPATH
    $ python
    >>> # namespace is <arbiter_dir>
    >>> from <arbiter_dir>.<cpp_file> import <cpp_func>

