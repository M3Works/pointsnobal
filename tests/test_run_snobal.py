import pandas as pd
import pytest
from pathlib import Path

from src.point_model import run_model


class TestRunSnobal:
    TEST_FILE = Path(__file__).parent.joinpath(
        "data_package/hoosier_small.csv"
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
            start_date, end_date, 2944.7, test_data
        )
        assert len(result) == 30
        assert result["specific_mass"].values[29] == pytest.approx(17.424981768915075)


class TestRunSnobal2(TestRunSnobal):
    TEST_FILE = Path(__file__).parent.joinpath(
        "data_package/inputs_csl_2023.csv"
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
            1625.5221485950697
        )

