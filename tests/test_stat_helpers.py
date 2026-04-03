"""Unit tests for do_stat() helper methods on Neviweb130Thermostat.

Tests:
  - _fetch_monthly_stats assigns _month_kwh from mock stat data
  - _fetch_daily_stats assigns _today_kwh from mock stat data
  - _fetch_hourly_stats assigns _hour_kwh and _marker from mock stat data
  - do_stat() skips stat fetch when interval not elapsed
  - _record_stat increments _total_kwh_count when marker changes
"""
from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from custom_components.neviweb130.climate import Neviweb130Thermostat


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_device_info(device_id: int = 111, model: int = 1123):
    return {
        "id": device_id,
        "name": "Test",
        "sku": "TH1123ZB",
        "location$id": 67890,
        "signature": {
            "model": model,
            "modelCfg": 0,
            "protocol": "zigbee",
            "softVersion": {"major": 1, "middle": 2, "minor": 3},
        },
    }


def make_client():
    client = MagicMock()
    client.scoped_unique_id.side_effect = lambda device_id: str(device_id)
    client._account_prefix = ""
    client._is_primary = True
    client._network_name = "Home"
    client._network_name2 = None
    client._network_name3 = None
    return client


def make_thermostat(client=None):
    if client is None:
        client = make_client()
    hass = MagicMock()
    hass.data = {"neviweb130": {"safe_mode": "-", "translation_cache": None, "ready": False}}
    hass.config.language = "en"
    entity = Neviweb130Thermostat(make_device_info(), "Test Thermostat", "TH1123ZB", "1.0.0", 67890, client)
    entity.hass = hass
    return entity


def _monthly_stat_data():
    return [
        {"period": 5000, "date": "2024-01-01T00:00:00.000Z"},
        {"period": 3000, "date": "2024-02-01T00:00:00.000Z"},
    ]


def _daily_stat_data():
    return [
        {"period": 2000, "date": "2024-02-10T00:00:00.000Z"},
        {"period": 1500, "date": "2024-02-11T00:00:00.000Z"},
    ]


def _hourly_stat_data():
    return [
        {"period": 500, "date": "2024-02-11T10:00:00.000Z"},
        {"period": 300, "date": "2024-02-11T11:00:00.000Z"},
    ]


# ===========================================================================
# _fetch_monthly_stats
# ===========================================================================

@pytest.mark.unit
class TestFetchMonthlyStats:
    def test_assigns_month_kwh_from_last_entry(self):
        client = make_client()
        client.get_device_monthly_stats.return_value = _monthly_stat_data()
        t = make_thermostat(client)

        t._fetch_monthly_stats()

        # Last entry: 3000 / 1000 = 3.0 kWh
        assert t._month_kwh == 3.0

    def test_assigns_monthly_kwh_count_as_sum(self):
        client = make_client()
        client.get_device_monthly_stats.return_value = _monthly_stat_data()
        t = make_thermostat(client)

        t._fetch_monthly_stats()

        # (5000 + 3000) / 1000 = 8.0 kWh total
        assert t._monthly_kwh_count == 8.0

    def test_sets_month_kwh_zero_when_no_data(self):
        client = make_client()
        client.get_device_monthly_stats.return_value = None
        t = make_thermostat(client)

        t._fetch_monthly_stats()

        assert t._month_kwh == 0

    def test_sets_month_kwh_zero_when_single_entry(self):
        client = make_client()
        client.get_device_monthly_stats.return_value = [{"period": 1000, "date": "2024-01-01T00:00:00.000Z"}]
        t = make_thermostat(client)

        t._fetch_monthly_stats()

        assert t._month_kwh == 0


# ===========================================================================
# _fetch_daily_stats
# ===========================================================================

@pytest.mark.unit
class TestFetchDailyStats:
    def test_assigns_today_kwh_from_last_entry(self):
        client = make_client()
        client.get_device_daily_stats.return_value = _daily_stat_data()
        t = make_thermostat(client)

        t._fetch_daily_stats(current_month=2)

        # Last entry: 1500 / 1000 = 1.5 kWh
        assert t._today_kwh == 1.5

    def test_assigns_daily_kwh_count_for_current_month(self):
        client = make_client()
        client.get_device_daily_stats.return_value = _daily_stat_data()
        t = make_thermostat(client)

        t._fetch_daily_stats(current_month=2)

        # Both entries are in February (month=2): (2000 + 1500) / 1000 = 3.5
        assert t._daily_kwh_count == 3.5

    def test_sets_today_kwh_zero_when_no_data(self):
        client = make_client()
        client.get_device_daily_stats.return_value = None
        t = make_thermostat(client)

        t._fetch_daily_stats(current_month=2)

        assert t._today_kwh == 0

    def test_excludes_entries_from_other_months(self):
        client = make_client()
        # January entry should be excluded when current_month=2
        client.get_device_daily_stats.return_value = [
            {"period": 9000, "date": "2024-01-15T00:00:00.000Z"},
            {"period": 1500, "date": "2024-02-11T00:00:00.000Z"},
        ]
        t = make_thermostat(client)

        t._fetch_daily_stats(current_month=2)

        # Only February entry counts: 1500 / 1000 = 1.5
        assert t._daily_kwh_count == 1.5


