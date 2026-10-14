# Camera session profile applied by the camera check.

from dataclasses import dataclass


@dataclass(frozen=True)
class ProfileSetting:
    key: str        # gphoto2 config path; other camera backends map it to their own name
    value: str
    label: str      # shown in the log and in diagnostics


SESSION_PROFILE = [
    ProfileSetting("/main/imgsettings/iso", "100", "ISO speed"),
    ProfileSetting("/main/capturesettings/aperture", "8", "Aperture (f/)"),
    ProfileSetting("/main/capturesettings/shutterspeed", "1/125", "Shutter speed"),
    ProfileSetting("/main/imgsettings/whitebalance", "Manual", "White balance mode (Manual = Custom)"),
    ProfileSetting("/main/imgsettings/colorspace", "AdobeRGB", "Color space"),
    ProfileSetting("/main/imgsettings/picturestyle", "Neutral", "Picture Style"),
    ProfileSetting("/main/capturesettings/imageformat", "RAW + Large Fine JPEG", "Image quality"),
    ProfileSetting("/main/capturesettings/exposurecompensation", "0", "Exposure compensation"),
    ProfileSetting("/main/capturesettings/meteringmode", "Spot", "Metering mode"),
    ProfileSetting("/main/capturesettings/drivemode", "Timer 2 sec", "Drive mode"),
    ProfileSetting("/main/settings/autopoweroff", "0", "Auto power off (s)"),
    ProfileSetting("/main/settings/capturetarget", "Memory card", "Capture target"),
    ProfileSetting("/main/capturesettings/autolightingoptimizer", "Off", "Auto Lighting Optimizer"),
    ProfileSetting("/main/imgsettings/whitebalanceadjusta", "0", "WB shift A-B"),
    ProfileSetting("/main/imgsettings/whitebalanceadjustb", "0", "WB shift G-M"),
]
