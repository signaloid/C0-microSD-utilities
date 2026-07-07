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

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <stdint.h>
#include <fcntl.h>
#include <stdbool.h>
#include <errno.h>

#include "C0microSDPlus/Constants.h"
#include "C0microSDPlus/HostUtils.h"


ssize_t
hostUtilsReadFromC0microSDPlus(char *  device, void *  destBuffer, size_t bufferSize, off_t offset)
{
	int		fd;
	ssize_t		result;
	off_t		seekOffset;

	/*
	 *	Opening and closing the device for each transaction is needed to force flush
	 */
	fd = open(device, O_RDONLY | O_SYNC | O_DSYNC);
	
	if (fd == -1)
	{
		perror("Error opening device");
		return -1;
	}

	seekOffset = lseek(fd, offset, SEEK_SET);
	if (seekOffset == (off_t)-1)
	{
		perror("Error seeking to target offset");
		close(fd);
		return -1;
	}

	result = read(fd, destBuffer, bufferSize);
	if (result != bufferSize)
	{
		perror("Error reading data from the device");
	}

	close(fd);
	return result;
}

ssize_t
hostUtilsWriteToC0microSDPlus(char *  device, void *  sourceBuffer, size_t bufferSize, off_t offset)
{
	int		fd;
	ssize_t		result;
	off_t		seekOffset;

	/*
	 *	Opening and closing the device for each transaction is needed to force flush
	 */
	fd = open(device, O_WRONLY | O_SYNC | O_DSYNC);
	
	if (fd == -1)
	{
		perror("Error opening device");
		return -1;
	}

	seekOffset = lseek(fd, offset, SEEK_SET);
	if (seekOffset == (off_t)-1)
	{
		perror("Error seeking to target offset");
		close(fd);
		return -1;
	}

	result = write(fd, sourceBuffer, bufferSize);
	if (result != bufferSize)
	{
		perror("Error writing data to the device");
	}
	
	close(fd);
	return result;
}

void
hostUtilsReadSignaloidSoCMMIOBuffer(char *  device, void *  destBuffer)
{
	ssize_t		res;
	res = hostUtilsReadFromC0microSDPlus(device, destBuffer, kSignaloidSoCConstantsMMIOBufferSizeBytes, kSignaloidSoCConstantsMMIOBufferOffset);
	if (res != kSignaloidSoCConstantsMMIOBufferSizeBytes)
	{	
		exit(EXIT_FAILURE);
	}
}

void
hostUtilsWriteSignaloidSoCMMIOBuffer(char *  device, void *  sourceBuffer)
{
	ssize_t		res;
	res = hostUtilsWriteToC0microSDPlus(device, sourceBuffer, kSignaloidSoCConstantsMMIOBufferSizeBytes, kSignaloidSoCConstantsMMIOBufferOffset);
	if (res != kSignaloidSoCConstantsMMIOBufferSizeBytes)
	{	
		exit(EXIT_FAILURE);
	}
}

uint32_t
hostUtilsGetSignaloidSoCConfigRegister(char *  device)
{
	uint32_t	socConfig;
	ssize_t		res;
	res = hostUtilsReadFromC0microSDPlus(device, (void *) &socConfig, sizeof(uint32_t), kSignaloidSoCConstantsConfigOffset);
	if (res != sizeof(uint32_t))
	{	
		exit(EXIT_FAILURE);
	}
	return socConfig;
}

void
hostUtilsSetSignaloidSoCConfigRegister(char *  device, uint32_t config)
{
	ssize_t res;
	res = hostUtilsWriteToC0microSDPlus(device, (void *) &config, sizeof(uint32_t), kSignaloidSoCConstantsConfigOffset);
	if (res != sizeof(uint32_t))
	{	
		exit(EXIT_FAILURE);
	}
}

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
	bool *  debugPin2)
{
	uint32_t regVal = hostUtilsGetSignaloidSoCConfigRegister(device);
	*rstn= (bool)((regVal >> 0) & 0x1);
	*unlockBitstreamSection= (bool)((regVal >> 1) & 0x1);
	*swLedEnable= (bool)((regVal >> 2) & 0x1);
	*swLed= (bool)((regVal >> 3) & 0x1);
	*redLed= (bool)((regVal >> 4) & 0x1);
	*greenLed= (bool)((regVal >> 5) & 0x1);
	*blueLed= (bool)((regVal >> 6) & 0x1);
	*debugPin0= (bool)((regVal >> 7) & 0x1);
	*debugPin1= (bool)((regVal >> 8) & 0x1);
	*debugPin2= (bool)((regVal >> 9) & 0x1);
}

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
	bool debugPin2)
{
	uint32_t regVal = 0;
	regVal |= ((uint32_t)rstn & 0x1) << 0;
	regVal |= ((uint32_t)unlockBitstreamSection & 0x1) << 1;
	regVal |= ((uint32_t)swLedEnable & 0x1) << 2;
	regVal |= ((uint32_t)swLed & 0x1) << 3;
	regVal |= ((uint32_t)redLed & 0x1) << 4;
	regVal |= ((uint32_t)greenLed & 0x1) << 5;
	regVal |= ((uint32_t)blueLed & 0x1) << 6;
	regVal |= ((uint32_t)debugPin0 & 0x1) << 7;
	regVal |= ((uint32_t)debugPin1 & 0x1) << 8;
	regVal |= ((uint32_t)debugPin2 & 0x1) << 9;

	hostUtilsSetSignaloidSoCConfigRegister(device, regVal);
}

void
hostUtilsSetSignaloidSoCCommandRegister(char *  device, uint32_t command)
{
	ssize_t res;
	res = hostUtilsWriteToC0microSDPlus(device, (void *) &command, sizeof(uint32_t), kSignaloidSoCConstantsCommandOffset);
	if (res != sizeof(uint32_t))
	{	
		exit(EXIT_FAILURE);
	}
}

SignaloidSoCStatus
hostUtilsGetSignaloidSoCStatusRegister(char *  device)
{
	SignaloidSoCStatus	status;
	ssize_t			res;
	res = hostUtilsReadFromC0microSDPlus(device, (void *) &status, sizeof(uint32_t), kSignaloidSoCConstantsStatusOffset);
	if (res != sizeof(uint32_t))
	{	
		exit(EXIT_FAILURE);
	}
	return status;
}

uint32_t
hostUtilsGetSignaloidSoCBootAddressRegister(char *  device)
{
	uint32_t	socBootAddress;
	ssize_t		res;
	res = hostUtilsReadFromC0microSDPlus(device, (void *) &socBootAddress, sizeof(uint32_t), kSignaloidSoCConstantsBootAddressOffset);
	if (res != sizeof(uint32_t))
	{	
		exit(EXIT_FAILURE);
	}
	return socBootAddress;
}

void
hostUtilsSetSignaloidSoCBootAddressRegister(char *  device, uint32_t bootAddress)
{
	ssize_t res;
	res = hostUtilsWriteToC0microSDPlus(device, (void *) &bootAddress, sizeof(uint32_t), kSignaloidSoCConstantsBootAddressOffset);
	if (res != sizeof(uint32_t))
	{	
		exit(EXIT_FAILURE);
	}
}
