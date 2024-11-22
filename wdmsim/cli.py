"""
Fancy CLI interface to the simulator
"""

import os
import logging
import traceback
from typing import Any, List
from pathlib import Path
import click

import wdmsim.run as wdmsim_run

# import wdmsim.arbiters.arbiter_registry as arbiter_registry
from wdmsim.arbiter.arbiter_factory import arbiter_registry, discover_arbiter_modules


logger = logging.getLogger(__name__)

# Discover arbiters from the environment variable
def discover_from_arbiter_path() -> List[Path]:
    path_separator = ":" if os.name != "nt" else ";"
    def parse_env_var(env_var: str) -> List[str]:
        if env_var.find(path_separator) != -1:
            return env_var.split(path_separator)
        else:
            return [env_var]
        
    arbiter_path = os.environ.get("WDMSIM_ARBITER_PATH", "")
    if arbiter_path:
        parsed_arbiter_path = [Path(p) for p in parse_env_var(arbiter_path) if p]
        discover_arbiter_modules(parsed_arbiter_path)
        return parsed_arbiter_path
    else:
        raise ValueError("Environment Variable WDMSIM_ARBITER_PATH is not set")

# Run at module load for click help message print
discover_from_arbiter_path()

def is_plot_option_set(ctx: click.Context, param: click.Parameter, value: str) -> Any:
    if ctx.params.get('plot') and not value:
        raise click.BadParameter('The option should be set if plot is enabled')
    return value


class _NaturalOrderGroup(click.Group):
    """
    Helper class to display subcommands in natural order 
    ref: https://github.com/pallets/click/issues/513
    """
    def list_commands(self, ctx):
        return self.commands.keys()


_arbiter_choices = list(arbiter_registry.keys())
_arbiter_map = {str(i): arbiter for i, arbiter in enumerate(_arbiter_choices)}

def _format_arbiter_help(formatter: click.HelpFormatter):
    formatter.write("\n")
    formatter.write("Arbiter Options:\n")
    formatter.write(f"  [index]: [arbiter]\n")
    # formatter.write("-" * 50 + "\n")
    for index, arbiter in _arbiter_map.items():
        formatter.write(f"  {int(index):7}: {arbiter}\n")

class ArbiterOption(click.Option):
    def _error(self, header_message: str) -> None:
        click.echo(header_message)
        if self.name == "arbiter":
            click.echo("Syntax: [-a|--arbiter] <name|index>")
        elif self.name == "arbiter_compare":
            click.echo("Syntax: [-ac|--arbiter_compare] <name|index>")
        click.echo(f"[index]: [arbiter]")
        click.echo("-" * 50)
        for index, arbiter in _arbiter_map.items():
            click.echo(f"{int(index):7}: {arbiter}")

    def handle_parse_result(self, ctx, opts, args):
        # Get the value provided by the user
        opt_inputs = opts.get(self.name)
        
        # if self.name not in opts and self.required or opt_inputs is None:
        if self.required and opt_inputs is None:
            msg_missing = "Error: No arbiter choice provided. Available arbiters are:\n"
            self._error(msg_missing)
            ctx.exit()
            # if self.name not in opts:
            #     msg_missing = "Error: No arbiter choice provided. Available arbiters are:\n"
            #     self._error(msg_missing)
            #     ctx.exit()
        
        if opt_inputs:
            # Check if the value is a numeric index and map it to the corresponding arbiter
            if self.multiple:
                opt_inputs_processed = []
                for opt_input in opt_inputs:
                    if opt_input.isdigit() and opt_input in _arbiter_map:
                        # opts[self.name] = _arbiter_map[opt_input]
                        opt_inputs_processed.append(_arbiter_map[opt_input])
                    elif opt_input in _arbiter_choices:
                        # opts[self.name] = opt_input
                        opt_inputs_processed.append(opt_input)
                    elif opt_input not in _arbiter_choices:
                        msg_invalid = f"Error: Invalid arbiter '{opt_input}' provided. Available arbiters are:\n"
                        self._error(msg_invalid)
                        ctx.exit()
            else:
                if opt_inputs.isdigit() and opt_inputs in _arbiter_map:
                    opt_inputs_processed = _arbiter_map[opt_inputs]
                elif opt_inputs in _arbiter_choices:
                    opt_inputs_processed = opt_inputs
                elif opt_inputs not in _arbiter_choices:
                    msg_invalid = f"Error: Invalid arbiter '{opt_input}' provided. Available arbiters are:\n"
                    self._error(msg_invalid)
                    ctx.exit()
        
            opts[self.name] = opt_inputs_processed

        return super(ArbiterOption, self).handle_parse_result(ctx, opts, args)


