# PointSnobal

Python implementation of the Snobal model applied at either a point

## Input files

### Variables that inform **snobal**
These variables are directly used within iSnobal
 * `air_temp` - modeled air temp at 2m above ground
 * `percent_snow` - % mix of snow vs rain (1 == all snow)
 * `precip` - precipitation mass
 * `precip_temp` - wet bulb temperature
 * `snow_density` - density of the NEW snow that hour
 * `vapor_pressure` - modeled vapor pressure
 * `wind_speed` - Wind speed at 5m above ground
 * `soil_temp` - Average temperature of the soil column down to 30cm
 * `net_solar` - net solar into the snowpack
 * `thermal` - net longwave radiation into the snowpack

You will need to calculate these using the methods outlined in SMRF 
after you have applied the new canopy radiation model

## Height settings for **snobal**
 * wind height: 5m
 * air temp height: 2m
 * soil temp depth: 0.3m

## Watch out for
 * Snobal expects temperatures to be in Kelvin. This code expects Celcius.
  We do the conversion in `get_timestep_force`
 * Precip mass (`precip`) is a big driver here. Without accurate conditions,
    model results will be poor

## PointSnobal script


### Script usage


### Requirements
Requirements can be found in `setup.py`

## Validation data
Using [metloom](https://github.com/M3Works/metloom) for station data that
can be used for validation. `get_daily_data` returns a GeoPandas DataFrame
of the variables and units on a daily timestep. Validation is crucial in 
snowpack modeling!

```python
# Imports
import pandas as pd
from metloom.pointdata import CDECPointData
from metloom.variables import CdecStationVariables

# Specify start and end date
start_date = pd.to_datetime("2019-10-01")
end_date = pd.to_datetime("2020-06-01")

# List of variables to request
desired_variables = [
    CdecStationVariables.SWE, CdecStationVariables.SNOWDEPTH
]

# Define the point
point = CDECPointData("GRV", "Graveyard Meadow")

# Request the data
df = point.get_daily_data(
    start_date, end_date, desired_variables
)
# Data comes back indexed on `datetime` and `site`, reset to just datetime
df = df.reset_index().set_index("datetime")
# Show the results
print(df)
# store in csv if you want
df.to_csv(f"{point.id}_station_data.csv", index_label="datetime")

```
