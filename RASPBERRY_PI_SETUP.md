# Raspberry Pi Setup
This project provides comprehensive driver support for the PiSugar Whisplay Hat, enabling easy control of the onboard LCD screen, physical buttons, LED indicators, and audio functions.

## Hardware:
* Raspberry Pi Zero WH
* PiSugar Whisplay HAT
* PiSugar 3 1200mAh

## Install Whisplay Drivers
```bash
git clone https://github.com/PiSugar/Whisplay.git --depth 1
cd Whisplay/Driver
sudo bash install_wm8960_drive.sh
sudo reboot
```

The program can be tested after the driver is installed.
```bash
cd Whisplay/example
sudo bash run_test.sh
```

The system provides a graphical interface to set more complex functions. You need to press F6 to select the sound card device, and the sound card name is wm8960.
```
sudo alsamixer
```
The default volume is relatively low; it can be adjusted up to around 70, beyond which it will cause distortion.

## Install PiSugar Power Manager
```bash
wget https://cdn.pisugar.com/release/pisugar-power-manager.sh
bash pisugar-power-manager.sh -v 1.7.7
```
>[!WARNING]
>Do NOT install 2.x.x versions — they are incompatible with Pi Zero (ARMv6).

Verify Battery & Model
```bash
echo "get battery" | nc 127.0.0.1 8423
echo "get model"   | nc 127.0.0.1 8423
```

Lock the working version (ciritical)
```
sudo apt-mark hold pisugar-server pisugar-poweroff
```
