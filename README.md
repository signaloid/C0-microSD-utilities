# C0-microSD Utilities
This repository contains utilities for interacting with the bootloader of the [Signaloid C0-microSD hot-pluggable hardware module](https://github.com/signaloid/C0-microSD-hardware).

## The C0-microSD bootloader
The C0-microSD built-in bootloader is designed to allow users to update (1) the custom bitstream configured into the C0-microSD; (2) the Signaloid C0 SoC bitstream[^1]; (3) the bootloader itself.

### Address spaces
The non-volatile flash memory of the device is divided into 6 different address spaces:

1.  `0x040000 - 0x040003` Boot config word (used to switch between bootloader and Signaloid C0 SoC)
2.  `0x080000 - 0x08FFFF` Bootloader bitstream
3.  `0x100000 - 0x10FFFF` Signaloid C0 SoC bitstream
4.  `0x180000 - 0x18FFFF` User bitstream
5.  `0x200000 - 0x8000000` Userspace (First 128KiB are used by Signaloid C0 SoC for initializing memory)

### Programmatically identifying the bootloader
When the bootloader is active, it presents itself as an empty 19.7MiB block storage device. To identify if the bootloader is active, users can read the 4 characters "SBLD" in addresses `0x20000 - 0x20003`. Following is a bash script example where the host computer has mounted the C0-microSD on `/dev/sda/` (you need to change `targetDevice` to point to where C0-microSD is mounted on your computer).

```bash
targetDevice="/dev/sda/"
kBootloaderCheckOffset=4194304 #  4 MiB offset for bootloader switch
kBootloaderCheckWord="53424c44" # Hex for "SBLD"
kBlockSize=512

checkBootloader=$(dd if=$targetDevice bs=$kBlockSize count=1 skip=$(($kBootloaderCheckOffset/$kBlockSize)) | head -c 4 | xxd -p)
if [ "$checkBootloader" == $kBootloaderCheckWord ]; then
    echo "Device is in bootloader mode"
else
    echo "Device is not in bootloader mode"
fi
```

## The `C0-microSD-toolkit.sh` tool
The `C0-microSD-toolkit.sh` shell script utilizes linux `dd` commands to configure the C0-microSD and flash new firmware. Following are the program's parameters and usage examples:

```
Usage: C0-microSD-toolkit.sh -t <targetDevice> [options]

Mandatory options:
  -t <targetDevice>   Specify the target device path.

Optional options:
  -b <inputFile>      Specify the input file for flashing (required with -u, -q, or -w).
  -u                  Flash user data (mutually exclusive with -q, -w, -s).
  -q                  Flash bootloader (mutually exclusive with -u, -w, -s).
  -w                  Flash the Signaloid C0 SoC (mutually exclusive with -u, -q, -s).
  -s                  Switch boot mode (mutually exclusive with -u, -q, -w).
  -f                  Force flash sequence (do not check for bootloader).
  -h                  Display this help message and exit.

Note: -b is required when using -u, -q, or -w to specify the input file needed for flashing.
```

#### Examples:
Flashing new user bitstream to `/dev/sda`:
```sh
sudo bash ./C0-microSD-toolkit.sh -t /dev/sda -b user-bitstream.bin
```

Flashing new userspace data to `/dev/sda`:
```sh
sudo bash ./C0-microSD-toolkit.sh -t /dev/sda -b program.bin -u
```

Flashing new bootloader to `/dev/sda`:
```sh
sudo bash ./C0-microSD-toolkit.sh -t /dev/sda -b bootloader-bitstream.bin -q
```

Flashing new Signaloid C0 SoC to `/dev/sda`:
```sh
sudo bash ./C0-microSD-toolkit.sh -t /dev/sda -b signaloid-soc.bin -w
```

Toggling boot mode of `/dev/sda`:
```sh
sudo bash ./C0-microSD-toolkit.sh -t /dev/sda -s
```

> [!NOTE]  
> Using the `-s` option will toggle the active configuration. So, if the device has booted in `bootloader` mode, this option will switch to `Signaloid C0 SoC` mode. The opposite will happen if the device has booted in `Signaloid C0 SoC` mode.

[^1]: Implementing a subset of the full capabilities of the Signaloid C0 processor.
