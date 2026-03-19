# Bluetooth Thermometer System Service

A continuous monitoring system for Govee and ThermoPro Bluetooth thermometers. It reads BLE advertisements, persists them to a local SQLite database, triggers push notifications via [ntfy.sh](https://ntfy.sh/), and exposes a modern, responsive web dashboard.

## Overview

- **Web Dashboard**: A two-pane interface to manage registered devices and discover new sensors.
- **Alerts**: Configurable high/low thresholds for temperature and humidity. Alerts are pushed instantly to your phone.
- **History Logs**: Every X minutes, device measurements are recorded for historical analysis.

## Project Setup

1. **Clone/Download** this repository to your Linux machine.
2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Configure**: Run the app once to generate a `config.json` or create one manually with your desired port, frequency, and `ntfy.sh` topic.

## Running as a Linux System Service (systemd)

To ensure the monitor runs continuously in the background and starts automatically on boot, you can register it as a systemd service.

1. Open a terminal and create a new service file:
   ```bash
   sudo nano /etc/systemd/system/sensing.service
   ```

2. Add the following configuration to the file. **Make sure to update the `User`, `WorkingDirectory`, and `ExecStart` paths** to point to your specific system setup:
   ```ini
   [Unit]
   Description=Bluetooth Thermometer Background Service
   After=network.target bluetooth.target

   [Service]
   Type=simple
   User=your_username
   WorkingDirectory=/path/to/Sensing
   ExecStart=/usr/bin/python3 /path/to/Sensing/app.py
   Restart=on-failure
   RestartSec=5

   # NOTE: If you are using a virtual environment, you must point ExecStart to 
   # the python executable *inside* the virtual environment, like so:
   # ExecStart=/path/to/Sensing/venv/bin/python /path/to/Sensing/app.py
   # 
   # You can also optionally add the Environment variable so scripts find your venv first:
   # Environment="PATH=/path/to/Sensing/venv/bin:$PATH"

   [Install]
   WantedBy=multi-user.target
   ```

3. Reload the systemd daemon to recognize your new service:
   ```bash
   sudo systemctl daemon-reload
   ```

4. Enable the service to start automatically on system boot:
   ```bash
   sudo systemctl enable sensing.service
   ```

5. Start the service immediately:
   ```bash
   sudo systemctl start sensing.service
   ```

6. To check the status or view the logs, use:
   ```bash
   sudo systemctl status sensing.service
   sudo journalctl -u sensing.service -f
   ```

## Web Dashboard

Once the service is running, navigate to `http://<your-machine-ip>:8432` in your browser. (The port defaults to `8432` but can be customized inside the `config.json` file).
