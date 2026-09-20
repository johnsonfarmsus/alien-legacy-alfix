# Alien Legacy fixes + autosave (ALFIX)

A patch for **Alien Legacy** (Sierra/Ybarra Productions, DOS, v1.01) that fixes two
bugs in the game's mass drivers and adds an in-game **autosave**. The first bug is the
game's best-known crash:

```
DOS/4GW Professional error (2001): exception 00h (divide by zero) at 180:001F75F5
Crash address (unrelocated) = 1:0002E5F5
```

It happens during turn processing (usually right after you speed up time) once a
colony has a **mass driver** aimed at certain destinations. Sierra's own README
attributes it to "mass drivers on high-gravity worlds"; the real cause is below.

**Autosave.** Every 200 turns the game silently writes `AUTO1.SAV` .. `AUTO5.SAV`
(rotating, so the five most recent are kept), using the game's own save routine.
They show up in the normal Load Game list like any other save. Nothing changes in
the UI and your own save name is untouched. It can be left out with
`python3 alfix.py --no-autosave`.

**No game files are included here.** You need your own copy of Alien Legacy.
The patcher only modifies an `AL.EXE` you already have, after verifying it.

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

**Existing saves.** A mass driver that already has a garbage countdown keeps
counting from it even after the executable is patched (it only reloads on its
next launch). Either take the driver offline and back online in-game, or run

```
python3 alfix.py --fix-saves            # (from the game folder; or pass the SAVES dir)
```

which resets every online mass driver with a garbage countdown to the correct
6-turn cycle, keeping the untouched saves in `SAVES/BACKUP/`.

Built and tested against the v1.01 CD executable
(`AL.EXE`, 827,647 bytes, MD5 `fb004009cb1dd703a143a5d9775c5b8c`).
Patched result: MD5 `a1998a1e69f2454a5959c2bcea5f9dae`
(`9644652f2e9c2b64fb04c5b580f7d010` with `--no-autosave`). Running the patcher
on an executable that already has the bug fixes adds the autosave to it.
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

The same mistake appears in the routine that (re)loads an installation's
countdown (`0x2E070`). Installations with no product take their cycle length from
their own `INST.DAT` row (the word at +0x32); anything with a product code of 4 or
more takes it from the `PROD.DAT` row. A mass driver's destination number sends it
down the second path, so its countdown is loaded from memory past the table:
18,998 turns for one destination, 0 for another. The correct value is right there
in `INST.DAT`: the mass driver's row says **6**. The game's delivery code itself is
fine (it has an explicit mass-driver branch that ships 25 ore to the destination
colony when the countdown expires); it just never gets a sane countdown. Two
other routines on this path (`0x3182C`, `0x327CA`) *do* bounds-check the product
code, so the original programmers guarded most of these lookups and missed two.

## What the patch changes

Bug fixes: five in-place edits, same length as the original code, so nothing else
moves. Autosave: the 6-byte hook, the 152-byte cave and the 4-byte header edit
described above. Offsets are relative to LE object 1; add `0x3E324` for the file offset.

| obj1 offset | original | patched | effect |
|---|---|---|---|
| `0x2E5B7` | `83FA04 7C3F 8D42FC 6BD00E` | `83EA04 83FA0F 733C 6BD20E` | `cmp edx,4 / jl / lea eax,[edx-4] / imul edx,eax,14` becomes `sub edx,4 / cmp edx,15 / jae skip / imul edx,edx,14`: an unsigned compare rejects codes below 4 **and** above 18, so the table can no longer be over-read. This is the actual fix. |
| `0x2E594` | `89442434 8B6C2434` | `89C5 85ED 740D 9090` | Replaces a redundant register spill with `mov ebp,eax / test ebp,ebp / jz skip`: a zero divisor on the first `idiv` contributes nothing instead of trapping. |
| `0x2E5E8` | `89442434 8B6C2434` | `89C5 85ED 740D 9090` | Same guard on the second `idiv` (the crash site). |
| `0x2A89C` | `31FF 668BB83E950000 89D0 C1FA1F F7FF 89C2` | `0FB7B83E950000 92 99 85FF 7501 47 F7FF 89C2` | A second function (installation cost display) has the same unchecked lookup. Rewritten with `movzx`/`xchg`/`cdq` to make room for `test edi,edi / jnz / inc edi`, so a zero divisor is treated as 1. |

| `0x2E0A1` | `83FE04 7D18 8D04AD00000000 29E8 C1E002 01E8 668B8482D68A0000 EB16 8D46FC 890424 8B3424 C1E003 29F0 668B84423E950000` | `8D46FC 83F80E 7711 89C6 C1E003 29F0 668B84423E950000 EB1A 8D04AD00000000 29E8 C1E002 01E8 668B8482D68A0000 90909090` | The countdown loader's branch selector, rewritten (51 bytes, 4 spare) so that `(product-4)` is compared unsigned against 14: codes 4..18 use `PROD.DAT` as before, everything else (including mass-driver destinations) uses the installation's own `INST.DAT` cycle. Mass drivers now fire every 6 turns. |

For every valid product code the patched code behaves identically to the original.

## How the autosave works

The game's turn-tick method (`0x41448`, slot `+0x18` of its file-manager object)
ends in a 6-byte epilogue at `0x41523`. That epilogue is replaced by a jump into a
152-byte routine placed in the unused zero padding at the end of the code object
(`0x58D80`; see `autosave.asm`). The routine reads the turn counter; if it is a
multiple of 200 and hasn't been handled yet, it sets the game's save-name global
to `AUTOn` (n = `(turn/200 - 1) mod 5 + 1`), calls the game's own save routine
(`0x40DF0`, which takes no arguments and writes the state plus a copy of
`campaign.tmp`), restores the player's save name, and then runs the displaced
epilogue. It costs a few instructions on ticks that aren't a 200th turn.

The game is relocated at load time, so the routine is position-independent: it
finds its own address with `call/pop` and takes the addresses of the turn counter
and the name string from two existing, already-relocated instructions
(`0x41458` and `0x40E07`). One 4-byte edit to the LE header raises object 1's
declared size from `0x58D68` to `0x59000` so the cave's page is fully mapped.

Tested by driving the game under DOSBox from a turn-4487 save: `AUTO3` was written
at turn 4600, `AUTO4` at 4800, `AUTO5` at 5000 and `AUTO1` at 5200, each a normal
213,605-byte save that loads from the Load Game screen.

## Not an emulator problem

This was first suspected to be a DOSBox-X dynamic-core issue on Apple Silicon.
It isn't: the crash reproduces on the interpreter core, DOSBox exits cleanly
(no host crash), and the fault is the game's own `idiv` with a zero divisor.

## Building ALFIX.COM

```
nasm -f bin alfix.asm -o ALFIX.COM
```

`alfix.asm` is plain 8086 code using only DOS INT 21h calls; the resulting
`ALFIX.COM` is about 1.6 KB. MD5 of the included build: `31725fc5a11eae64bd70ea18170e4fe2`.
The autosave routine is built separately with `nasm -f bin autosave.asm -o autosave.bin`;
its bytes are embedded in both patchers.

## License

The patchers, the assembly sources, and this write-up are © 2026 Trevor Johnson and
released under the GNU Affero General Public License v3.0 or later (see `LICENSE`).
Alien Legacy itself is © 1994 Sierra On-Line / Ybarra Productions and is not
included or licensed here.