# ===========================================================================
# _fetch_hourly_stats
# ===========================================================================

@pytest.mark.unit
class TestFetchHourlyStats:
    def test_assigns_hour_kwh_from_last_entry(self):
        client = make_client()
        client.get_device_hourly_stats.return_value = _hourly_stat_data()
        t = make_thermostat(client)

        t._fetch_hourly_stats(current_day=11)

        # Last entry: 300 / 1000 = 0.3 kWh
        assert t._hour_kwh == 0.3

    def test_assigns_marker_from_last_entry_date(self):
        client = make_client()
        client.get_device_hourly_stats.return_value = _hourly_stat_data()
        t = make_thermostat(client)

        t._fetch_hourly_stats(current_day=11)

        assert t._marker == "2024-02-11T11:00:00.000Z"

    def test_assigns_hourly_kwh_count_for_current_day(self):
        client = make_client()
        client.get_device_hourly_stats.return_value = _hourly_stat_data()
        t = make_thermostat(client)

        t._fetch_hourly_stats(current_day=11)

        # Both entries are on day 11: (500 + 300) / 1000 = 0.8
        assert t._hourly_kwh_count == 0.8

    def test_sets_hour_kwh_zero_when_empty_list(self):
        """When API returns a single-entry list (≤1), hour_kwh is set to 0."""
        client = make_client()
        client.get_device_hourly_stats.return_value = [{"period": 300, "date": "2024-02-11T11:00:00.000Z"}]
        t = make_thermostat(client)

        t._fetch_hourly_stats(current_day=11)

        assert t._hour_kwh == 0


# ===========================================================================
# _record_stat
# ===========================================================================

@pytest.mark.unit
class TestRecordStat:
    def test_initializes_total_when_zero(self):
        t = make_thermostat()
        t._total_kwh_count = 0
        t._monthly_kwh_count = 10.0
        t._daily_kwh_count = 2.0
        t._hourly_kwh_count = 0.5
        t._marker = "2024-02-11T11:00:00.000Z"

        t._record_stat()

        assert t._total_kwh_count == 12.5
        assert t._mark == "2024-02-11T11:00:00.000Z"

    def test_increments_total_when_marker_changes(self):
        t = make_thermostat()
        t._total_kwh_count = 100.0
        t._mark = "2024-02-11T10:00:00.000Z"
        t._marker = "2024-02-11T11:00:00.000Z"
        t._hour_kwh = 0.3

        t._record_stat()

        assert t._total_kwh_count == 100.3
        assert t._mark == "2024-02-11T11:00:00.000Z"

    def test_does_not_increment_when_marker_unchanged(self):
        t = make_thermostat()
        t._total_kwh_count = 100.0
        t._mark = "2024-02-11T11:00:00.000Z"
        t._marker = "2024-02-11T11:00:00.000Z"
        t._hour_kwh = 0.3

        t._record_stat()

        assert t._total_kwh_count == 100.0


# ===========================================================================
# do_stat() interval guard
# ===========================================================================

@pytest.mark.unit
class TestDoStatIntervalGuard:
    def test_skips_fetch_when_interval_not_elapsed(self):
        """do_stat() must not call any stat API when interval has not elapsed."""
        client = make_client()
        t = make_thermostat(client)

        # Set energy_stat_time to "just now" so interval hasn't elapsed
        t._energy_stat_time = time.time()
        start = time.time()

        t.do_stat(start)

        client.get_device_monthly_stats.assert_not_called()
        client.get_device_daily_stats.assert_not_called()
        client.get_device_hourly_stats.assert_not_called()

    def test_sets_energy_stat_time_on_first_call(self):
        """When _energy_stat_time is 0, do_stat() sets it to start and returns."""
        client = make_client()
        t = make_thermostat(client)
        t._energy_stat_time = 0
        start = time.time()

        t.do_stat(start)

        assert t._energy_stat_time == start
        client.get_device_monthly_stats.assert_not_called()
