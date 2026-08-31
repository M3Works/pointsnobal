import pandas as pd
import pytest
from pathlib import Path

from pointsnobal.point_model import initialize_model, run_model


class TestInitializeModel:
    """
    Unit tests for how the snobal timestep hierarchy and parameters are
    constructed. These do not run the model, so they are fast and do not
    depend on the compiled extension producing specific values.
    """

    @staticmethod
    def _index(freq, periods=48):
        return pd.date_range("2022-10-01", periods=periods, freq=freq)

    @pytest.mark.parametrize("freq, expected_intervals", [
        ("1H", 1),
        ("3H", 3),
        ("6H", 6),
    ])
    def test_normal_intervals_track_frequency(self, freq, expected_intervals):
        # The NORMAL (1 hr) level must run once per hour of the data step so
        # that multi-hour input integrates the whole step, not just one hour.
        _, tstep_info, _, _ = initialize_model(self._index(freq), 2103.0)
        assert tstep_info[1]["intervals"] == expected_intervals

    @pytest.mark.parametrize("freq, expected_seconds", [
        ("1H", 3600.0),
        ("6H", 21600.0),
    ])
    def test_data_timestep_in_seconds(self, freq, expected_seconds):
        _, tstep_info, _, _ = initialize_model(self._index(freq), 2103.0)
        assert tstep_info[0]["time_step"] == expected_seconds

    def test_constants_only_hold_c_params_keys(self):
        # constants is passed to the C layer as both `mh` and `params`; only
        # these six keys are read from it (via the PARAMS struct).
        _, _, constants, _ = initialize_model(self._index("1H"), 2103.0)
        assert set(constants) == {
            "z_u", "z_t", "z_g",
            "relative_heights", "max_h2o_vol", "max_z_s_0",
        }

    def test_measurement_heights_passed_through(self):
        _, _, constants, _ = initialize_model(
            self._index("1H"), 2103.0, z_u=7.5, z_t=3.0, z_g=0.5
        )
        assert constants["z_u"] == 7.5
        assert constants["z_t"] == 3.0
        assert constants["z_g"] == 0.5

    def test_measurement_height_defaults(self):
        _, _, constants, _ = initialize_model(self._index("1H"), 2103.0)
        assert (constants["z_u"], constants["z_t"], constants["z_g"]) == (
            5.0, 2.0, 0.3
        )

    def test_tstep_info_has_no_output_flag(self):
        # snobal's built-in output paths are disabled; the flag is not used.
        _, tstep_info, _, _ = initialize_model(self._index("1H"), 2103.0)
        assert all("output" not in level for level in tstep_info)

    def test_sub_hourly_frequency_rejected(self):
        with pytest.raises(ValueError, match="whole-hour timestep"):
            initialize_model(self._index("30min"), 2103.0)

    def test_irregular_index_rejected(self):
        index = self._index("1H").delete(5)  # break the regular spacing
        with pytest.raises(ValueError, match="regular frequency"):
            initialize_model(index, 2103.0)


class TestRunSnobal:
    TEST_FILE = Path(__file__).parent.joinpath(
        "data/inputs_csl_2023.csv"
    )
    ELEVATION = 2103.0

    @pytest.fixture(scope="class")
    def test_data(self):
        return pd.read_csv(
            self.TEST_FILE,
            parse_dates=["datetime"], index_col="datetime"
        )

    @pytest.fixture(scope="class")
    def daily_result(self, test_data):
        return run_model(self.ELEVATION, test_data)

    def test_run_snobal(self, daily_result):
        # 6H input, daily output. The specific_mass gold reflects the corrected
        # sub-timestep integration (one normal step per data hour); a loose
        # tolerance keeps it robust across compiler/architecture float drift.
        assert len(daily_result) == 302
        assert daily_result["specific_mass"].values[200] == pytest.approx(
            1548.35, rel=1e-3
        )

    def test_snowpack_accumulates_and_melts_out(self, daily_result):
        mass = daily_result["specific_mass"]
        assert (mass >= 0).all()
        assert mass.max() > 500  # a real snowpack built up
        assert mass.iloc[-1] == pytest.approx(0.0, abs=1e-6)  # melted out

    def test_measurement_heights_change_results(self, test_data, daily_result):
        # Different measurement heights must actually reach the model and
        # change the turbulent/soil fluxes -> a different snowpack.
        altered = run_model(
            self.ELEVATION, test_data, z_u=2.0, z_t=1.0, z_g=0.1
        )
        # Lower/closer sensors change the turbulent + soil fluxes, giving a
        # different modeled snowpack than the default heights.
        assert altered["specific_mass"].values[200] == pytest.approx(
            1476.46, rel=1e-3
        )
        assert not daily_result["specific_mass"].equals(
            altered["specific_mass"]
        )

    def test_hourly_output_yields_more_rows(self, test_data, daily_result):
        sub_daily = run_model(
            self.ELEVATION, test_data, output_frequency_hours=1
        )
        # 6H input -> the finest available cadence is every data step
        assert len(sub_daily) == 1208

    def test_output_cadence_preserves_instantaneous_state(
        self, test_data, daily_result
    ):
        # The output cadence only changes which timesteps are recorded, not
        # the physics: instantaneous state must match at shared timestamps.
        sub_daily = run_model(
            self.ELEVATION, test_data, output_frequency_hours=1
        )
        shared = daily_result.index.intersection(sub_daily.index)
        assert len(shared) == len(daily_result)
        for column in ["thickness", "specific_mass", "snow_density",
                       "temp_snowcover"]:
            diff = (
                daily_result.loc[shared, column]
                - sub_daily.loc[shared, column]
            ).abs().max()
            assert diff == pytest.approx(0.0, abs=1e-9)

    def test_swi_conserved_across_output_cadence(self, test_data, daily_result):
        # SWI is summed over each output interval, so the season total is
        # independent of how finely it is reported.
        sub_daily = run_model(
            self.ELEVATION, test_data, output_frequency_hours=1
        )
        assert sub_daily["SWI"].sum() == pytest.approx(
            daily_result["SWI"].sum(), rel=1e-9
        )

    def test_run_model_rejects_irregular_input(self, test_data):
        broken = test_data.drop(test_data.index[10])
        with pytest.raises(ValueError):
            run_model(self.ELEVATION, broken)
