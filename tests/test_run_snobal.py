import pandas as pd
import pytest
from pathlib import Path

from pointsnobal.point_model import run_model


class TestRunSnobal:
    TEST_FILE = Path(__file__).parent.joinpath(
        "data/inputs_csl_2023.csv"
    )

    @pytest.fixture(scope="class")
    def test_data(self):
        return pd.read_csv(
            self.TEST_FILE,
            parse_dates=["datetime"], index_col="datetime"
        )

    def test_run_snobal(self, test_data):
        start_date = test_data.index.min()
        end_date = test_data.index.max()

        # Run the model for that file
        result = run_model(
            start_date, end_date, 2103.0, test_data
        )
        assert len(result) == 302
        assert result["specific_mass"].values[200] == pytest.approx(
            1623.4878530514477
        )
