# Emu Industries Malware Analysis

```sh
cd "$HOME/malware"
chmod +x emu.py setup.sh
sudo ./setup.sh 'CTF{your_fixed_flag}'
```

```sh
sudo cp "$HOME/Downloads/Windows 10 x64.iso" "$HOME/malware/prepare/windows.iso"
sudo chgrp emulab "$HOME/malware/prepare/windows.iso"
sudo chmod 640 "$HOME/malware/prepare/windows.iso"
sudo ./emu.py prepare --install-iso "$HOME/malware/prepare/windows.iso"
```

```sh
sudo ./emu.py prepare
```

```sh
sudo ./emu.py prepare --save-baseline
```

```bat
shutdown /s /t 0
```

```sh
sudo ./emu.py reference "$HOME/Downloads/submission.zip"
```
