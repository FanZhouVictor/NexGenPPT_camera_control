# NexGenPPT Camera Control

Desktop app for photographing fabric specimens with a Canon EOS RP over USB. It runs on macOS and Windows.

The app checks the camera and applies the session profile. It then takes 4 photos of one specimen: 2 at 0°, and 2 more after you rotate the specimen 180°. Photos are saved to `data/raw/camera_sessions/<date>/`, along with a log for each photo and a `case_manifest.json`.

## Setup

You need Python 3.10 or newer. Then do the steps for your computer.

**macOS**

```bash
brew install gphoto2
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

**Windows**

1. Install [digiCamControl](https://digicamcontrol.com) (tested with 2.1.6).
2. In digiCamControl, set transfer to **Save to PC only**.
3. Install the app's packages:

```bat
py -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

Keep digiCamControl open while you use the app. On both systems, quit EOS Utility first, because only one program can use the camera at a time.

## Run

```bash
.venv/bin/python -m camera_control          # macOS
.venv\Scripts\python -m camera_control      # Windows
```

Photos are saved inside this folder by default. To save them somewhere else, set `CAMERA_OUTPUT_ROOT` to a folder path before you start the app.

## How the camera is controlled

| | macOS | Windows |
|---|---|---|
| Tool | `gphoto2` | digiCamControl (`CameraControlRemoteCmd.exe`) |
| Settings it can set | All 15 in the profile | 6. The rest stay as set on the camera itself |

The camera code is in [`camera_control/capture/cameras.py`](camera_control/capture/cameras.py). The session profile is in [`profile.py`](camera_control/capture/profile.py), and the specimen naming rules are in [`case_rules.py`](camera_control/capture/case_rules.py).

## Tests

The tests use fake camera tools in `tests/fakes`, so they don't need a camera. The fakes are shell scripts, so the tests run on macOS and Linux only.

```bash
.venv/bin/python -m unittest discover tests
```
