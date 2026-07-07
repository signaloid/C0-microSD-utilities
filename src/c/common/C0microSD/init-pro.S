.globl	_init
.globl	__errno
.align	4

.section .text.unlikely

_init:
.option push
.option norelax
	li	sp, 0x0020000	# 128K
	la	gp, __global_pointer$
.option pop
	# Clear the bss segment
	la      a0, _edata
	la      a2, _end
	sub     a2, a2, a0
	li      a1, 0
	call    memset
	# Push a0 and a1 in the stack to save argc and argv of main
	addi    sp,sp,-8
	sw      a0,4(sp)
	sw      a1,0(sp)

	# Call initialization function
	call	_start

	# Pop a0 and a1 in the stack to save argc and argv of main
	lw      a0,4(sp)
	lw      a1,0(sp)
	addi    sp,sp,8

	call	main
	call	exit

errnoValue:	.word 0

__errno:
	la	a0, errnoValue
	ret

