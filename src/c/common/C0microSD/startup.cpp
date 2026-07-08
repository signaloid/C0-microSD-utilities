/*
   Simple C++ startup routine to setup CRT
   SPDX-License-Identifier: Unlicense

   https://five-embeddev.com/

*/

#include <algorithm>
#include <cstdint>

/*
 *	Generic C function pointer.
 */
typedef void (*function_t)();

extern "C" function_t __init_array_start[];
extern "C" function_t __init_array_end[];

/*
 *	Define the symbols with "C" naming as they are used by the assembler
 */
extern "C" void _start(void);

/*
 *	Define the following to avoid compilation issues
 */
extern "C" { void* __dso_handle __attribute__ ((__weak__)); }

/*
 *	Standard entry point, no arguments.
 */
extern int main(void);

/*
 *	At this point we have a stack and global poiner, but no access to global variables.
 */
void
_start(void)
{
	/*
	 *	Call constructors
	 */
	std::for_each( __init_array_start,
			__init_array_end,
			[](const function_t pf) {pf();});
}

