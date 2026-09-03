/*
 * Storage-blind PID 1 for the first offline Vero boot component.
 *
 * It deliberately has no C runtime and makes only two Linux syscalls:
 * write(1, marker, marker_length) and nanosleep(&delay, NULL).
 */

    .section .rodata
    .balign 8
marker:
    .ascii "STREMIO_VERO_SAFE_PROBE: kernel, DTB and initramfs reached; storage untouched.\n"
    .set marker_length, . - marker

    .balign 8
delay:
    .xword 60
    .xword 0

    .section .text
    .balign 4
    .global _start
    .type _start, %function
_start:
    mov x0, #1
    adrp x1, marker
    add x1, x1, :lo12:marker
    mov x2, #marker_length
    mov x8, #64
    svc #0

1:
    adrp x0, delay
    add x0, x0, :lo12:delay
    mov x1, #0
    mov x8, #101
    svc #0
    b 1b
    .size _start, . - _start

    .section .note.GNU-stack,"",%progbits
