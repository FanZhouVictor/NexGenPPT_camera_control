# NexGenPPT Camera Control

Desktop app for photographing fabric specimens with a Canon EOS RP over USB. It runs on macOS and Windows.

The app checks the camera and applies the session profile. It then takes 4 photos of one specimen alone on the paper, either a whole parent or one cut piece: 2 at 0°, and 2 more after you rotate it 180°. Photos are saved to `data/raw/camera_sessions/<date>/`, along with a log for each photo and a `case_manifest.json`.

## What you fill in

Before each capture the app asks a few questions about the specimen. Any combination of answers is allowed.

- **Sample ID** of the parent sample, such as `C205`.
- **What you are photographing:** the whole parent, one cut piece, or something else. For a piece you enter how many the sample was cut into and choose which piece is on the paper; only one piece is photographed at a time. The pieces are named `P1`, `P2`, … from left to right as cut; you can type your own names instead (letters and numbers, up to 8 characters). The app remembers the count and names for each sample; a new sample, or a new count, starts again from `P1`, `P2`, …
- **Contamination:** before or after.
- **Aged:** yes or no, and for how long.
- **Washed:** yes or no, the wash condition, how long ago it ended, and whether the specimen is now wet, damp or dry. If it was both aged and washed, which came first.
- **Notes:** anything else worth recording.

Times can be in minutes, hours or days, and decimals are fine. Leave a time empty if you don't know it; it is saved as `unknown`.

Photos are named by sample and piece, for example `<time>-C205_P2_0deg_r01.CR3`. Each capture's folder also says the condition, for example `C205_P2_contam_aged7d_washed_<time>/` (`clean` or `contam`, then `aged` with its length, then `washed`).

Every answer is saved in full in `case_manifest.json` next to the photos.

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

The camera code is in [`camera_control/capture/cameras.py`](camera_control/capture/cameras.py). The session profile is in [`profile.py`](camera_control/capture/profile.py), and the specimen answers and naming are in [`specimen.py`](camera_control/capture/specimen.py).

## Tests

The tests use fake camera tools in `tests/fakes`, so they don't need a camera. The fakes are shell scripts, so the tests run on macOS and Linux only.

```bash
.venv/bin/python -m unittest discover tests
```
