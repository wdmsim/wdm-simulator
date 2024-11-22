
from typing import Dict, List
from pathlib import Path
import importlib
import sys
import os
import inspect
import logging

from wdmsim.arbiter.base_arbiter import BaseArbiter

logger = logging.getLogger(__name__)

arbiter_registry : Dict[str, BaseArbiter] = BaseArbiter._registry

def arbiter_factory(register_str_id: str):
    def register(arb_cls: BaseArbiter):
        # arb_cls.__init_subclass__(register_str_id=register_str_id)
        arbiter_registry[register_str_id] = arb_cls
        return arb_cls
    return register

"""
Auto-discovery method
"""
def _is_arbiter_class(cls):
    return inspect.isclass(cls) and issubclass(cls, BaseArbiter) and cls != BaseArbiter

def discover_arbiter_modules(arbiter_dirs: List[Path]):
    for arbiter_dir in arbiter_dirs:
        if arbiter_dir.exists() and arbiter_dir.is_dir() and os.access(arbiter_dir, os.R_OK):
            # Add the arbiter path to the system path
            if str(arbiter_dir) not in sys.path:
                sys.path.append(str(arbiter_dir))

            # Discover all the arbiter modules in the directory
            for file_path in arbiter_dir.iterdir():
                if file_path.is_file() and file_path.suffix == '.py' and file_path.stem != '__init__':
                    # construct the module name
                    module_name = file_path.stem
                    # import the module
                    spec = importlib.util.spec_from_file_location(module_name, file_path)
                    if spec is not None:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        # Add the module to the system modules
                        sys.modules[module_name] = module

                        # for name, obj in inspect.getmembers(module, _is_arbiter_class):
                        #     # for now, use decorator to register classes
                        #     # arbiter_factory(name)(obj)
                        #     logger.info(f"Discovered arbiter class: {name} in module: {module_name}")


