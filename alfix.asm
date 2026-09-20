; ALFIX.COM -- fixes the mass-driver divide-by-zero crash in Alien Legacy (DOS v1.01)
; Build:  nasm -f bin alfix.asm -o ALFIX.COM
; Run inside DOSBox from the game folder:  ALFIX
;
; SPDX-License-Identifier: AGPL-3.0-or-later
; Copyright (C) 2026 Trevor Johnson -- GNU AGPL v3 or later, see LICENSE. No warranty.
;
; Verifies every patch site before writing, backs up AL.EXE to AL.BAK,
; and reports "already patched" if run twice.  Pure DOS INT 21h, no dependencies.

        org 100h
        cpu 8086

PAGES   equ 3E324h                      ; file offset of LE object 1, page 0

start:
        mov     dx, msg_banner
        call    print

        ; ---- open AL.EXE read/write ----
        mov     ax, 3D02h
        mov     dx, fn_exe
        int     21h
        jc      .no_exe
        mov     [h_exe], ax

        ; ---- pass 1: verify all sites ----
        mov     si, patch_table
.verify:
        cmp     word [si], 0
        je      .verified
        call    seek_site
        mov     ah, 3Fh                 ; read
        mov     bx, [h_exe]
        mov     cx, [si+4]              ; length
        mov     dx, buf
        int     21h
        jc      .io_err
        cmp     ax, [si+4]
        jne     .io_err
        ; compare with NEW bytes?
        mov     cx, [si+4]
        mov     di, [si+8]
        call    cmp_buf
        jne     .not_new
        mov     byte [si+10], 1         ; flag: already patched
        inc     byte [n_already]
        jmp     .next
.not_new:
        mov     cx, [si+4]
        mov     di, [si+6]
        call    cmp_buf
        jne     .mismatch
.next:
        add     si, 11
        jmp     .verify

.verified:
        mov     al, [n_already]
        cmp     al, NPATCH
        je      .already_all

        ; ---- backup AL.EXE -> AL.BAK (unless it exists) ----
        mov     ax, 3D00h
        mov     dx, fn_bak
        int     21h
        jnc     .have_bak               ; exists: don't overwrite
        call    make_backup
        jc      .io_err
        mov     dx, msg_backup
        call    print
        jmp     .write
.have_bak:
        mov     bx, ax
        mov     ah, 3Eh
        int     21h

        ; ---- pass 2: write ----
.write:
        mov     si, patch_table
.wloop:
        cmp     word [si], 0
        je      .done
        cmp     byte [si+10], 1
        je      .wnext
        call    seek_site
        mov     ah, 40h
        mov     bx, [h_exe]
        mov     cx, [si+4]
        mov     dx, [si+8]
        int     21h
        jc      .io_err
.wnext:
        add     si, 11
        jmp     .wloop

.done:
        call    close_exe
        mov     dx, msg_done
        call    print
        mov     ax, 4C00h
        int     21h

.already_all:
        call    close_exe
        mov     dx, msg_already
        call    print
        mov     ax, 4C00h
        int     21h

.mismatch:
        call    close_exe
        mov     dx, msg_mismatch
        call    print
        mov     ax, 4C02h
        int     21h

.io_err:
        call    close_exe
        mov     dx, msg_ioerr
        call    print
        mov     ax, 4C03h
        int     21h

.no_exe:
        mov     dx, msg_noexe
        call    print
        mov     ax, 4C01h
        int     21h

; ---------------------------------------------------------------- helpers
; seek_site: SI -> patch entry; seeks h_exe to its file offset
seek_site:
        mov     bx, [h_exe]
        mov     dx, [si]                ; low word
        mov     cx, [si+2]              ; high word
        mov     ax, 4200h
        int     21h
        ret

