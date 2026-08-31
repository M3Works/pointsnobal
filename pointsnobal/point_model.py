"""
Authors: Micah Sandusky, M3 Works LLC (m3works.io)
Created: November 2024
"""

import copy
from typing import List
import logging

import numpy as np
import pandas as pd

from .c_snobal import snobal


LOG = logging.getLogger(__name__)

# Constants
C_TO_K = 273.16
FREEZE = C_TO_K


# Map of our CSV values to expected snobal inputs
MAP_INPUT_VALS = {'air_temp': 'T_a', 'net_solar': 'S_n', 'thermal': 'I_lw',
               'vapor_pressure': 'e_a', 'wind_speed': 'u',
               'soil_temp': 'T_g', 'precip': 'm_pp',
               'percent_snow': 'percent_snow', 'snow_density': 'rho_snow',
               'precip_temp': 'T_pp'}


# Map of snobal outputs to human-readable
EM_OUT = {'net_rad': 'R_n_bar', 'sensible_heat': 'H_bar',
          'latent_heat': 'L_v_E_bar',
          'snow_soil': 'G_bar', 'precip_advected': 'M_bar',
          'sum_EB': 'delta_Q_bar', 'evaporation': 'E_s_sum',
          'snowmelt': 'melt_sum', 'SWI': 'ro_pred_sum',
          'cold_content': 'cc_s'}

# Map of output variables for snowpack state
SNOW_OUT = {'thickness': 'z_s', 'snow_density': 'rho',
            'specific_mass': 'm_s', 'liquid_water': 'h2o',
            'temp_surf': 'T_s_0', 'temp_lower': 'T_s_l',
            'temp_snowcover': 'T_s', 'thickness_lower': 'z_s_l',
            'water_saturation': 'h2o_sat'}


