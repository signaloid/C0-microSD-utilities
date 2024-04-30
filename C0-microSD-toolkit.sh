#!/bin/bash

#
#	Copyright (c) 2024, Signaloid.
#
#	Permission is hereby granted, free of charge, to any person obtaining a copy
#	of this software and associated documentation files (the "Software"), to deal
#	in the Software without restriction, including without limitation the rights
#	to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#	copies of the Software, and to permit persons to whom the Software is
#	furnished to do so, subject to the following conditions:
#
#	The above copyright notice and this permission notice shall be included in all
#	copies or substantial portions of the Software.
#
#	THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#	IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#	FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#	AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#	LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#	OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#	SOFTWARE.
#

flashConfigWord='false'
flashBootloader='false'
flashSoC='false'
flashUserData='false'
checkBootloader='true'

kVersion="1.0"

kExitCodeSuccess=0			# Success exit code
kExitCodeFail=1				# Failiure exit code
kMaxAttempts=5				# Maximum flashing attempts

kBlockSize=512				# Block size used in dd				0x200
kBootloaderCheckOffset=131072		# 128 KiB offset for bootloader check word	0x20000	
kBootloaderSwitchConfigOffset=262144	# 256 KiB offset for switch config		0x40000
kBootloaderUnlockOffset=393216		# 384 KiB offset for unlocking bootloader	0x60000
kBootloaderBitstreamOffset=524288	# 512 KiB offset for bootloader bitstream	0x80000
kSoCBitstreamOffset=1048576		# 1.0 MiB offset for SoC bitstream		0x100000
kUserBitstreamOffset=1572864		# 1.5 MiB offset for application bitstream	0x180000
kUserDataOffset=2097152			# 2.0 MiB offset for userspace			0x200000

kBootloaderCheckWord="53424c44"
kBootloaderUnlockWord="55424c44"

confirmAction() {
	while true; do
		read -rp "WARNING: This action may render the device inoperable. Proceed? (y/n) " yn
		case $yn in
			[Yy]* ) break;; # If yes, exit loop and proceed
			[Nn]* ) echo "Operation cancelled."; exit;; # If no, exit script
			* ) echo "Please answer yes or no.";; # Otherwise, ask again
		esac
	done
}

printVersion() {
	echo "Signaloid C0-microSD-toolkit. Version $kVersion"
}

printUsage() {
	printVersion
	echo ""	
	echo "Usage: $0 -t <targetDevice> [options]"
	echo ""
	echo "Mandatory options:"
	echo "  -t <targetDevice>   Specify the target device path."
	echo ""
	echo "Optional options:"
	echo "  -b <inputFile>      Specify the input file for flashing (required with -u, -q, or -w)."
	echo "  -u                  Flash user data (mutually exclusive with -q, -w, -s)."
	echo "  -q                  Flash bootloader (mutually exclusive with -u, -w, -s)."
	echo "  -w                  Flash the Signaloid SoC (mutually exclusive with -u, -q, -s)."
	echo "  -s                  Switch boot mode (mutually exclusive with -u, -q, -w)."
	echo "  -f                  Force flash sequence (do not check for bootloader)."
	echo "  -h                  Display this help message and exit."
	echo "  -v                  Display tool version and exit."
	echo ""
	echo "Examples:"
	echo "  $0 -t /dev/sdx -b image.bin -u   # Flash user data to device /dev/sdx using image.bin"
	echo "  $0 -t /dev/sdx -s                # Switch boot mode of /dev/sdx"
	echo ""
	echo "Note: -b is required when using -u, -q, or -w to specify the input file needed for flashing."
}

while getopts t:b:uqswfhv flag
do
	case "${flag}" in
		t) targetDevice=${OPTARG};;
		b) inputFile=${OPTARG};;
		u) flashUserData='true';;
		q) flashBootloader='true';;
		w) flashSoC='true';;
		s) flashConfigWord='true';;
		f) checkBootloader='false';;
		h) printUsage;exit $kExitCodeSuccess;;
		v) printVersion;exit $kExitCodeSuccess;;
		*) printUsage;exit $kExitCodeFail;;
	esac
