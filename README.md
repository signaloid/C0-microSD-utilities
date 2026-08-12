# Signaloid Compute Module Utilities
This repository offers a set of common C and Python libraries for building host applications that interact
with Signaloid Compute modules like the [Signaloid C0-microSD hot-pluggable hardware module](https://github.com/signaloid/C0-microSD-hardware), as well as toolkits, which you can use to flash new bitstreams and firmware to the devices.

## Interfacing with the Signaloid C0-microSD
When connected to a host computer, the Signaloid C0-microSD presents itself as an unformatted block
storage device. Communication with the device is achieved through block reads and writes to a set of
pre-defined addresses. The C0-microSD can operate in two different modes when connected to a
host: `Bootloader` mode and `Signaloid SoC` mode.

- `Bootloader` mode: This mode allows flashing new bitstreams and firmware to the device.
- `Signaloid SoC` mode: This is the built-in Signaloid C0 SoC, which features a subset of
  Signaloid's uncertainty-tracking technology.

Interfacing with the C0-microSD varies depending on the active mode.

In the `src/` folder, you will find common functions and classes for building C and Python applications
that interact with the C0-microSD when the Signaloid SoC mode is active.

## Using the `C0_microSD_toolkit.py` tool
You can use the `C0_microSD_toolkit.py` Python script to configure the C0-microSD and flash new
firmware. The script is written and tested in Python 3.10 and does not use any
additional libraries. Following are the program's command-line arguments and usage examples:

```
usage: C0_microSD_toolkit.py [-h] -t TARGET_DEVICE [-b INPUT_FILE] [-u | -q | -w | -s | -i] [-f]

Signaloid C0_microSD_toolkit. Version 1.1

options:
  -h, --help        Show this help message and exit.
  -t TARGET_DEVICE  Specify the target device path.
  -b INPUT_FILE     Specify the input file for flashing (required with -u, -q, or -w).
  -p PAD_SIZE       Pad input file with zeros to target size.
  -u                Flash user data.
  -q                Flash new Bootloader bitstream.
  -w                Flash new Signaloid SoC bitstream.
  -s                Switch boot mode.
  -i                Print target C0-microSD information, and run data verification.
  -y                Flash warmboot sector.
  -f                Force flash sequence (do not check for bootloader).
```

> [!IMPORTANT]  
> All options except of `-s` require the C0-microSD to be in **Bootloader** mode. 

### Examples:
The following examples assume that the C0-microSD is located in`/dev/sda`.

Flash new custom user bitstream:
```sh
sudo python3 ./C0_microSD_toolkit.py -t /dev/sda -b user-bitstream.bin
```

Flash new user data:
```sh
sudo python3 ./C0_microSD_toolkit.py -t /dev/sda -b program.bin -u
```

Flash new Bootloader bitstream:
```sh
sudo python3 ./C0_microSD_toolkit.py -t /dev/sda -b bootloader-bitstream.bin -q
```

Flash new Signaloid SoC bitstream:
```sh
sudo python3 ./C0_microSD_toolkit.py -t /dev/sda -b signaloid-soc.bin -w
```

Toggle boot mode of C0-microSD:
```sh
sudo python3 ./C0_microSD_toolkit.py -t /dev/sda -s
```

Print target C0-microSD information and verify loaded bitstreams:
```sh
sudo python3 ./C0_microSD_toolkit.py -t /dev/sda -i
```

> [!NOTE]  
> Using the `-s` option will toggle the active configuration. So, if the device has booted in 
> `Bootloader` mode, this option will switch to `Signaloid Core` mode, and vice versa.

# C0-SD Utilities
This repository includes C and Python libraries for the Signaloid **C0-SD family** of compute modules — both the **C0-microSD+** and the **C0-SD** — as well as the `C0_SD_toolkit`, which you can use to flash new bitstreams and application binaries and to inspect a connected device.

## Interfacing with the Signaloid C0-SD family
When connected to a host computer, a C0-microSD+ or C0-SD presents itself as an unformatted block
storage device. The host computer communicates with the device through block reads and writes to a set of
pre-defined addresses. In contrast to the C0-microSD, these modules operate in a single mode, which
supports flashing and running new application binaries, as well as updating the FPGA bitstream. The
`--variant` option selects the target module; when it is omitted, the toolkit auto-detects the module
from the device's bitstream (see *Selecting the compute module* below).

## Using the `C0_SD_toolkit.py` tool
You can use the `C0_SD_toolkit.py` Python script to configure a C0-microSD+ or C0-SD and flash new
firmware. The script is written and tested in Python 3.10 and does not use any additional libraries.
Following are the program's command-line arguments and usage examples:

```
usage: C0_SD_toolkit.py [-h] [--variant {C0-microSD+,C0-SD}]
                        [--regmap-path REGMAP_PATH]
                        target_device <command> ...

Signaloid C0-SD toolkit. Version 2.3

positional arguments:
  target_device         Target device path
  <command>
    info                Print target device info and bitstream metadata.
    status              Print verbose status (COMMAND, CONFIG, STATUS, and
                        SD_CONFIG on C0-SD).
    flash-application   Flash an application binary
    flash-bitstream     Flash a bitstream file
    configure (config)  Apply a configuration action (per-variant)

options:
  -h, --help            show this help message and exit
  --variant {C0-microSD+,C0-SD}
                        Hardware variant. Default: auto-detect from the
                        device's bitstream; required if it cannot be
                        identified.
  --regmap-path REGMAP_PATH
                        Path to the regmap package directory for the selected
                        --variant (defaults to the built-in regmaps).
```

### Selecting the compute module (`--variant`)
The toolkit works with both the C0-microSD+ and the C0-SD. Which variant a command targets is
resolved as follows:

- **`--variant` omitted:** the toolkit auto-detects the module by decoding the JSON metadata prefix
  of the device's bitstream and reading its `compute_module_type` field. This is a lookup by key on
  the decoded JSON, so it is independent of the order or position of the fields (future bitstream
  revisions may reorder them). If the module is identified, that variant is used.
- **`--variant` omitted and the module cannot be identified** (e.g. a blank device, or a bitstream
  without Signaloid metadata): the toolkit exits with an error asking you to pass `--variant`.
- **`--variant` given:** it overrides auto-detection. If the given variant does not match the one
  declared by the bitstream — or the bitstream could not be identified — the toolkit prints a warning
  and proceeds with the variant you specified.

Detection messages and warnings are written to `stderr`, so they do not interfere with command output.

### The `info` command
`info` decodes and prints the bitstream's embedded metadata (compute module type, creation date,
bitstream type, metadata-schema version, size, and CRC). By default it reads only the metadata prefix
and **does not** run CRC verification, because the default device configuration exposes only the first
4 KiB of flash and locks the rest.

