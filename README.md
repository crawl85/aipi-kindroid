# AiPi-Lite Kindroid integration

Adds two selectable portraits, per-Kin Piper voices, and optional Kindroid chat images to an existing AiPi-Lite setup. Restart the Termux launcher with the alternate Kin ID to select the alternate portrait and voice. The firmware polls the phone for the active portrait while idle.

## Latest setup

This version includes the [PocketTTS Android bridge and Termux installer](pockettts/README.md). It can use the saved Android PocketTTS voice for the alternate Kin, with Piper as fallback. The default Kin stays on Piper. Install the base Kin profiles first, then follow the PocketTTS instructions if you want that feature. An existing working installation can skip the base installer.

The Moto and AiPi can use regular home Wi-Fi or the same hotspot. Use the Moto's Wi-Fi IPv4 address when it joins another device's network. When the Moto hosts the hotspot itself, use its hotspot gateway address. Set the AiPi OTA URL and XiaoZhi WebSocket URL to the same Moto address. The PocketTTS bridge uses loopback on the Moto and keeps its pairing when the network changes.

## Phone setup

This is an add-on for an existing Termux installation with `~/start-aipi.sh`, `~/aipi-phone/bridge.py`, and `~/aipi-phone/data/.config.yaml`. The launcher, complete XiaoZhi server installation, voice models, and Kindroid credentials are supplied by your existing setup. The installer backs up the bridge and config on first installation.

1. Extract this repository on the phone. Stop the running services with Ctrl+C.
2. Run `bash /path/to/extracted/aipi-kindroid-github/phone/install-phone.sh`. Enter the alternate Kin ID and choose the Piper aliases. Defaults are `alloy` and `nova`. The installer retains the original Harley/Gamora labels for compatibility. Install FFmpeg in Termux if you use chat images.
3. Connect the AiPi and Moto as described above. In the URLs below substitute the Moto’s reachable IPv4 address for the example IP.
4. Set XiaoZhi's advertised WebSocket URL in `~/aipi-phone/data/.config.yaml` and set the AiPi's Custom OTA URL in its Wi-Fi setup page.

   | Setting | Example |
   | --- | --- |
   | XiaoZhi WebSocket | `ws://192.168.1.42:8000/xiaozhi/v1/` |
   | AiPi Custom OTA URL | `http://192.168.1.42:8003/xiaozhi/ota/` |
   | Avatar relay test | `http://192.168.1.42:8082/aipi/avatar` |

5. Start `bash ~/start-aipi.sh`, enter your API key and desired Kin ID, and reboot the AiPi. Leave Termux running. From another device on the same network, the OTA page should show the hotspot IP in the WebSocket address. The avatar URL should return `H` for the alternate portrait and `G` for the default.

### English transcription

The Piper alias controls the spoken reply. Both profiles share XiaoZhi's speech recognizer. If you're running the multilingual SherpaASR SenseVoice model and your installed provider reads the `language` option, set `language: en` under `ASR → SherpaASR` in the live config. Back up that config first, restart Termux, and check your transcript in Kindroid. If the setting has no effect, inspect the installed provider inside the environment launched by `start-aipi.sh` to see how it initializes SenseVoice. The exact transcription change on the working phone was not captured in this source archive.

## Firmware build

1. Check out [XiaoZhi ESP32](https://github.com/78/xiaozhi-esp32) at revision `4de00aed740595a8713b01f8332b9b2cf30685bc` (v2.6.0). The source package specifies ESP-IDF v6.1.
2. From the upstream checkout, run `git apply /path/to/extracted/aipi-kindroid-github/firmware/aipi-kin-profiles.patch`.
3. Prepare two directories of original or authorized images. Each needs `closed.png`, `parted.png`, `open.png`, and `blink.png`. Use consistent framing.
4. Install Pillow with `python -m pip install Pillow` and generate the headers from the upstream checkout:

   ```sh
   python /path/to/extracted/aipi-kindroid-github/firmware/generate_frames.py \
     /path/to/default-frames /path/to/alternate-frames main/boards/xorigin/aipi-lite
   ```

5. Run `python scripts/build.py xorigin/aipi-lite --name aipi-lite --language en-US`. For the 16 MB XOrigin AiPi-Lite with the original matching partition layout and active app slot at `0x20000`, ESPFlash can write the app image there with ESP32-S3, 115200 baud, SPI speed/mode kept, and full-chip erase off. Verify your partition layout and back up your working firmware before flashing.

The firmware patch contains the display logic. This archive leaves firmware binaries, avatar artwork, and voice model files out of the repository. See `LICENSE-xiaozhi` for the upstream notice.

## Publishing

Before pushing, review `git status --short` and the staged files. Keep actual Kin IDs, API keys, Wi-Fi passwords, live settings, logs, and chat images local. Start with a private repository if you want to review the upload before sharing it.
