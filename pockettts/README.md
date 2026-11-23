# AiPi PocketTTS Bridge

Use the PocketTTS Android Engine already installed on your Moto to synthesize Harley's replies. This add-on requires the existing AiPi Kin profiles setup in Termux. It uses a local connection authenticated with an app-generated pairing key. Neither app needs a new cloud account.

## Setup on the Moto

1. Copy the `pockettts` folder from this repository to Downloads as `aipi-pockettts`. Tap the included `AiPi-PocketTTS-Bridge.apk` to install it. Android may ask you to allow app installs from your file manager.
2. In **Pocket TTS Android Engine**, select `drama` and tap **Save Selection and Parameters**. Keep Pocket TTS Android Engine as the preferred system TTS engine.
3. In **AiPi PocketTTS Bridge**, tap **Start bridge**, then **Copy pairing key**. Keep the bridge running when you use Harley.
4. In the running AiPi Termux session, press **Ctrl+C**. At the shell prompt, run:

   ```sh
   bash ~/storage/downloads/aipi-pockettts/termux/install.sh
   ```

   Run `termux-setup-storage` if Termux cannot access Downloads. If you extracted to a different folder, adjust the script path. At the pairing prompt, paste the key copied from the bridge app and press Enter. The prompt hides what you paste.
5. If the installer reports that FFmpeg is missing, run `pkg install ffmpeg`.
6. Run `bash ~/start-aipi.sh` and enter Harley's Kin ID as usual. Try a short line on the AiPi, then restart with Gamora's ID to confirm she still uses Piper.

When PocketTTS is unavailable, Harley falls back to her Piper alias and Termux prints `PocketTTS unavailable. Using Piper for this reply.` If you see that, check that the bridge is running, PocketTTS is the preferred Android TTS engine, and the pairing key came from the currently installed bridge. PocketTTS synthesis has a 20-second deadline.

## Restore the original proxy

Stop the AiPi launcher before restoring the two backed-up files.

```sh
cd ~/aipi-phone
cp bridge.py.before-pockettts bridge.py
cp kin_profiles.py.before-pockettts kin_profiles.py
bash ~/start-aipi.sh
```

## Included files

The APK and Android source are included. The APK uses NanoHTTPD 2.3.1, whose license is included in `android/`. The Termux installer preserves the previous bridge and proxy before patching them. Treat `~/aipi-phone/data/pockettts-bridge.key` as a local credential and keep it out of Git.