; cmp_buf: compare CX bytes at buf with DS:DI; ZF set if equal
cmp_buf:
        push    si
        mov     si, buf
        push    es
        push    ds
        pop     es
        xchg    si, di                  ; DS:SI = expected, ES:DI = buf
        repe    cmpsb
        pop     es
        pop     si
        ret

close_exe:
        mov     bx, [h_exe]
        cmp     bx, 0
        je      .r
        mov     ah, 3Eh
        int     21h
        mov     word [h_exe], 0
.r:     ret

; make_backup: copy AL.EXE -> AL.BAK using h_exe (rewound). CF on error.
make_backup:
        mov     ah, 3Ch                 ; create
        xor     cx, cx
        mov     dx, fn_bak
        int     21h
        jc      .err
        mov     [h_bak], ax
        mov     bx, [h_exe]
        xor     cx, cx
        xor     dx, dx
        mov     ax, 4200h               ; rewind source
        int     21h
.loop:
        mov     ah, 3Fh
        mov     bx, [h_exe]
        mov     cx, 8000h
        mov     dx, copybuf
        int     21h
        jc      .err
        or      ax, ax
        jz      .fin
        mov     cx, ax
        mov     ah, 40h
        mov     bx, [h_bak]
        mov     dx, copybuf
        int     21h
        jc      .err
        jmp     .loop
.fin:
        mov     bx, [h_bak]
        mov     ah, 3Eh
        int     21h
        clc
        ret
.err:
        stc
        ret

print:
        mov     ah, 09h
        int     21h
        ret

; ---------------------------------------------------------------- data
fn_exe  db 'AL.EXE',0
fn_bak  db 'AL.BAK',0
h_exe   dw 0
h_bak   dw 0
n_already db 0

msg_banner  db 'ALFIX - Alien Legacy mass-driver divide-by-zero fix',13,10,'$'
msg_backup  db 'Backup written: AL.BAK',13,10,'$'
msg_done    db 'AL.EXE patched. You are good to go.',13,10,'$'
msg_already db 'AL.EXE is already patched. Nothing to do.',13,10,'$'
msg_mismatch db 'This AL.EXE does not match the expected v1.01 build.',13,10
             db 'Nothing was changed.',13,10,'$'
msg_ioerr   db 'File error. Nothing (or only part) was changed - restore AL.BAK if present.',13,10,'$'
msg_noexe   db 'AL.EXE not found. Run ALFIX from the Alien Legacy folder.',13,10,'$'

NPATCH  equ 4
; entry: dd file_offset ; dw len ; dw old_ptr ; dw new_ptr ; db already_flag
patch_table:
        dd PAGES+2E5B7h
        dw 11, p1_old, p1_new
        db 0
        dd PAGES+2E594h
        dw 8, p2_old, p2_new
        db 0
        dd PAGES+2E5E8h
        dw 8, p2_old, p2_new
        db 0
        dd PAGES+2A89Ch
        dw 18, p4_old, p4_new
        db 0
        dw 0                            ; terminator

p1_old  db 83h,0FAh,04h, 7Ch,3Fh, 8Dh,42h,0FCh, 6Bh,0D0h,0Eh
p1_new  db 83h,0EAh,04h, 83h,0FAh,0Fh, 73h,3Ch, 6Bh,0D2h,0Eh
p2_old  db 89h,44h,24h,34h, 8Bh,6Ch,24h,34h
p2_new  db 89h,0C5h, 85h,0EDh, 74h,0Dh, 90h,90h
p4_old  db 31h,0FFh, 66h,8Bh,0B8h,3Eh,95h,00h,00h, 89h,0D0h, 0C1h,0FAh,1Fh, 0F7h,0FFh, 89h,0C2h
p4_new  db 0Fh,0B7h,0B8h,3Eh,95h,00h,00h, 92h, 99h, 85h,0FFh, 75h,01h, 47h, 0F7h,0FFh, 89h,0C2h

buf     times 32 db 0
copybuf:                                ; 32K copy buffer lives past the end of the image