Pass `--verify` to check the bitstream CRC: the toolkit unlocks the bitstream section, reads and
verifies the full bitstream, then re-locks the section (it is always re-locked afterwards, even if
verification fails).

```
usage: C0_SD_toolkit.py target_device info [-h] [--raw] [--verify]

options:
  -h, --help  show this help message and exit
  --raw       Print the raw JSON metadata object instead of labelled fields.
  --verify    Unlock the bitstream section, verify its CRC, then re-lock it
              (off by default; the locked device exposes only the first 4 KiB
              of flash).
```

### Examples:
The following examples assume the target device is located at `/dev/sda`. They omit `--variant`, so
the toolkit auto-detects the module from the device; pass `--variant=C0-microSD+` or
`--variant=C0-SD` to force a specific one.

Print target device info (metadata only, no CRC verification):
```sh
sudo python3 C0_SD_toolkit.py /dev/sda info
```

Print device info and verify the bitstream CRC (unlocks then re-locks the bitstream section):
```sh
sudo python3 C0_SD_toolkit.py /dev/sda info --verify
```

Flash new Signaloid SoC application binary:
```sh
sudo python3 C0_SD_toolkit.py /dev/sda flash-application program.bin
```

Flash new FPGA bitstream:
```sh
sudo python3 C0_SD_toolkit.py /dev/sda flash-bitstream bitstream.bin
```

Start the Signaloid SoC core:
```sh
sudo python3 C0_SD_toolkit.py /dev/sda config core-start
```

Stop and reset the Signaloid SoC core:
```sh
sudo python3 C0_SD_toolkit.py /dev/sda config core-stop
```

# SD-Dev utilities
## Using the `SD_Dev_toolkit.py` tool
You can use the `SD_Dev_toolkit.py` to detect and power-cycle the SD cards on-board the SD-Dev.
```
usage: SD_Dev_toolkit.py [-h] [-p]

Signaloid SD_Dev_toolkit. Version 0.1

options:
  -h, --help         Show this help message and exit.
  -p, --power-cycle  Power-cycle the onboard full-size SD and microSD cards.
```

