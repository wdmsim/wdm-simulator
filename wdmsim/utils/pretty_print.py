
import logging

from wdmsim.schemas.design_params import LaneOrderParams, LaserDesignParams, RingDesignParams


# aesthetic
def str_pad_align(txt: str, pad='=', text_print_width=80) -> str:
    return txt.center(text_print_width, pad)

def pad_print(pad='=') -> str:
    return str_pad_align('', pad)

def str_print(txt: str, pad='=') -> str:
    return str_pad_align(f" {txt} ", pad)


# run function header
def print_run_header(
    laser_config_file: str,
    laser_config_section: str,
    ring_config_file: str,
    ring_config_section: str,
    init_lane_order_config_file: str,
    init_lane_order_config_section: str,
    tgt_lane_order_config_file: str,
    tgt_lane_order_config_section: str,
    laser_design_params: LaserDesignParams,
    ring_design_params: RingDesignParams,
    init_lane_order_params: LaneOrderParams,
    tgt_lane_order_params: LaneOrderParams,
    arbiter_of_choice: str,
) -> None:
    """Print log header
    Aesthestics are important for main function runs

    """
    logging.info(pad_print())
    log_header = "WDM Simulator"
    logging.info(str_print(log_header))
    logging.info(pad_print())

    # print config file info
    logging.info(f'[Config]   ::\tfile :: section')
    logging.info(f' laser     ::\t{laser_config_file:<30}\t\t :: {laser_config_section:>12} ')
    logging.info(f' ring      ::\t{ring_config_file:<30}\t\t :: {ring_config_section:>12} ')
    logging.info(f' init_lane ::\t{init_lane_order_config_file:<30}\t\t :: {init_lane_order_config_section:>12} ')
    logging.info(f' tgt_lane  ::\t{tgt_lane_order_config_file:<30}\t\t :: {tgt_lane_order_config_section:>12} ')

    # print laser design parameters
    logging.info(pad_print())
    logging.info(f'[Laser Design Parameters]')
    for k, v in laser_design_params._asdict().items():
        if k != "file" and k != "section":
            logging.info(f'\t{k:<30}\t\t :: {v!s:>12}')

    # print ring design parameters
    logging.info(pad_print())
    logging.info(f'[Ring Design Parameters]')
    for k, v in ring_design_params._asdict().items():
        if k != "file" and k != "section":
            logging.info(f'\t{k:<30}\t\t :: {v!s:>12}')

    # print initial lane order parameters
    logging.info(pad_print())
    logging.info(f'[Initial Lane Order Parameters]')
    # print only alias
    for k, v in init_lane_order_params._asdict().items():
        if k == "alias":
            logging.info(f'\t{k:<30}\t\t :: {v!s:>12}')

    # print target lane order parameters
    logging.info(pad_print())
    logging.info(f'[Target Lane Order Parameters]')
    # print only alias
    for k, v in tgt_lane_order_params._asdict().items():
        if k == "alias":
            logging.info(f'\t{k:<30}\t\t :: {v!s:>12}')

    # print arbiter of choice
    logging.info(pad_print())
    logging.info(f'[Arbiter of Choice]')
    logging.info(f'\t{"class_name":<30}\t\t :: {arbiter_of_choice:>12}')

    # terminate
    logging.info(pad_print())


def format_wavelengths(wavelengths: list, fmt: str = '.2f', scale: int = 1e9) -> str:
    """Format list of wavelengths for printing

    """
    formatted_wavelengths = []
    for wavelength in wavelengths:
        if type(wavelength) == float:
            formatted_wavelengths.append(float(f'{wavelength*scale:{fmt}}'))
        else:
            formatted_wavelengths.append(wavelength)
            
    return formatted_wavelengths
