#!/usr/bin/env python3
"""
Plant hardening notifier with console logging.

Checks current and forecast temperatures via Open-Meteo API and sends push notifications
using the `jeffrey` library when plants should be moved inside or outside.
Includes print statements for cron log monitoring.

Run every 30 minutes via cron.
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


def load_status():
    """Load the last-known plant location: 'inside' or 'outside'."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            data = json.load(f)
            status = data.get('status', 'inside')
            print(f"[INFO] Loaded status from file: {status}")
            return status
    print("[INFO] No status file found, defaulting to 'inside'.")
    return 'inside'


def save_status(status: str):
    """Persist the new plant location status."""
    with open(STATE_FILE, 'w') as f:
        json.dump({'status': status}, f)
    print(f"[INFO] Saved new status: {status}")


def fetch_weather():
    """Retrieve current and hourly forecast temperatures from Open-Meteo."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        'latitude': LATITUDE,
        'longitude': LONGITUDE,
        'hourly': 'temperature_2m',
        'current_weather': 'true',
        'timezone': TIMEZONE,
    }
    print("[INFO] Fetching weather data from Open-Meteo...")
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    print("[INFO] Weather data fetched successfully.")
    return resp.json()


def extract_forecast_temps(data, now):
    """
    Build a list of forecast temperatures:
      - If before 23:00, next FORECAST_HOURS hours.
      - If at or after 23:00, from the next hour until 06:00 next morning.
    """
    times = data['hourly']['time']
    temps = data['hourly']['temperature_2m']
    forecast = []

    base = now.replace(minute=0, second=0, microsecond=0)
    if now.minute > 0:
        base += timedelta(hours=1)
    print(f"[INFO] Base time for forecast: {base.isoformat()}")

    if now.hour >= 23:
        end = (base + timedelta(days=1)).replace(hour=8)
        for t_str, t_val in zip(times, temps):
            t = datetime.fromisoformat(t_str)
            if base <= t <= end:
                forecast.append(t_val)
        print(f"[INFO] Night forecast window until {end.isoformat()} retrieved.")
    else:
        for i in range(1, FORECAST_HOURS + 1):
            t = base + timedelta(hours=i)
            key = t.strftime("%Y-%m-%dT%H:%M")
            if key in times:
                forecast.append(temps[times.index(key)])
        print(f"[INFO] Day forecast for next {FORECAST_HOURS} hours retrieved.")

    print(f"[INFO] Forecast temperatures: {forecast}")
    return forecast


def main():
    now = datetime.now()
    print(f"[START] Plant notifier run at {now.isoformat()}")
    try:
        weather = fetch_weather()
        current_temp = weather['current_weather']['temperature']
        print(f"[INFO] Current temperature: {current_temp}°C")
        forecast = extract_forecast_temps(weather, now)
        status = load_status()
        print(f"[INFO] Current status: {status}")
        new_status = status
        message = None

        # Night-time logic
        if now.hour >= 23:
            print("[INFO] Using night-time logic.")
            if all(t > THRESHOLD_C for t in forecast) and status == 'inside':
                new_status = 'outside'
                message = (
                    f"Tonight's temperatures will stay above {THRESHOLD_C:.1f}°C; "
                    "you can leave the plants outside."
                )
            elif any(t < THRESHOLD_C for t in forecast) and status == 'outside':
                new_status = 'inside'
                message = (
                    f"Tonight's temperatures will fall below {THRESHOLD_C:.1f}°C; "
                    "bring the plants inside."
                )
        # Day-time logic
        else:
            print("[INFO] Using day-time logic.")
            if (
                forecast
                and status == 'inside'
                and all(t > THRESHOLD_C for t in forecast)
            ):
                new_status = 'outside'
                message = (
                    f"The next {FORECAST_HOURS} hours are forecast above {THRESHOLD_C:.1f}°C; "
                    "move the plants outside."
                )
            elif (
                forecast
                and status == 'outside'
                and all(t < THRESHOLD_C for t in forecast)
            ):
                new_status = 'inside'
                message = (
                    f"The next {FORECAST_HOURS} hours are forecast below {THRESHOLD_C:.1f}°C; "
                    "bring the plants inside."
                )

        if message:
            print(f"[NOTIFY] {message}")
            notification.send_push_to_jeffrey_notifications(
                message,
                title="Plant Hardening Reminder"
            )
            print(f"[INFO] Changing status from {status} to {new_status}")
            save_status(new_status)
        else:
            print(f"[INFO] No action needed. Status remains {status}.")

    except Exception as e:
        print(f"[ERROR] An error occurred: {e}")

    print("[END] Run completed.")


if __name__ == '__main__':
    main()