done


if [ -z "$targetDevice" ]; then
	echo "No target device argument supplied"
	exit $kExitCodeFail
fi

#
#	Writing to $kBootloaderSwitchConfigOffset switches the boot config word
#
switchBootConfig() {
	echo "Switching device boot mode"
	dd if=/dev/zero of="$targetDevice" bs=$kBlockSize count=1 seek="$((kBootloaderSwitchConfigOffset/kBlockSize))" status=none
	echo "Device configured succesfully"
	echo "Power cycle the device to boot in new mode"
}

unlockBootloader() {
	echo "Unlocking bootloader"
	echo -n $kBootloaderUnlockWord | xxd -r -p | dd of="$targetDevice" bs=1 seek=$kBootloaderUnlockOffset count=4 conv=notrunc status=none
}

lockBootloader() {
	echo -n "00000000" | xxd -r -p | dd of="$targetDevice" bs=1 seek=$kBootloaderUnlockOffset count=4 conv=notrunc status=none
}

if ${flashConfigWord}; then
	switchBootConfig
	exit $kExitCodeSuccess
fi

if [ -z "$inputFile" ]; then
	echo "No bitstream argument supplied"
	exit $kExitCodeFail
fi

if [ -f "$inputFile" ]; then
	echo "File name: \"$inputFile\""
else
	echo "File named $inputFile does not exist."
	exit $kExitCodeFail
fi

#
#	After this point the bootloader should be loaded
#
checkBootloaderWord=$(dd if=$targetDevice bs=$kBlockSize count=1 skip=$((kBootloaderCheckOffset/kBlockSize)) status=none 2> /dev/null | head -c 4 | xxd -p)
if [ "$checkBootloader" = "false" ]; then
	echo "Skipping bootloader check (-f option)"
elif [ "$checkBootloaderWord" = $kBootloaderCheckWord ]; then
	echo "Device is in bootloader mode"
else
	echo "Device is not in bootloader mode. Switching..."
	switchBootConfig
	exit $kExitCodeSuccess
fi

inputFileBytes=$(wc -c < "$inputFile")
if ${flashBootloader}; then
	echo "Loading Bootloader bitstream"
	echo "Bitstream size: $inputFileBytes Bytes."
	confirmAction
	unlockBootloader
	flashOffset=$kBootloaderBitstreamOffset
elif ${flashSoC}; then
	echo "Loading Signaloid Core bitstream"
	echo "Bitstream size: $inputFileBytes Bytes."
	confirmAction
	unlockBootloader
	flashOffset=$kSoCBitstreamOffset
elif ${flashUserData}; then
	echo "Data file size: $inputFileBytes Bytes."
	echo "Loading userspace data"
	flashOffset=$kUserDataOffset
else
	echo "Bitstream size: $inputFileBytes Bytes."
	echo "Loading user bitstream"
	flashOffset=$kUserBitstreamOffset
fi

#
#	Flash data and verify
#
for ((i=1; i<=kMaxAttempts; i++)); do
	echo "Attempt $i of $kMaxAttempts"

	echo "FLASHING..."
	dd if="$inputFile" of="$targetDevice" bs=$kBlockSize seek="$((flashOffset/kBlockSize))" status=none
	sleep 0.5

	echo "VERIFY..."
	if sudo dd if="$targetDevice" bs=1 count="$inputFileBytes" skip="$((flashOffset))" status=none | cmp - "$inputFile"; then
		echo "Success: The data matches"
		lockBootloader
		echo "DONE"
		exit $kExitCodeSuccess
	else
		echo "Error: The data do not match"
	fi
	sleep 0.5
done

lockBootloader
echo "FAIL"
exit $kExitCodeFail
