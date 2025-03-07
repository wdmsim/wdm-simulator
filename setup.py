"""
    Setup file for wdm-simulator
    Finds pyproject.toml to determine build system
    and configures setup using setup.cfg

    This file was generated with PyScaffold 4.5.
    PyScaffold helps you to put up the scaffold of your new Python project.
    Learn more under: https://pyscaffold.org/
"""
from typing import List
import os
from pathlib import Path
from setuptools import setup
from pybind11.setup_helpers import Pybind11Extension, build_ext

# Discover arbiters from the environment variable
def get_wdmsim_arbiter_path() -> List[Path]:
    path_separator = ":" if os.name != "nt" else ";"
    def parse_env_var(env_var: str) -> List[str]:
        if env_var.find(path_separator) != -1:
            return env_var.split(path_separator)
        else:
            return [env_var]
        
    arb_path_env_var = os.environ.get("WDMSIM_ARBITER_PATH", "")
    if arb_path_env_var != "":
        return [Path(p) for p in parse_env_var(arb_path_env_var)]
    else:
        return None


if __name__ == "__main__":
    try:
        # # setup(use_scm_version={"version_scheme": "no-guess-dev"})
        # setup()

        parsed_arbiter_path = get_wdmsim_arbiter_path()
        if parsed_arbiter_path:
            # setup with pybind cpp extension
            for arbiter_path in parsed_arbiter_path:
                ext_modules = []

                # detect cpp files in the arbiter path
                for cpp_file in arbiter_path.glob("*.cpp"):
                    ext_modules.append(
                        Pybind11Extension(
                            f"{arbiter_path.stem}.{cpp_file.stem}",
                            [cpp_file.relative_to(os.getcwd())],
                            # [cpp_file.absolute()],
                        )
                    )

        else:
            ext_modules = []
            
        setup(
            ext_modules=ext_modules,
            cmdclass={"build_ext": build_ext},
        )

    except:  # noqa
        print(
            "\n\nAn error occurred while building the project, "
            "please ensure you have the most updated version of setuptools, "
            "setuptools_scm and wheel with:\n"
            "   pip install -U setuptools setuptools_scm wheel\n\n"
        )
        raise

