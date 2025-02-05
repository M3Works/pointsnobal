"""
Hit the API
"""
import argparse
import json
from pathlib import Path

import pandas as pd
import requests


def main():
    parser = argparse.ArgumentParser(
        description=''
    )
    parser.add_argument(
        'csv_file', type=str,
        help='name of the basin')
    parser.add_argument(
        'elevation', type=float,
        help='station elevation in METERS')
    parser.add_argument(
        '--output_dir', type=str, default='./',
        help='where to output the report')
    parser.add_argument(
        "--api_key", type=str, default=None,
        help='api key for the request'
    )
    parser.add_argument(
        "--api_id", type=str, default="bktiz24e19",
        help='api key for the request'
    )
    args = parser.parse_args()

    # API endpoint and parameters
    url = f"https://{args.api_id}.execute-api.us-west-2.amazonaws.com/m3works/snobal"
    params = {"elevation": args.elevation}

    # Setup the new file
    file_path = Path(args.csv_file)
    output_file_name = file_path.name.replace('inputs', 'snobal')
    output_file = file_path.parent.joinpath(output_file_name)

    # Headers
    headers = {
        "x-api-key": args.api_key,
        "Content-Type": "text/csv"
    }

    print("Reading file and calling API")
    # Load the CSV file as binary data
    with open(args.csv_file, "rb") as file:
        response = requests.post(
            url, headers=headers, params=params, data=file)

    print("API request finished")
    # error if we failed
    response.raise_for_status()

    result = response.json()

    print("Parsing results")
    # Get result into pandas
    df = pd.DataFrame.from_dict(result['results']["data"])
    df.index = pd.to_datetime(result['results']["index"])

    print(f"Outputting results to {str(output_file)}")
    df.to_csv(
        str(output_file), index_label="datetime"
    )
    print("Finished")


if __name__ == '__main__':
    main()