class WdmSimCommand(click.Command):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Dynamically add options to the command with improved formatting for readability
        self.params.extend([
            # For ArbiterOption, ensure it's defined and properly handles dynamic instantiation.
            ArbiterOption(
                ['-a', '--arbiter'], 
                type=click.STRING, # Assuming a simple string type for demonstration
                required=True, 
                multiple=True, 
                help='Arbiter of choice'
            ),
            click.Option(
                ['-lf', '--laser_config_file'], 
                type=click.Path(exists=True, file_okay=True, dir_okay=False), 
                default='configs/example_laser_config.yml', 
                show_default=True, 
                help='Laser config file'
            ),
            click.Option(
                ['-ls','--laser_config_section'], 
                type=str, 
                default='msa-8', 
                show_default=True, 
                help='Laser config section'
            ),
            click.Option(
                ['-rf','--ring_config_file'], 
                type=click.Path(exists=True, file_okay=True, dir_okay=False), 
                default='configs/example_ring_config.yml', 
                show_default=True, 
                help='Ring config file'
            ),
            click.Option(
                ['-rs','--ring_config_section'], 
                type=str, 
                default='msa-8', 
                show_default=True, 
                help='Ring config section'
            ),
            click.Option(
                ['-ilof','--init_lane_order_config_file'], 
                type=click.Path(exists=True, file_okay=True, dir_okay=False), 
                default='configs/example_lane_order.yml', 
                show_default=True, 
                help='Ring config file'
            ),
            click.Option(
                ['-ilos','--init_lane_order_config_section'],
                type=str, 
                default='linear_8', 
                show_default=True, 
                help='Ring config section'
            ),
            click.Option(
                ['-tlof','--tgt_lane_order_config_file'], 
                type=click.Path(exists=True, file_okay=True, dir_okay=False), 
                default='configs/example_lane_order.yml', 
                show_default=True, 
                help='Ring config file'
            ),
            click.Option(
                ['-tlos','--tgt_lane_order_config_section'],
                type=str, 
                default='linear_8', 
                show_default=True, 
                help='Ring config section'
            ),
            click.Option(
                ['--results_dir'],
                # type=click.Path(exists=True, file_okay=False, dir_okay=True),
                # Let the simulator to create the directory if it doesn't exist
                type=click.Path(exists=False, file_okay=False, dir_okay=True),
                default=Path('results'),
                show_default=True,
                help='Results directory'
            ),
            click.Option(
                ['-v', '--verbose'], 
                is_flag=True, 
                default=False, 
                required=False, 
                show_default=True, 
                help='Enable verbose output'
            ),
        ])

    def format_help(self, ctx, formatter):
        super().format_help(ctx, formatter)
        # Add additional help text
        _format_arbiter_help(formatter)
        # formatter.write("\n")
        # formatter.write("Arbiter Options:\n")
        # formatter.write(f"  [index]: [arbiter]\n")
        # # formatter.write("-" * 50 + "\n")
        # for index, arbiter in _arbiter_map.items():
        #     formatter.write(f"  {int(index):7}: {arbiter}\n")


class WdmSimShortCommand(click.Command):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def format_help(self, ctx, formatter):
        super().format_help(ctx, formatter)
        # Add additional help text
        _format_arbiter_help(formatter)


