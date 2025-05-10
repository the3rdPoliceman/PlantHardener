import os
import sys
import json
from datetime import datetime, timedelta
import pytest

# ensure project root on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import plant_hardening_notifier as phn


def make_hourly_data(start: datetime, values: list):
    """
    Create a weather data dict with 'hourly': { 'time': [...], 'temperature_2m': [...] }
    Times are ISO strings for each hour corresponding to values.
    """
    times = [(start + timedelta(hours=i)).replace(minute=0, second=0, microsecond=0).isoformat()
             for i in range(len(values))]
    return {'hourly': {'time': times, 'temperature_2m': values}}


def test_load_save_status(tmp_path):
    state_file = tmp_path / "state.json"
    # default when missing
    assert phn.load_status(file_path=str(state_file)) == 'inside'
    # save and load
    phn.save_status('outside', file_path=str(state_file))
    assert phn.load_status(file_path=str(state_file)) == 'outside'


def test_extract_forecast_temps_day():
    # simulate now at 10:15
    now = datetime(2025, 5, 10, 10, 15)
    # provide data for next 5 hours
    values = [10, 12, 16, 17, 18]  # hours 10,11,12,13,14
    data = make_hourly_data(now.replace(minute=0, hour=10), values)
    # horizon=3: expect temperatures at 11,12,13 => values[1:4]
    forecast = phn.extract_forecast_temps(data, now=now, horizon_hours=3)
    assert forecast == values[1:4]


def test_extract_forecast_temps_night():
    # simulate now at 23:30
    now = datetime(2025, 5, 10, 23, 30)
    # generate data from 23:00 through next day 06:00
    hours = list(range(23, 24)) + list(range(0, 7))  # 23,0..6
    values = [20 if h >= 0 else 20 for h in hours]
    # set start at today 23:00
    start = datetime(2025, 5, 10, 23, 0)
    data = make_hourly_data(start, values)
    forecast = phn.extract_forecast_temps(data, now=now)
    # expect all values from next full hour (00:00) until 06:00 => values[1:] (0-based)
    assert forecast == values[1:]


def test_decide_action_day_move_out():
    # inside and forecast all above threshold
    status = 'inside'
    now = datetime(2025, 5, 10, 9, 0)
    forecast = [16, 17, 18]
    new_status, msg = phn.decide_action(status, forecast, now=now)
    assert new_status == 'outside'
    assert 'move the plants outside' in msg


def test_decide_action_day_move_in():
    # outside and forecast all below threshold
    status = 'outside'
    now = datetime(2025, 5, 10, 15, 0)
    forecast = [10, 12, 13]
    new_status, msg = phn.decide_action(status, forecast, now=now)
    assert new_status == 'inside'
    assert 'bring the plants inside' in msg


def test_decide_action_day_no_change():
    # inside but mixed forecast
    status = 'inside'
    now = datetime(2025, 5, 10, 11, 0)
    forecast = [16, 14, 17]
    new_status, msg = phn.decide_action(status, forecast, now=now)
    assert new_status == status
    assert msg is None


def test_decide_action_night_leave_out():
    # inside and overnight all above
    status = 'inside'
    now = datetime(2025, 5, 10, 23, 0)
    forecast = [16, 17, 18, 19, 20, 21, 22]
    new_status, msg = phn.decide_action(status, forecast, now=now)
    assert new_status == 'outside'
    assert 'leave the plants outside' in msg


def test_decide_action_night_bring_in():
    # outside and overnight not all above
    status = 'outside'
    now = datetime(2025, 5, 10, 23, 30)
    forecast = [16, 14, 15, 13]
    new_status, msg = phn.decide_action(status, forecast, now=now)
    assert new_status == 'inside'
    assert 'bring the plants inside' in msg


def test_decide_action_night_no_change_when_already_outside_temp_ok():
    # outside and all above threshold
    status = 'outside'
    now = datetime(2025, 5, 10, 23, 45)
    forecast = [16, 17, 18]
    new_status, msg = phn.decide_action(status, forecast, now=now)
    assert new_status == status
    assert msg is None
