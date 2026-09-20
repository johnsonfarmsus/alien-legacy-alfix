; autosave.asm -- in-game autosave for Alien Legacy (DOS v1.01), as a code cave
; SPDX-License-Identifier: AGPL-3.0-or-later
; Copyright (C) 2026 Trevor Johnson
;
; Build:  nasm -f bin autosave.asm -o autosave.bin
; The bytes go at LE object-1 offset CAVE (unused zero padding at the end of the
; code object).  The turn-tick method's epilogue at 0x41523 (pop ebp/edi/esi/ecx/
; ebx/ret, 6 bytes) is replaced by "jmp CAVE" + nop, and the cave ends by
; executing that same epilogue.
;
; Every INTERVAL turns the game's own save routine (0x40DF0) is called with the
; save-name global temporarily set to AUTO1..AUTO<SLOTS>, rotating.  The routine
; needs no arguments and preserves all registers but EAX.
;
; The code is position independent: the game is relocated at load time, so
; absolute addresses are read from two already-relocated instructions:
;   0x41458  mov edx,[turn_counter]   -> imm32 at 0x4145A
;   0x40E07  mov esi,[save_name]      -> imm32 at 0x40E08

        bits 32
        cpu 386

CAVE        equ 0x58D80         ; obj1 offset of this code
SAVE_FN     equ 0x40DF0         ; save routine (obj1 offset)
TURN_IMM    equ 0x4145A         ; relocated address of the turn counter lives here
NAME_IMM    equ 0x40E08         ; relocated address of the save-name string lives here
INTERVAL    equ 200
SLOTS       equ 5

        org CAVE

cave:
        pushfd
        pushad
        cld
        call    .here
.here:  pop     ebx
        sub     ebx, .here              ; ebx = linear base of object 1

        mov     esi, [ebx + TURN_IMM]   ; esi -> turn counter
        mov     eax, [esi]              ; eax = current turn
        cmp     eax, [ebx + last_saved]
        je      .done
        xor     edx, edx
        mov     ecx, INTERVAL
        div     ecx                     ; eax = turn/INTERVAL, edx = remainder
        test    edx, edx
        jnz     .done

        mov     ecx, [esi]
        mov     [ebx + last_saved], ecx ; remember: this turn is handled

        dec     eax                     ; slot = (turn/INTERVAL - 1) mod SLOTS
        xor     edx, edx
        mov     ecx, SLOTS
        div     ecx                     ; edx = slot 0..SLOTS-1

        mov     esi, [ebx + NAME_IMM]   ; esi -> save-name string (game global)
        push    esi
        lea     edi, [ebx + namebuf]
        mov     ecx, 4
        rep     movsd                   ; keep the player's current name (16 bytes)
        pop     edi
        mov     dword [edi], 'AUTO'
        add     dl, '1'
        mov     [edi + 4], dl
        mov     byte [edi + 5], 0       ; "AUTOn"

        call    SAVE_FN                 ; game writes saves\AUTOn.sav

        lea     esi, [ebx + namebuf]
        mov     edi, [ebx + NAME_IMM]
        mov     ecx, 4
        rep     movsd                   ; restore the player's name
.done:
        popad
        popfd
        ; --- displaced epilogue of the turn-tick method ---
        pop     ebp
        pop     edi
        pop     esi
        pop     ecx
        pop     ebx
        ret

        align 4
last_saved: dd 0                        ; turn number of the last autosave
namebuf:    times 16 db 0
cave_end:
