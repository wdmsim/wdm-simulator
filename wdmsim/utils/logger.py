
import logging
from enum import Enum
from pathlib import Path
from typing import Optional


_VERBOSE = logging.DEBUG
_INFO = logging.INFO
# _SILENT = logging.CRITICAL


def setup_logger(log_fpath: Optional[str], verbose: bool = False):
    
    # setup default basic config for the root logger
    root_logger = logging.getLogger()
    if verbose:
        root_logger.setLevel(_VERBOSE)
    else:
        root_logger.setLevel(_INFO)
    root_logger.handlers = []

    # Add a console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(_INFO)
    console_handler_formatter = logging.Formatter('[%(name)s] %(message)s')
    console_handler.setFormatter(console_handler_formatter)

    root_logger.addHandler(console_handler)

    if log_fpath is not None:
        # TODO: check if path is valid

        # Ensure that the parent directory exists
        Path(log_fpath).parent.mkdir(parents=True, exist_ok=True)

        # Add an output file to the root logger
        # overwrite if the file already exists
        file_handler = logging.FileHandler(Path(log_fpath).resolve(), 'w')
        file_handler.setLevel(_VERBOSE)
        file_handler_formatter = logging.Formatter('%(message)s')
        file_handler.setFormatter(file_handler_formatter)

        root_logger.addHandler(file_handler)

    # # Add a rotating file handler to the root logger
    # # overwrite if the file already exists
    # file_handler = logging.RotatingFileHandler(Path(log_fpath).resolve(), 'w', maxBytes=1000000, backupCount=5)
    # file_handler.setLevel(logging.DEBUG)
    # file_handler_formatter = logging.Formatter('%(message)s')
    # file_handler.setFormatter(file_handler_formatter)
    #
    # root_logger.addHandler(file_handler)
    #