# @click.command()
@click.group(cls=_NaturalOrderGroup)
def cli():
    """
    CLI interface to the simulator
    """
    pass


@cli.command(cls=WdmSimCommand, help='Run a single experiment')
@click.option('--profile', 
              is_flag=True, 
              show_default=True,
              required=False,
              default=False,
              help='Run in profile mode')
@click.option('-nl', '--num_laser_swaps', 
              type=int, 
              default=10, 
              required=False,
              show_default=True,
              help='Number of laser swap iterations')
@click.option('-nr', '--num_ring_swaps', 
              type=int, 
              default=1, 
              required=False,
              show_default=True,
              help='Number of ring swap iterations')
def run(
    profile, 
    num_laser_swaps, 
    num_ring_swaps,
    arbiter, 
    laser_config_file, 
    laser_config_section, 
    ring_config_file, 
    ring_config_section, 
    init_lane_order_config_file,
    init_lane_order_config_section,
    tgt_lane_order_config_file,
    tgt_lane_order_config_section,
    results_dir,
    verbose
):
    """
    Run a single experiment
    """

    # # enable verbose
    # enable_verbose(verbose)

    # multiple options enabled for arbiter choice
    for arbiter_sel in arbiter:
        # run the experiment
        wdmsim_run.run(
            profile=profile,
            num_laser_swaps=num_laser_swaps,
            num_ring_swaps=num_ring_swaps,
            arbiter=arbiter_sel,
            laser_config_file=laser_config_file,
            laser_config_section=laser_config_section,
            ring_config_file=ring_config_file,
            ring_config_section=ring_config_section,
            init_lane_order_config_file=init_lane_order_config_file,
            init_lane_order_config_section=init_lane_order_config_section,
            tgt_lane_order_config_file=tgt_lane_order_config_file,
            tgt_lane_order_config_section=tgt_lane_order_config_section,
            results_dir=results_dir,
            verbose=verbose,
        )


@cli.command(cls=WdmSimCommand, help='Run a e2e comparison experiment')
@click.option('-nl', '--num_laser_swaps', 
              type=int, 
              default=10, 
              required=False,
              show_default=True,
              help='Number of laser swap iterations')
@click.option('-nr', '--num_ring_swaps', 
              type=int, 
              default=1, 
              required=False,
              show_default=True,
              help='Number of ring swap iterations')
@click.option('-c', '--arbiter_compare', 
              # type=click.Choice(arbiter_registry.keys()),
              type=click.STRING,
              cls=ArbiterOption,
              required=True,
              # multiple=True,
              help='Arbiter of choice')
@click.option('--stop_on_failure',
              is_flag=True,
              default=False,
              required=False,
              show_default=True,
              help='Stop on failure (for interactive debugging)')
def compare(
    num_laser_swaps, 
    num_ring_swaps,
    arbiter, 
    arbiter_compare,
    laser_config_file, 
    laser_config_section, 
    ring_config_file, 
    ring_config_section, 
    init_lane_order_config_file,
    init_lane_order_config_section,
    tgt_lane_order_config_file,
    tgt_lane_order_config_section,
    stop_on_failure,
    results_dir,
    verbose
):
    """
    Run a single experiment
    """

    # # enable verbose
    # enable_verbose(verbose)

    # multiple options enabled for arbiter choice
    for arbiter_sel in arbiter:
        # run the experiment
        wdmsim_run.compare(
            num_laser_swaps=num_laser_swaps,
            num_ring_swaps=num_ring_swaps,
            arbiter=arbiter_sel,
            arbiter_compare=arbiter_compare,
            laser_config_file=laser_config_file,
            laser_config_section=laser_config_section,
            ring_config_file=ring_config_file,
            ring_config_section=ring_config_section,
            init_lane_order_config_file=init_lane_order_config_file,
            init_lane_order_config_section=init_lane_order_config_section,
            tgt_lane_order_config_file=tgt_lane_order_config_file,
            tgt_lane_order_config_section=tgt_lane_order_config_section,
            stop_on_failure=stop_on_failure,
            results_dir=results_dir,
            verbose=verbose,
        )



