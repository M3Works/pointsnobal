"""
Use the function in the point_model.py module to
create output csvs of snobal state outputs

Authors: Micah Sandusky, M3 Works LLC (m3works.io)
Created: Jan 2025
"""
import argparse
from pathlib import Path
import pandas as pd
import logging

from point_model import run_model


LOG = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="CLI for running pointsnobal"
    )
    parser.add_argument(
        "filepath", required=True,
        help="Path to input csv"
    )
    parser.add_argument(
        "elevation", type="float",
        required=True, help="Elevation of point in meters"
    )
    parser.add_argument(
        "--output_file", type="str", default=None,
        required=False, help="Optional path to output file"
    )
    args = parser.parse_args()

    LOG.info(f"Reading in {args.filepath}")
    df_inputs = pd.read_csv(
        args.filepath,
        parse_dates=["datetime"], index_col="datetime"
    )
    # Start and end dates
    start_date = df_inputs.index.min()
    end_date = df_inputs.index.max()

    output_file = args.output_file or "./pointsnobal_results.csv"

    # Run the model for that file
    LOG.info(f"Running pointsnobal...")
    df_out = run_model(
        start_date, end_date, args.elevation, df_inputs
    )
    LOG.info(f"Finished pointsnobal, outputting to {output_file}")
    df_out.to_csv(output_file)


if __name__ == '__main__':
    main()