def initialize_model(
        model_datetimes: pd.DatetimeIndex, elevation: float,
        z_u: float = 5.0, z_t: float = 2.0, z_g: float = 0.3,
):
    """
    Args:
        model_datetimes: datetime index from the forcing data
        elevation: elevation in meters
        z_u: wind speed measurement height in meters (relative to the snow
            surface)
        z_t: air temperature measurement height in meters (relative to the
            snow surface)
        z_g: soil temperature depth in meters

    Returns:
        output_record: output dictionary for start (mostly 0.0s)
        tstep_info: Information for dynamic timestepping
        constants: Dictionary of constants for snobal
        model_datetimes: a list of datetimes for which to run the model
    """
    # initialize isnobal state
    LOG.info('Initializing snobal Model')
    freq = pd.infer_freq(model_datetimes)
    if freq is None:
        raise ValueError(
            "Could not infer a regular frequency from the input datetime "
            "index. pointsnobal requires evenly-spaced input data."
        )
    # Seconds between input records (the data timestep)
    offset = pd.tseries.frequencies.to_offset(freq)
    data_tstep = pd.Timedelta(offset).total_seconds()
    # The normal/medium/small sub-timestep hierarchy below assumes the data
    # step is a whole number of hours: the normal step is one hour and is run
    # once per hour of the data step. Reject anything that would not divide
    # cleanly rather than silently under-integrating the timestep.
    if data_tstep % 3600 != 0:
        raise ValueError(
            "pointsnobal requires input data on a whole-hour timestep, got "
            f"{data_tstep / 3600.0:.4g} hours between records."
        )
    normal_intervals = int(data_tstep // 3600)

    # Only the keys consumed by the C layer (via the PARAMS struct) are kept
    constants = {
            'max_h2o_vol': 0.01,
            'max_z_s_0': 0.25,
            'z_u': z_u,
            'z_t': z_t,
            'z_g': z_g,
            'relative_heights': True,
        }

    # get the timestep info. Each data step is run as `normal_intervals`
    # one-hour normal steps, which are adaptively subdivided into medium
    # (15 min) and small (1 min) steps when the pack mass is below threshold.
    tstep_info = [
        {
            'level': 0, 'threshold': None,
            'time_step': data_tstep,  # data timestep in seconds
            'intervals': None
        },
        {'level': 1, 'threshold': 60.0, 'time_step': 3600.0,
        'intervals': normal_intervals},
        {'level': 2, 'threshold': 10.0, 'time_step': 900.0,
        'intervals': 4},
        {'level': 3, 'threshold': 1.0, 'time_step': 60.0,
        'intervals': 15}
    ]
    # get init params
    dem = np.atleast_2d(elevation)
    mask = np.atleast_2d(1)
    roughness = np.atleast_2d(0.005)

    output_record = {
        'mask': mask, 'elevation': dem,
        'z_0': roughness
    }
    for key in [
        'rho', 'T_s_0', 'T_s_l', 'T_s',
        'cc_s_0', 'cc_s_l', 'cc_s', 'm_s', 'm_s_0', 'm_s_l', 'z_s',
        'z_s_0', 'z_s_l',
        'h2o_sat', 'layer_count', 'h2o', 'h2o_max', 'h2o_vol',
        'h2o_total',
        'R_n_bar', 'H_bar', 'L_v_E_bar', 'G_bar', 'G_0_bar',
        'M_bar', 'delta_Q_bar', 'delta_Q_0_bar', 'E_s_sum', 'melt_sum',
        'ro_pred_sum',
        'current_time', 'time_since_out'
    ]:
        output_record[key] = np.atleast_2d(0.0)

    return output_record, tstep_info, constants, model_datetimes


def get_timestep_force(df_inputs: pd.DataFrame, tstep: pd.Timestamp):
    """
    Get the timestep of inputs needed for snobal

    Args:
        df_inputs: all hourly inputs in a dataframe
        tstep: timestep to sample
    Returns:
        dictionary of inputs for that timestep
    """
    # Get the row for the expected timestep
    input_row = df_inputs.loc[tstep, :]
    result = {}

    # map function from these values to the ones required by snobal
    for f in input_row.keys():
        # expected input name for snobal
        if f in MAP_INPUT_VALS:
            result[MAP_INPUT_VALS[f]] = np.atleast_2d(input_row[f])
        else:
            LOG.debug(f"{f} is not a known mapping input")

    # convert from C to K
    result['T_a'] += FREEZE
    result['T_pp'] += FREEZE
    result['T_g'] += FREEZE

    return result


def save_timsteps(
        output_list: List[dict], output_records: dict, tstep: pd.Timestamp
):
    """

    Args:
        output_list: list of dictionaries containing output state
            for each day
        output_records: an output dictionary for one day
        tstep: timestep of output

    Returns:
        populated output_list
    """
    # preallocate
    record = {}

    # gather all the data together
    for key, value in EM_OUT.items():
        record[key] = copy.deepcopy(output_records[value])[0, 0]

    for key, value in SNOW_OUT.items():
        record[key] = copy.deepcopy(output_records[value])[0, 0]

    # convert from K to C
    record['temp_snowcover'] -= FREEZE
    record['temp_surf'] -= FREEZE
    record['temp_lower'] -= FREEZE

    record['datetime'] = tstep - pd.to_timedelta("1 hour")

    output_list.append(record)
    return output_list


def run_model(
        elevation: float,
        df_inputs: pd.DataFrame,
        z_u: float = 5.0, z_t: float = 2.0, z_g: float = 0.3,
        output_frequency_hours: int = 24,
) -> pd.DataFrame:
    """
    Run snobal with given input data
    Args:
        elevation: elevation in meters for the point
        df_inputs: hourly input pd.Dataframe
        z_u: wind speed measurement height in meters (relative to the snow
            surface)
        z_t: air temperature measurement height in meters (relative to the
            snow surface)
        z_g: soil temperature depth in meters
        output_frequency_hours: how often (in hours) to record an output row.
            Defaults to 24 (daily). Use 1 for hourly output. Accumulated
            outputs (e.g. SWI) are summed over each output interval, so at
            hourly output they represent hourly totals rather than daily.

    Returns:
        Dataframe of outputs indexed on datetime
    """
    # Variable for storing the outputs
    output_list = []
    # Get the variables for snobal
    output_record, tstep_info, constants, model_datetimes = initialize_model(
        df_inputs.index, elevation, z_u=z_u, z_t=z_t, z_g=z_g)

    # Tracking how often we output
    output_record['current_time'] = 1.0 * np.zeros(
        output_record['elevation'].shape)
    output_record['time_since_out'] = 1.0 * np.zeros(
        output_record['elevation'].shape)

    # Get the timestep for the data (first index of the isnobal tstep list)
    data_tstep = tstep_info[0]['time_step']
    LOG.debug('Reading inputs for first timestep')

    # Get the initial inputs
    input1 = get_timestep_force(df_inputs, model_datetimes[0])
    LOG.debug('starting pointsnobal time series loop')
    j = 1
    # Iterate through the rest of the timesteps to run snobal
    for tstep in model_datetimes[1:]:
        LOG.debug(
            'running snobal for timestep: {}'.format(tstep)
        )
        # Get the next inputs
        input2 = get_timestep_force(df_inputs, tstep)

        first_step = j

        # Run the model
        rt = snobal.do_tstep_grid(
            input1, input2, output_record, tstep_info,
            constants, constants,
            first_step=first_step,
            nthreads=1)

        if rt != -1:
            raise ValueError(f'pointsnobal error on time step {tstep}')

        # copy the second inputs to now be the starting inputs
        input1 = copy.deepcopy(input2)

        # output at the requested frequency and the last time step
        if (j * (data_tstep / 3600.0) % output_frequency_hours == 0) \
                or (j == len(model_datetimes) - 1):
            LOG.debug('Outputting {}'.format(tstep))

            # write timesep to the final dataframe
            output_list = save_timsteps(output_list, output_record, tstep)
            # Store a zero array in time since out since we just output
            output_record['time_since_out'] = np.zeros(
                output_record['elevation'].shape
            )

        LOG.debug('Finished timestep: {}'.format(tstep))

        j += 1

    df_out = pd.DataFrame.from_records(output_list)
    return df_out.set_index("datetime")
