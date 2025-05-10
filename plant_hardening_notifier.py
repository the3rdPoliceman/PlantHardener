#!/usr/bin/env python3
"""
Plant hardening notifier (refactored for testability).

Provides functions to load/save state, fetch weather, compute forecasts,
make move decisions, and send notifications via Jeffrey.

Run main() every 30 minutes via cron.
"""
import os
import json
from datetime import datetime, timedelta
import requests
import notification  # assumes your Jeffrey library is exposed as `notification`

# Configuration
LATITUDE = 47.3769
LONGITUDE = 8.5417
THRESHOLD_C = 15.0
FORECAST_HOURS = 3
STATE_FILE = os.path.join(os.path.dirname(__file__), "plant_status.json")
TIMEZONE = "Europe/Zurich"


def load_status(file_path=STATE_FILE):
    """Load last-known plant location: 'inside' or 'outside'."""
    try:
        with open(file_path) as f:
            return json.load(f).get('status', 'inside')
    except (FileNotFoundError, json.JSONDecodeError):
        return 'inside'


def save_status(status, file_path=STATE_FILE):
    """Persist the new plant location status."""
    with open(file_path, 'w') as f:
        json.dump({'status': status}, f)


def fetch_weather(latitude=LATITUDE, longitude=LONGITUDE, timezone=TIMEZONE):
    """Retrieve hourly temperature from Open-Meteo."""
    resp = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            'latitude': latitude,
            'longitude': longitude,
            'hourly': 'temperature_2m',
            'timezone': timezone,
        }
    )
    resp.raise_for_status()
    return resp.json()


def extract_forecast_temps(data, now=None, horizon_hours=FORECAST_HOURS):
    """
    Extract forecast temperatures:
      - Before 23:00: next `horizon_hours` hours starting at the next full hour (or current if on the hour).
      - At/after 23:00: from next full hour until 06:00 next day.
    """
    if now is None:
        now = datetime.now()
    times = data['hourly']['time']
    temps = data['hourly']['temperature_2m']
    forecast = []

    # Round up to next full hour
    base = now.replace(minute=0, second=0, microsecond=0)
    if now.minute > 0:
        base += timedelta(hours=1)

    if now.hour < 23:
        # Next horizon_hours hours include base + 0..horizon_hours-1
        for i in range(horizon_hours):
            t = base + timedelta(hours=i)
            key = t.strftime("%Y-%m-%dT%H:%M")
            if key in times:
                forecast.append(temps[times.index(key)])
    else:
        # Night window: from next full hour until 06:00 next day
        end = (base + timedelta(days=1)).replace(hour=6)
        for t_str, t_val in zip(times, temps):
            t = datetime.fromisoformat(t_str)
            if base <= t <= end:
                forecast.append(t_val)

    return forecast


def decide_action(status, forecast, now=None):
    """
    Decide next status and notification message based
    on current status, forecast list, and optional now.
    Returns (new_status, message) or (status, None).
    """
    if now is None:
        now = datetime.now()
    new_status = status
    message = None

    # Day-time before 23:00
    if now.hour < 23:
        if status == 'inside' and forecast and all(t > THRESHOLD_C for t in forecast):
            new_status = 'outside'
            message = (
                f"The next {len(forecast)} hours are forecast above {THRESHOLD_C:.1f}°C; "
                "move the plants outside."
            )
        elif status == 'outside' and forecast and all(t < THRESHOLD_C for t in forecast):
            new_status = 'inside'
            message = (
                f"The next {len(forecast)} hours are forecast below {THRESHOLD_C:.1f}°C; "
                "bring the plants inside."
            )
    # Night-time at/after 23:00
    else:
        if status == 'inside' and forecast and all(t > THRESHOLD_C for t in forecast):
            new_status = 'outside'
            message = (
                f"Tonight's temperatures will stay above {THRESHOLD_C:.1f}°C; "
                "you can leave the plants outside."
            )
        elif status == 'outside' and forecast and not all(t > THRESHOLD_C for t in forecast):
            new_status = 'inside'
            message = (
                f"Tonight's temperatures will dip below {THRESHOLD_C:.1f}°C; "
                "bring the plants inside."
            )
    return new_status, message


def send_notification(message):
    """Send push notification via Jeffrey."""
    notification.send_push_to_jeffrey_notifications(
        message,
        title="Plant Hardening Reminder"
    )


def main():
    now = datetime.now()
    data = fetch_weather()
    forecast = extract_forecast_temps(data, now)
    status = load_status()
    new_status, message = decide_action(status, forecast, now)
    if message:
        send_notification(message)
        save_status(new_status)


if __name__ == '__main__':
    main()