@cli.command(cls=WdmSimCommand, help='Run a statistics')
@click.option('--num_bins', 
              type=int, 
              default=10, 
              required=False,
              show_default=True,
              help='Number of bins')
@click.option('--plot',
              is_flag=True,
              default=False,
              required=False,
              show_default=True,
              help='Plot the violin plot')
def stat(
    num_bins,
    arbiter, 
    laser_config_file, 
    laser_config_section, 
    ring_config_file, 
    ring_config_section, 
    init_lane_order_config_file,
    init_lane_order_config_section,
    tgt_lane_order_config_file,
    tgt_lane_order_config_section,
    results_dir,
    plot,
    verbose,
):
    """
    Run a statistics
    """

    # multiple options enabled for arbiter choice
    for arbiter_sel in arbiter:
        # run the experiment
        wdmsim_run.stat(
            num_bins=num_bins,
            arbiter=arbiter_sel,
            laser_config_file=laser_config_file,
            laser_config_section=laser_config_section,
            ring_config_file=ring_config_file,
            ring_config_section=ring_config_section,
            init_lane_order_config_file=init_lane_order_config_file,
            init_lane_order_config_section=init_lane_order_config_section,
            tgt_lane_order_config_file=tgt_lane_order_config_file,
            tgt_lane_order_config_section=tgt_lane_order_config_section,
            results_dir=results_dir,
            plot=plot,
            verbose=verbose,
        )



@cli.command(cls=WdmSimCommand, help='Debug mode')
@click.option('--exit_status', 
              type=int, 
              default=0, 
              required=False,
              show_default=True,
              help='target exit status for debug plot')
@click.option('--plot',
              is_flag=True,
              required=False,
              default=False,
              show_default=True,
              help='Plot snapshot of the system')
def debug(
    exit_status, 
    arbiter, 
    laser_config_file, 
    laser_config_section, 
    ring_config_file, 
    ring_config_section, 
    init_lane_order_config_file,
    init_lane_order_config_section,
    tgt_lane_order_config_file,
    tgt_lane_order_config_section,
    results_dir,
    plot,
    verbose
):
    """
    Run a single experiment
    """

    # # enable verbose
    # enable_verbose(verbose)

    # multiple options enabled for arbiter choice
    for arbiter_sel in arbiter:
        # run the experiment
        wdmsim_run.debug(
            exit_status=exit_status,
            arbiter=arbiter_sel,
            laser_config_file=laser_config_file,
            laser_config_section=laser_config_section,
            ring_config_file=ring_config_file,
            ring_config_section=ring_config_section,
            init_lane_order_config_file=init_lane_order_config_file,
            init_lane_order_config_section=init_lane_order_config_section,
            tgt_lane_order_config_file=tgt_lane_order_config_file,
            tgt_lane_order_config_section=tgt_lane_order_config_section,
            results_dir=results_dir,
            plot=plot,
            verbose=verbose,
        )


@cli.command(cls=WdmSimCommand, help='Run a sweep of experiments')
@click.option('-nprocs', 
              type=int, 
              default=1, 
              required=False,
              show_default=True,
              help='Number of processes to use for multiprocessing')
@click.option('-nl', '--num_laser_swaps', 
              type=int, 
              default=10, 
              required=False,
              show_default=True,
              help='Number of iterations')
@click.option('-nr', '--num_ring_swaps',
              type=int,
              default=1,
              required=False,
              show_default=True,
              help='Number of ring swap iterations')
