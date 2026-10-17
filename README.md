# NexGenPPT Camera Control

Desktop app for photographing fabric specimens with a Canon EOS RP over USB. It runs on macOS and Windows.

The app checks the camera and applies the session profile. It then takes 4 photos of one specimen alone on the paper, either a whole parent or one cut piece: 2 at 0°, and 2 more after you rotate it 180°. Photos are saved to `Documents/NexGenPPT Camera Control/<date>/`, along with a log for each photo and a `case_manifest.json`.

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

1. Install these:
   - [Python](https://www.python.org/downloads/) 3.12. In the installer, tick **Add python.exe to PATH**.
   - [Git for Windows](https://git-scm.com/download/win).
   - [digiCamControl](https://digicamcontrol.com) (tested with 2.1.6). In digiCamControl, set transfer to **Save to PC only**.
2. On the camera itself, set these once: Adobe RGB colour space, Picture Style Neutral, spot metering, 2-second self-timer, Auto Lighting Optimizer off, white balance shift 0,0, and auto power off disabled. digiCamControl can't set them, and the camera keeps them until someone changes them.
3. Open Command Prompt, then download the app and install its packages:

   ```bat
   cd %USERPROFILE%
   git clone -b main https://github.com/FanZhouVictor/NexGenPPT_camera_control.git
   cd NexGenPPT_camera_control
   py -m venv .venv
   .venv\Scripts\pip install -r requirements.txt
   ```

4. Make a desktop shortcut:
   1. In File Explorer, open the `NexGenPPT_camera_control` folder in your user folder. Right-click `NexGenPPT Camera Control.pyw` and choose **Show more options → Send to → Desktop (create shortcut)**.
   2. Right-click the new shortcut, choose **Properties**, click **Change Icon…**, then **Browse…**, and pick `camera_control\assets\icon.ico` in the same folder. Click **OK** twice.
   3. Rename the shortcut to `NexGenPPT Camera Control`.

Open the app with the shortcut. Each time, it first gets the latest version from the `main` branch and installs any new packages, then opens the app, with no console window. Without internet it skips the update. If the app can't start, it shows a message and writes the details to `launch_error.log` in the app's folder.

Keep digiCamControl open while you use the app. On both systems, quit EOS Utility first, because only one program can use the camera at a time.

## Run

```bash
.venv/bin/python -m camera_control          # macOS
.venv\Scripts\python -m camera_control      # Windows, without the update step
```

Photos are saved in `NexGenPPT Camera Control` inside your Documents folder. To save them somewhere else, set `CAMERA_OUTPUT_ROOT` to a folder path before you start the app.

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