## Using the `SD_Dev_power_measure.py` tool
You can use the `SD_Dev_power_measure.py` to read and log power measurement data using the SD-Dev
on-board current sense circuitry. ADC channel 0 corresponds to the full-size SD card socket and
channel 1 to the microSD card socket. For this functionality to work, you must first enable the
I2C kernel module. If you use one of the official Raspberry-Pi OS images, you can do that using
the `raspi-config` command.
```
usage: SD_Dev_power_measure.py [-h] [-s SMBUS_NUMBER] [-o OUTPUT_FILENAME] [-c {0,1}] [-g {1,2,4,8}] [-r {12,14,16}]

Signaloid SD_Dev_power_measure. Version 0.1

options:
  -h, --help            Show this help message and exit.
  -s SMBUS_NUMBER, --smbus-number SMBUS_NUMBER
                        Specify the target smbus number. (default: 1)
  -o OUTPUT_FILENAME, --output_filename OUTPUT_FILENAME
                        Filename of output csv file. When set, the application will log measurements to this file. (default: None)
  -c {0,1}, --channel {0,1}
                        ADC channel. Channel 0 corresponds to the full-size SD card socket and channel 1 to the microSD card socket. (default: 1)
  -g {1,2,4,8}, --gain {1,2,4,8}
                        ADC Programmable Gain Amplifier (PGA) gain. (default: 4)
  -r {12,14,16}, --samle-rate-bits {12,14,16}
                        Sample bits. (default: 12)
```

[^1]: Implementing a subset of the full capabilities of the Signaloid C0 processor.


# The `signaloid_api` module
You can use the `signaloid_api` module to build and download binaries for applications that support uncertainty-tracking on the Signaloid SoC, from Signaloid's API. This module provides both a command-line interface and a Python API for programmatic usage.

For detailed documentation and examples, please see the [signaloid_api README](src/python/signaloid_api/README.md).

## Error Handling

The module provides consistent error handling with detailed error messages. When an error occurs, you'll see output in the following format:

```
Action: {action_name}
Status Code: {http_status_code}
Headers: {response_headers}
Response Body: {error_details}
{action_name} failed: {error_details}
```

For example, when hitting the repository limit:
```
Action: Repository connection
Status Code: 403
Headers: {'Content-Type': 'application/json', ...}
Response Body: {
  "error": "Forbidden",
  "message": "Repositories limit reached. Upgrade your account at https://signaloid.io/billing."
}
Repository connection failed: {'error': 'Forbidden', 'message': 'Repositories limit reached. Upgrade your account at https://signaloid.io/billing.'}
```

Common error scenarios include:
- Repository limit reached
- Invalid API key
- Repository not found
- Build failures
- Network errors

## Quick Start

```bash
# Download a binary using repository ID
python -m src.python.signaloid_api.core_downloader --api-key YOUR_API_KEY --repo-id YOUR_REPO_ID

# Build directly from a GitHub repository URL
python -m src.python.signaloid_api.core_downloader --api-key YOUR_API_KEY --repo-url https://github.com/signaloid/Signaloid-C0-microSD-Demo-Calculator

# For help and more options
python -m src.python.signaloid_api.core_downloader --help
```

### Example Output

When using a GitHub repository URL, the tool will:
1. Verify the repository exists and has a `src` directory
2. Connect the GitHub repository to the Signaloid Cloud Developer Platform
3. Build the application with the specified core (default: C0-microSD-N)
4. Download the resulting binary as `buildArtifacts.tar.gz`

The downloaded binary can then be flashed to your C0-microSD device using the C0_microSD_toolkit.py script.

```bash
$ python -m src.python.signaloid_api.core_downloader --api-key YOUR_API_KEY --repo-url https://github.com/signaloid/Signaloid-C0-microSD-Demo-Calculator

Verifying GitHub repository: https://github.com/signaloid/Signaloid-C0-microSD-Demo-Calculator
Repository signaloid/Signaloid-C0-microSD-Demo-Calculator is valid and has a src directory
Creating Signaloid repository from GitHub URL: https://github.com/signaloid/Signaloid-C0-microSD-Demo-Calculator
Repository created with ID: rep_5c8104c6bb47468bbce9e0d1a83d2123

Using C0-microSD-N (default)

Creating build for repository rep_5c8104c6bb47468bbce9e0d1a83d2123 with C0-microSD-N...
Build created with ID: bld_ddff3fd873304eccaf68b7ce6f277123

Waiting for build to complete...
Build status: Initialising
Build status: Completed

Getting build outputs...
Build outputs retrieved

Build output:


Downloading binary...
Binary downloaded to: buildArtifacts.tar.gz
```