def sweep(
    nprocs, 
    num_laser_swaps,
    num_ring_swaps,
    arbiter, 
    laser_config_file, 
    laser_config_section, 
    ring_config_file, 
    ring_config_section, 
    init_lane_order_config_file,
    init_lane_order_config_section,
    tgt_lane_order_config_file,
    tgt_lane_order_config_section,
    results_dir,
    verbose,
):
    """
    Run a sweep of experiments
    """
    # # enable verbose
    # enable_verbose(verbose)

    # multiple options enabled for arbiter choice
    for arbiter_sel in arbiter:
        # run the experiment
        wdmsim_run.sweep(
            nprocs=nprocs,
            num_laser_swaps=num_laser_swaps,
            num_ring_swaps=num_ring_swaps,
            arbiter=arbiter_sel,
            laser_config_file=laser_config_file,
            laser_config_section=laser_config_section,
            ring_config_file=ring_config_file,
            ring_config_section=ring_config_section,
            init_lane_order_config_file=init_lane_order_config_file,
            init_lane_order_config_section=init_lane_order_config_section,
            tgt_lane_order_config_file=tgt_lane_order_config_file,
            tgt_lane_order_config_section=tgt_lane_order_config_section,
            results_dir=results_dir,
            verbose=verbose,
        )


@cli.command(cls=WdmSimCommand, help='Run a sweep of compare experiments')
@click.option('-nprocs', 
              type=int, 
              default=1, 
              required=False,
              show_default=True,
              help='Number of processes to use for multiprocessing')
@click.option('-nl', '--num_laser_swaps', 
              type=int, 
              default=10, 
              required=False,
              show_default=True,
              help='Number of iterations')
@click.option('-nr', '--num_ring_swaps',
              type=int,
              default=1,
              required=False,
              show_default=True,
              help='Number of ring swap iterations')
@click.option('-c', '--arbiter_compare', 
              # type=click.Choice(arbiter_registry.keys()),
              type=click.STRING,
              cls=ArbiterOption,
              required=True,
              # multiple=True,
              help='Arbiter of choice')
def sweep_compare(
    nprocs, 
    num_laser_swaps,
    num_ring_swaps,
    arbiter, 
    arbiter_compare,
    laser_config_file, 
    laser_config_section, 
    ring_config_file, 
    ring_config_section, 
    init_lane_order_config_file,
    init_lane_order_config_section,
    tgt_lane_order_config_file,
    tgt_lane_order_config_section,
    results_dir,
    verbose,
):
    """
    Run a sweep of experiments
    """
    # # enable verbose
    # enable_verbose(verbose)

    # multiple options enabled for arbiter choice
    for arbiter_sel in arbiter:
        # run the experiment
        wdmsim_run.sweep_compare(
            nprocs=nprocs,
            num_laser_swaps=num_laser_swaps,
            num_ring_swaps=num_ring_swaps,
            arbiter=arbiter_sel,
            arbiter_compare=arbiter_compare,
            laser_config_file=laser_config_file,
            laser_config_section=laser_config_section,
            ring_config_file=ring_config_file,
            ring_config_section=ring_config_section,
            init_lane_order_config_file=init_lane_order_config_file,
            init_lane_order_config_section=init_lane_order_config_section,
            tgt_lane_order_config_file=tgt_lane_order_config_file,
            tgt_lane_order_config_section=tgt_lane_order_config_section,
            results_dir=results_dir,
            verbose=verbose,
        )



plot_choice : List[str] = [
    'fsr_mean',
    'fsr_variance',
    'tuning_range_mean',
    'tuning_range_variance',
    'resonance_variance',
    "grid_variance",
]

@cli.command(cls=WdmSimCommand, help='Plot from sweep')
@click.option('-nl', '--num_laser_swaps',
              type=int,
              default=10,
              required=False,
              show_default=True,
              help='Number of iterations')
@click.option('-nr', '--num_ring_swaps',
              type=int,
              default=1,
              required=False,
              show_default=True,
              help='Number of ring swap iterations')
@click.option('--plot_x_axis', 
              type=click.Choice(plot_choice),
              required=False,
              help='x axis for plot (Currently only assuming ring sweep)')
