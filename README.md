# Alien Legacy mass-driver crash fix (ALFIX)

A 35-byte patch for **Alien Legacy** (Sierra/Ybarra Productions, DOS, v1.01) that fixes
the game's best-known crash:

```
DOS/4GW Professional error (2001): exception 00h (divide by zero) at 180:001F75F5
Crash address (unrelocated) = 1:0002E5F5
```

It happens during turn processing (usually right after you speed up time) once a
colony has a **mass driver** aimed at certain destinations. Sierra's own README
attributes it to "mass drivers on high-gravity worlds"; the real cause is below.

**No game files are included here.** You need your own copy of Alien Legacy.
The patcher only modifies an `AL.EXE` you already have, after verifying it.
The game has been out of print for decades (it is on GOG's community wishlist,
not its store); the copy this patch was developed against came from
[My Abandonware](https://www.myabandonware.com/game/alien-legacy-21h).

## How to apply

Two equivalent patchers. Pick whichever is easier for you.

**Inside DOSBox (no other tools needed).** Copy `ALFIX.COM` into the game folder
(next to `AL.EXE`), then from the DOS prompt in that folder run:

```
ALFIX
```

**From a modern OS with Python 3.** Copy `alfix.py` into the game folder and run:

```
python3 alfix.py
```

Either way the patcher checks every byte it is about to change, refuses to touch a
file that doesn't match, writes a backup first (`AL.BAK` for the DOS version,
`AL.EXE.ORIG` for the Python one), and reports "already patched" if run again.
To undo, rename the backup back to `AL.EXE`.

Built and tested against the v1.01 CD executable
(`AL.EXE`, 827,647 bytes, MD5 `fb004009cb1dd703a143a5d9775c5b8c`).
Patched result: MD5 `cc559fb99d9dd01bb5db44efdc669503`.
If your `AL.EXE` differs (another release or a floppy version) the patcher will
say so and change nothing; please open an issue with your file's size and MD5.

## What the bug actually is

The per-turn colony cost routine (LE object 1, function at `0x2E469`) walks each
colony's 16 installation slots (27 bytes each, starting at colony offset `0x16E`).
For every active installation it charges an upkeep cost from `INST.DAT`
(52-byte rows), and, if the slot's *product* field (a dword at slot offset 5) is
4 or greater, a second cost taken from `PROD.DAT` (14-byte rows: ore, energy,
life support, humans, robots, **turns**, qty). That second cost is computed as
`value * 24 / turns`.

`PROD.DAT` has 15 rows, so valid product codes are 4..18. The code checks
`product < 4` and skips, but never checks the upper bound:

```
mov  edx, [eax+0x173]      ; product field
cmp  edx, 4
jl   skip                  ; only a lower bound
lea  eax, [edx-4]
imul edx, eax, 14          ; row offset into PROD.DAT
...
mov  ax, [row+10]          ; "turns"
...
idiv ebp                   ; <-- crashes when "turns" is 0
```

For a **mass driver** (installation kind 51, the last row of `INST.DAT`) the same
field doesn't hold a product at all: it holds the **destination colony index**
(33 = SSZeus, 35 = SSCronus, 38 = SSPoseidon in a typical game). Those values
index far past the 15-row table into unrelated memory. Whether the "turns" word
it lands on is zero depends on what happens to be there, which is why some
mass drivers are fine and others crash the game every time the clock advances.
(A side effect: unpatched, mass drivers are charged a nonsense per-turn cost
read from that unrelated memory.)

## What the patch changes

Four in-place edits, same length as the original code, so nothing else moves.
Offsets are relative to LE object 1; add `0x3E324` for the file offset.

| obj1 offset | original | patched | effect |
|---|---|---|---|
| `0x2E5B7` | `83FA04 7C3F 8D42FC 6BD00E` | `83EA04 83FA0F 733C 6BD20E` | `cmp edx,4 / jl / lea eax,[edx-4] / imul edx,eax,14` becomes `sub edx,4 / cmp edx,15 / jae skip / imul edx,edx,14`: an unsigned compare rejects codes below 4 **and** above 18, so the table can no longer be over-read. This is the actual fix. |
| `0x2E594` | `89442434 8B6C2434` | `89C5 85ED 740D 9090` | Replaces a redundant register spill with `mov ebp,eax / test ebp,ebp / jz skip`: a zero divisor on the first `idiv` contributes nothing instead of trapping. |
| `0x2E5E8` | `89442434 8B6C2434` | `89C5 85ED 740D 9090` | Same guard on the second `idiv` (the crash site). |
| `0x2A89C` | `31FF 668BB83E950000 89D0 C1FA1F F7FF 89C2` | `0FB7B83E950000 92 99 85FF 7501 47 F7FF 89C2` | A second function (installation cost display) has the same unchecked lookup. Rewritten with `movzx`/`xchg`/`cdq` to make room for `test edi,edi / jnz / inc edi`, so a zero divisor is treated as 1. |

For every valid product code the patched code behaves identically to the original.

## Not an emulator problem

This was first suspected to be a DOSBox-X dynamic-core issue on Apple Silicon.
It isn't: the crash reproduces on the interpreter core, DOSBox exits cleanly
(no host crash), and the fault is the game's own `idiv` with a zero divisor.

## Building ALFIX.COM

```
nasm -f bin alfix.asm -o ALFIX.COM
```

`alfix.asm` is plain 8086 code using only DOS INT 21h calls; the resulting
`ALFIX.COM` is under 1 KB. MD5 of the included build: `cdb1e9dc7a5f4d319fb2f3fb6fe1136b`.

## License

The patcher, the assembly source, and this write-up are © 2026 Trevor Johnson and
released under the GNU Affero General Public License v3.0 or later (see `LICENSE`).
Alien Legacy itself is © 1994 Sierra On-Line / Ybarra Productions and is not
included or licensed here.
