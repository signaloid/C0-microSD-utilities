/*
 *	Copyright (c) 2026, Signaloid.
 *
 *	Permission is hereby granted, free of charge, to any person obtaining a copy
 *	of this software and associated documentation files (the "Software"), to deal
 *	in the Software without restriction, including without limitation the rights
 *	to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 *	copies of the Software, and to permit persons to whom the Software is
 *	furnished to do so, subject to the following conditions:
 *
 *	The above copyright notice and this permission notice shall be included in all
 *	copies or substantial portions of the Software.
 *
 *	THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 *	IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 *	FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 *	AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 *	LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 *	OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 *	SOFTWARE.
 */

#pragma once

#include "C0SoCStatus.h"


/**
 *	@brief	Read data from the Signaloid C0-microSD+ device. This is the entry
 *		function for all read transactions.
 *
 *	@param	device		device path of C0-microSD+
 *	@param	destBuffer	destination buffer for data to be stored
 *	@param	bufferSize	number of bytes to be read
 *	@param	offset		offset address
 *
 *	@return			number of bytes read, -1 if error occurred.
 */
ssize_t hostUtilsReadFromC0microSDPlus(char *  device, void *  destBuffer, size_t bufferSize, off_t offset);

/**
 *	@brief	Write data to the Signaloid C0-microSD+ device. This is the entry
 *		function for all write transactions.
 *
 *	@param	device		device path of C0-microSD+
 *	@param	sourceBuffer	source buffer of data
 *	@param	bufferSize	number of bytes to be written
 *	@param	offset		offset address
 *
 *	@return			number of bytes written, -1 if error occurred.
 */
ssize_t hostUtilsWriteToC0microSDPlus(char *  device, void *  sourceBuffer, size_t bufferSize, off_t offset);

/**
 *	@brief	Read data from Signaloid C0-microSD+ MMIO buffer
 *
 *	@param	device		device path of C0-microSD+
 *	@param	destBuffer	destination buffer, this must be at least kSignaloidSoCConstantsMMIOBufferSizeBytes bytes long
 */
void hostUtilsReadSignaloidSoCMMIOBuffer(char *  device, void *  destBuffer);

/**
 *	@brief	Write data to Signaloid C0-microSD+ MMIO buffer
 *
 *	@param	device		device path of C0-microSD+
 *	@param	sourceBuffer	source buffer, this must be at least kSignaloidSoCConstantsMMIOBufferSizeBytes bytes long
 */
void hostUtilsWriteSignaloidSoCMMIOBuffer(char *  device, void *  sourceBuffer);

/**
 *	@brief	Read Config register of Signaloid C0-microSD+
 *
 *	@param	device		device path of C0-microSD+
 *	@return	uint32_t	Signaloid C0-microSD+ Config register value
 */
uint32_t hostUtilsGetSignaloidSoCConfigRegister(char *  device);

/**
 *	@brief	Write Config register of Signaloid C0-microSD+
 *	@param	device		device path of C0-microSD+
 *	@param	config		config register value
 */
void hostUtilsSetSignaloidSoCConfigRegister(char *  device, uint32_t config);

/**
 *	@brief	Write Command register of Signaloid C0-microSD+
 *	@param	device		device path of C0-microSD+
 *	@param	config		command register value
 */
void hostUtilsSetSignaloidSoCCommandRegister(char *  device, uint32_t command);

/**
 *	@brief	Read and unpack Config register of Signaloid C0-microSD+.
 *
 *	@param	device				device path of C0-microSD+
 *	@param	rstn				return value: Reset signal of SoC core
 *	@param	unlockBitstreamSection	return value: Bitstream section of SPI flash is unlocked
 *	@param	swLedEnable			return value: Software control of onboard LED is enabled
 *	@param	swLed				return value: Software control bit of onboard LED
 *	@param	redLed				return value: Red onboard LED control bit
 *	@param	greenLed			return value: Green onboard LED control bit
 *	@param	blueLed			return value: Blue onboard LED control bit
 *	@param	debugPin0			return value: Debug pin 0 control bit
 *	@param	debugPin1			return value: Debug pin 1 control bit
 *	@param	debugPin2			return value: Debug pin 2 control bit
 */
void
hostUtilsGetSignaloidSoCConfigRegisterUnpacked(
	char *  device,
	bool *  rstn,
	bool *  unlockBitstreamSection,
	bool *  swLedEnable,
	bool *  swLed,
	bool *  redLed,
	bool *  greenLed,
	bool *  blueLed,
	bool *  debugPin0,
	bool *  debugPin1,
	bool *  debugPin2);

/**
 *	@brief	Pack and write Config register of Signaloid C0-microSD+.
 *
 *	@param	device				device path of C0-microSD+
 *	@param	rstn				Reset signal of SoC core
 *	@param	unlockBitstreamSection	Unlock bitstream section of SPI flash
 *	@param	swLedEnable			Enable software control of onboard LED
 *	@param	swLed				Software control bit of onboard LED
 *	@param	redLed				Red onboard LED control bit
 *	@param	greenLed			Green onboard LED control bit
 *	@param	blueLed			Blue onboard LED control bit
 *	@param	debugPin0			Debug pin 0 control bit
 *	@param	debugPin1			Debug pin 1 control bit
 *	@param	debugPin2			Debug pin 2 control bit
 */
void
hostUtilsSetSignaloidSoCConfigRegisterUnpacked(
	char *  device,
	bool rstn,
	bool unlockBitstreamSection,
	bool swLedEnable,
	bool swLed,
	bool redLed,
	bool greenLed,
	bool blueLed,
	bool debugPin0,
	bool debugPin1,
	bool debugPin2);

/**
 *	@brief	Read status register of Signaloid C0-microSD+
 *
 *	@param	device			device path of C0-microSD+
 *	@return	SignaloidSoCStatus	Status code of Signaloid SoC
 */
SignaloidSoCStatus hostUtilsGetSignaloidSoCStatusRegister(char *  device);

/**
 *	@brief	Read Boot Address register of Signaloid C0-microSD+
 *
 *	@param	device		device path of C0-microSD+
 *	@return	uint32_t	Signaloid C0-microSD+ Boot Address register value
 */
uint32_t hostUtilsGetSignaloidSoCBootAddressRegister(char *  device);

/**
 *	@brief	Write Boot Address register of Signaloid C0-microSD+
 *	@param	device		device path of C0-microSD+
 *	@param	bootAddress		boot address value
 */
void hostUtilsSetSignaloidSoCBootAddressRegister(char *  device, uint32_t bootAddress);