@click.option('--plot_y_axis', 
              type=click.Choice(plot_choice),
              required=False,
              help='y axis for plot (Currently only assuming ring sweep)')
def plot(
    num_laser_swaps,
    num_ring_swaps,
    arbiter,
    laser_config_file,
    laser_config_section,
    ring_config_file,
    ring_config_section,
    init_lane_order_config_file,
    init_lane_order_config_section,
    tgt_lane_order_config_file,
    tgt_lane_order_config_section,
    results_dir,
    plot_x_axis,
    plot_y_axis,
    verbose,
):
    """
    Run a sweep of experiments
    """

    # multiple options enabled for arbiter choice
    for arbiter_sel in arbiter:
        # run the experiment
        wdmsim_run.plot_sweep(
            num_laser_swaps=num_laser_swaps,
            num_ring_swaps=num_ring_swaps,
            arbiter=arbiter_sel,
            laser_config_file=laser_config_file,
            laser_config_section=laser_config_section,
            ring_config_file=ring_config_file,
            ring_config_section=ring_config_section,
            init_lane_order_config_file=init_lane_order_config_file,
            init_lane_order_config_section=init_lane_order_config_section,
            tgt_lane_order_config_file=tgt_lane_order_config_file,
            tgt_lane_order_config_section=tgt_lane_order_config_section,
            results_dir=results_dir,
            plot_x_axis=plot_x_axis,
            plot_y_axis=plot_y_axis,
        )


@cli.command(cls=WdmSimCommand, help='Plot from sweep-compare')
@click.option('-nl', '--num_laser_swaps',
              type=int,
              default=10,
              required=False,
              show_default=True,
              help='Number of iterations')
@click.option('-nr', '--num_ring_swaps',
              type=int,
              default=1,
              required=False,
              show_default=True,
              help='Number of ring swap iterations')
@click.option('-c', '--arbiter_compare', 
              # type=click.Choice(arbiter_registry.keys()),
              type=click.STRING,
              cls=ArbiterOption,
              required=True,
              # multiple=True,
              help='Arbiter of choice')
@click.option('--plot_x_axis', 
              type=click.Choice(plot_choice),
              required=False,
              help='x axis for plot (Currently only assuming ring sweep)')
@click.option('--plot_y_axis', 
              type=click.Choice(plot_choice),
              required=False,
              help='y axis for plot (Currently only assuming ring sweep)')
def plot_compare(
    num_laser_swaps,
    num_ring_swaps,
    arbiter,
    arbiter_compare,
    laser_config_file,
    laser_config_section,
    ring_config_file,
    ring_config_section,
    init_lane_order_config_file,
    init_lane_order_config_section,
    tgt_lane_order_config_file,
    tgt_lane_order_config_section,
    results_dir,
    plot_x_axis,
    plot_y_axis,
    verbose,
):
    """
    Run a sweep of experiments
    """

    # multiple options enabled for arbiter choice
    for arbiter_sel in arbiter:
        # run the experiment
        wdmsim_run.plot_sweep_compare(
            num_laser_swaps=num_laser_swaps,
            num_ring_swaps=num_ring_swaps,
            arbiter=arbiter_sel,
            arbiter_compare=arbiter_compare,
            laser_config_file=laser_config_file,
            laser_config_section=laser_config_section,
            ring_config_file=ring_config_file,
            ring_config_section=ring_config_section,
            init_lane_order_config_file=init_lane_order_config_file,
            init_lane_order_config_section=init_lane_order_config_section,
            tgt_lane_order_config_file=tgt_lane_order_config_file,
            tgt_lane_order_config_section=tgt_lane_order_config_section,
            results_dir=results_dir,
            plot_x_axis=plot_x_axis,
            plot_y_axis=plot_y_axis,
        )

@cli.command(cls=WdmSimCommand, help='Record a single experiment')
@click.option('--json_path', 
              type=click.Path(exists=False, dir_okay=False, readable=True, resolve_path=True, path_type=Path),
              required=True,
              help='Specify the path to the JSON file')
