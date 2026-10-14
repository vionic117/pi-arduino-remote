# Raspberry Pi + Arduino Uno Remote Control Dashboard

A lightweight web dashboard hosted on a headless Raspberry Pi for controlling an Arduino Uno over USB serial. Open the dashboard from another device on the same network to turn the Arduino's built-in LED on or off, make it blink, and request its status.

## Features

- Web-based control interface powered by **FastAPI** and **Uvicorn**
- Arduino Uno communication over USB serial at **115200 baud**
- LED **ON**, **OFF**, and **BLINK** commands
- **STATUS** command to request information from the Arduino
- Headless Raspberry Pi operation, administered over SSH
- Automatic dashboard startup using **systemd**
- Simple `github-upload` helper for publishing changes to GitHub

## How it works

```text
Laptop / phone browser
        |
        | HTTP on local network (port 5000)
        v
Raspberry Pi (FastAPI dashboard)
        |
        | USB serial: /dev/ttyACM0, 115200 baud
        v
Arduino Uno (ArduinoController sketch)
        |
        v
Built-in LED
```

## Repository structure

```text
pi-remote/
├── app.py
├── github-upload
├── sketches/
│   ├── ArduinoController/
│   │   └── ArduinoController.ino
│   └── Blink/
│       └── Blink.ino
├── .gitignore
└── README.md
```

The `venv/` virtual environment and local backup files are intentionally excluded from Git.

## Requirements

**Hardware**

- Raspberry Pi running Raspberry Pi OS (headless/CLI operation is fine)
- Arduino Uno and a USB data cable
- Another device with a web browser on the same network

**Software**

- Python 3 with `venv` and `pip`
- FastAPI, Uvicorn, and PySerial
- Git (for version control)
- Arduino CLI and `avrdude` for building/uploading sketches, as applicable to your setup

## Setup

### 1. Clone the repository

```bash
git clone git@github.com:vionic117/pi-arduino-remote.git
cd pi-arduino-remote
```

### 2. Create a Python virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn pyserial
```

### 3. Connect the Arduino

Connect the Arduino Uno to the Raspberry Pi with a USB data cable. Confirm the serial device is available:

```bash
ls -l /dev/ttyACM*
```

The existing setup uses `/dev/ttyACM0`. This path may change if other serial devices are connected. Make sure the Arduino is running the compatible sketch from `sketches/ArduinoController/` before using the dashboard.

### 4. Start the dashboard

```bash
python app.py
```

On the configured Raspberry Pi, the server listens on port **5000**. From another device on the same network, open:

```text
http://<raspberry-pi-ip>:5000
```

For example, replace `<raspberry-pi-ip>` with the address assigned by your network. Keep the dashboard on a trusted local network; it is not intended to be exposed directly to the public internet without authentication and additional security controls.

## Arduino commands

The Raspberry Pi sends the following text commands over USB serial:

| Command | Purpose |
| --- | --- |
| `LED ON` | Turn the built-in LED on |
| `LED OFF` | Turn the built-in LED off |
| `LED BLINK` | Make the built-in LED blink |
| `STATUS` | Request Arduino status |

The dashboard provides corresponding API routes:

| Route | Purpose |
| --- | --- |
| `/api/status` | Dashboard/service status |
| `/api/arduino/on` | Send LED ON |
| `/api/arduino/off` | Send LED OFF |
| `/api/arduino/blink` | Send LED BLINK |
| `/api/arduino/status` | Request Arduino status |

## Automatic startup with systemd

The working Raspberry Pi uses a service named `arduino-dashboard.service`. To inspect it:

```bash
sudo systemctl status arduino-dashboard.service
sudo systemctl cat arduino-dashboard.service
```

To start the service and enable startup on boot:

```bash
sudo systemctl enable --now arduino-dashboard.service
```

To view recent service logs:

```bash
journalctl -u arduino-dashboard.service -n 50 --no-pager
```

**Important:** The service definition is machine-specific and is not currently included in this repository. On another Raspberry Pi, create a service that runs that machine's virtual-environment Python interpreter with `app.py`, using the correct project path and user. The original setup runs from `/home/mvb/pi-remote/`.

## Uploading updates to GitHub

On the configured Raspberry Pi, the `github-upload` helper is available as a shell command:

```bash
github-upload
```

It stages changes, displays the changed files, asks you to confirm by typing `yes`, prompts for a commit message, and pushes to the `main` branch. It uses SSH authentication with GitHub.

Before confirming, check for secrets or other files you do not want to publish. The helper does not automatically scan source code for credentials.

## Troubleshooting

**Dashboard not reachable:** Check the Raspberry Pi's IP address and service status. Confirm the browser device is on the same network and that port 5000 is reachable.

**Arduino not responding:** Check the USB cable, verify the Arduino appears as `/dev/ttyACM0` (or update the serial port in the app), and make sure the correct sketch is uploaded. Only one program should use the serial port at a time.

**Service errors:** Run `journalctl -u arduino-dashboard.service -n 50 --no-pager` to inspect logs.

**GitHub upload fails:** Check your SSH authentication with `ssh -T git@github.com` and verify the Git remote with `git remote -v`.

## Project status

Working prototype: browser dashboard, Arduino LED control, serial communication, and automatic startup after Raspberry Pi reboot have been tested successfully.

## Future ideas

- Live sensor readings and Arduino status updates
- Adjustable LED blink rate
- Additional output controls
- Optional controller/gamepad input
- Secure remote access with authentication
