#  Plant Hardening Notifier

##  Overview
This project automates the process of hardening your plants by monitoring local temperature forecasts and notifying you when to move them **inside** or **outside**. It uses the `Open-Meteo` API (no account required) and sends push notifications via your custom `jeffrey` library.

##  Features
-  Fetches hourly temperature forecasts from [Open-Meteo](https://open-meteo.com)
-  Simplified logic for day (next 3 hours) and night (23:00–06:00) decision windows
-  Persists current state (*inside*/*outside*) in a JSON file
-  Sends push notifications using `send_push_to_jeffrey_notifications`


##  Installation
1. Clone or download this repository
2. In the directory, run `python3 -m venv venv` to set up the venv
3. Run `source venv/bin/activate` to activate the venv
4. Install dependencies with `pip install -r requirements.txt`


##  Reinstalling Required Libraries after updating Jeffrey

Go to project directory and run the following
1. `source ./venv/bin/activate` to set the project venv as the active python version 
2. `pip install --upgrade --force-reinstall -r requirements.txt` to reinstall requirements


##  Configuration
-  Edit `LATITUDE` and `LONGITUDE` in `plant_hardening_notifier.py` if you’re outside Zürich.
-  Adjust `THRESHOLD_C` or `FORECAST_HOURS` to change temperature threshold or forecast window.
-  Ensure your Pi’s system timezone is set to `Europe/Zurich`.

##  Usage
-  Manual run:
```
./plant_hardening_notifier.py
```
-  Cron job (every 30 min, 08:00–23:00):
```

crontab -e
0,30 8-22 * * * /path/to/run_plant_hardening_notifier.sh
0 23 * * * /path/to/run_plant_hardening_notifier.sh
```

##  Testing
-  Run all unit tests with pytest:
```
pytest tests/test_notifier.py
```

##  Project Structure
-  `plant_hardening_notifier.py` — core logic & entry point
-  `run_plant_hardening_notifier.sh` — cron wrapper script
-  `plant_status.json` — persisted state file
-  `tests/` — pytest unit tests
-  `.gitignore` — excludes venv, IDE files, state file, etc.

##  TODOs
- [ ] Add logging for API errors and decision outcomes!TODO!