@click.option('-nl', '--num_laser_swaps', 
              type=int, 
              default=10, 
              required=False,
              show_default=True,
              help='Number of laser swap iterations')
@click.option('-nr', '--num_ring_swaps', 
              type=int, 
              default=1, 
              required=False,
              show_default=True,
              help='Number of ring swap iterations')
@click.option('--overwrite_json',
              type=bool,
              is_flag=True,
              default=False,
              required=False,
              show_default=True,
              help='Overwrite the JSON file if it exists')
def record(
    json_path, 
    num_laser_swaps, 
    num_ring_swaps,
    arbiter, 
    laser_config_file, 
    laser_config_section, 
    ring_config_file, 
    ring_config_section, 
    init_lane_order_config_file,
    init_lane_order_config_section,
    tgt_lane_order_config_file,
    tgt_lane_order_config_section,
    results_dir,
    overwrite_json,
    verbose
):
    """
    Run a single experiment
    """

    # # enable verbose
    # enable_verbose(verbose)

    # multiple options enabled for arbiter choice
    for arbiter_sel in arbiter:
        # run the experiment
        wdmsim_run.record(
            json_path=json_path,
            num_laser_swaps=num_laser_swaps,
            num_ring_swaps=num_ring_swaps,
            arbiter=arbiter_sel,
            laser_config_file=laser_config_file,
            laser_config_section=laser_config_section,
            ring_config_file=ring_config_file,
            ring_config_section=ring_config_section,
            init_lane_order_config_file=init_lane_order_config_file,
            init_lane_order_config_section=init_lane_order_config_section,
            tgt_lane_order_config_file=tgt_lane_order_config_file,
            tgt_lane_order_config_section=tgt_lane_order_config_section,
            results_dir=results_dir,
            overwrite_json=overwrite_json,
            verbose=verbose,
        )


# @cli.command(help='Replay a single experiment')
@cli.command(cls=WdmSimShortCommand, help='Replay a single experiment')
@click.option('--json_path', 
              type=click.Path(exists=True, dir_okay=False, readable=True, resolve_path=True, path_type=Path),
              required=True,
              help='Specify the path to the JSON file')
@click.option('-a','--arbiter_override',
              type=click.STRING,
              cls=ArbiterOption,
              required=False,
              help='Override the arbiter to the specified from the JSON file record')
@click.option('-v', '--verbose',
              is_flag=True,
              default=False,
              show_default=True)
def replay(
    json_path, 
    arbiter_override,
    verbose,
):
    """
    Run a single experiment
    """

    # # enable verbose
    # enable_verbose(verbose)

    # run the experiment
    wdmsim_run.replay(
        json_path=json_path,
        arbiter_override=arbiter_override,
        verbose=verbose,
    )


@cli.command(help="List available arbiters")
def list_arbiter():
    """
    List available arbiters
    """
    print(f"Directories: (Set by $WDMSIM_ARBITER_PATH)")
    for path in discover_from_arbiter_path():
        print(f"  {path.resolve()}")

    print("Available arbiters: [index: arbiter]")
    for index, arbiter in _arbiter_map.items():
        print(f"{int(index):4}: {arbiter}")


def main():
    import multiprocessing
    if hasattr(multiprocessing, 'set_start_method'):
        multiprocessing.set_start_method('fork')  # Only available on Unix-based systems

    # arbiter_path = os.environ.get("WDMSIM_ARBITER_PATH", "")
    # if arbiter_path:
    #     discover_arbiter_modules(Path(arbiter_path))
    # else:
    #     raise ValueError("Environment Variable WDMSIM_ARBITER_PATH is not set")
    discover_from_arbiter_path()

    return cli()
    # try:
    #     return cli()
    # except Exception as e:
    #     print(e)
    #     traceback.print_exc()
    #     import pdb; pdb.set_trace()

if __name__ == '__main__':
    main()
