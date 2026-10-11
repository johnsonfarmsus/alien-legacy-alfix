# ALFIX — Alien Legacy mass-driver fixes + autosave

A patch for **Alien Legacy** (Sierra/Ybarra Productions, DOS, v1.01 and v1.10). It does
three things (the autosave is v1.01 only for now):

1. **Fixes the game's best-known crash.** Once a colony has a mass driver aimed at
   certain destinations, the game dies whenever the clock advances:
   ```
   DOS/4GW Professional error (2001): exception 00h (divide by zero) at 180:001F75F5
   Crash address (unrelocated) = 1:0002E5F5
   ```
   Sierra's README blames "mass drivers on high-gravity worlds"; the real cause is below.
2. **Makes mass drivers actually deliver.** Aimed at most destinations they never
   fire: their "Turns left" counter is loaded from garbage (often tens of thousands,
   sometimes 0). Same root cause. Fixed, they launch 25 ore every 6 turns, the
   interval the game's own data files specify.
3. **Adds an in-game autosave.** Every 200 turns the game silently writes
   `AUTO1.SAV` .. `AUTO5.SAV` (rotating, so the five most recent are kept) using its
   own save routine. They appear in the normal Load Game list. Nothing changes in
   the UI and your own save name is untouched.

**No game files are included here.** You need your own copy of Alien Legacy. The
game has been out of print for decades; the copy this patch was developed against
came from [My Abandonware](https://www.myabandonware.com/game/alien-legacy-21h).
The patcher only modifies an `AL.EXE` you already have, after verifying every byte
it is about to change.

## Two editions

| | mass-driver fixes | autosave |
|---|:---:|:---:|
| **Standard** (`ALFIX.COM`, or `python3 alfix.py`) | yes | yes (v1.01 only) |
| **Fixes only** (`python3 alfix.py --no-autosave`) | yes | no |

Running the patcher on an executable that already has the fixes-only edition
upgrades it to standard. On v1.10 both editions currently apply the fixes only;
the patcher says so.

## How to apply

**Inside DOSBox (no other tools needed).** Copy `ALFIX.COM` into the game folder
(next to `AL.EXE`), then from the DOS prompt in that folder run:

```
ALFIX
```

**From a modern OS with Python 3.** Copy `alfix.py` into the game folder and run:

```
python3 alfix.py                 # standard edition
python3 alfix.py --no-autosave   # fixes only
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
6-turn cycle, keeping the untouched saves in `SAVES/BACKUP/`. `--fix-saves` knows
the v1.01 save layout only (it skips files of any other size); on v1.10 use the
offline/online toggle instead.

**Versions.** Both patchers detect the version by checking every patch site, and
work on either supported build:

| build | `AL.EXE` | original MD5 | standard | fixes only |
|---|---|---|---|---|
| v1.01 CD | 827,647 bytes | `fb004009cb1dd703a143a5d9775c5b8c` | `a1998a1e69f2454a5959c2bcea5f9dae` | `9644652f2e9c2b64fb04c5b580f7d010` |
| v1.10 CD (`AL_CD_V1.10`, March 1995) | 936,827 bytes | `e6c78d883eb7972bc4c69098cdeff971` | (fixes only for now) | `4ca4f029fbbe20bfb4ece0f1bccfd3fc` |

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
described above. Offsets are relative to LE object 1; add `0x3E324` for the file offset (v1.01; v1.10 is below).

| obj1 offset | original | patched | effect |
|---|---|---|---|
| `0x2E5B7` | `83FA04 7C3F 8D42FC 6BD00E` | `83EA04 83FA0F 733C 6BD20E` | `cmp edx,4 / jl / lea eax,[edx-4] / imul edx,eax,14` becomes `sub edx,4 / cmp edx,15 / jae skip / imul edx,edx,14`: an unsigned compare rejects codes below 4 **and** above 18, so the table can no longer be over-read. This is the actual fix. |
| `0x2E594` | `89442434 8B6C2434` | `89C5 85ED 740D 9090` | Replaces a redundant register spill with `mov ebp,eax / test ebp,ebp / jz skip`: a zero divisor on the first `idiv` contributes nothing instead of trapping. |
| `0x2E5E8` | `89442434 8B6C2434` | `89C5 85ED 740D 9090` | Same guard on the second `idiv` (the crash site). |
| `0x2A89C` | `31FF 668BB83E950000 89D0 C1FA1F F7FF 89C2` | `0FB7B83E950000 92 99 85FF 7501 47 F7FF 89C2` | A second function (installation cost display) has the same unchecked lookup. Rewritten with `movzx`/`xchg`/`cdq` to make room for `test edi,edi / jnz / inc edi`, so a zero divisor is treated as 1. |

| `0x2E0A1` | `83FE04 7D18 8D04AD00000000 29E8 C1E002 01E8 668B8482D68A0000 EB16 8D46FC 890424 8B3424 C1E003 29F0 668B84423E950000` | `8D46FC 83F80E 7711 89C6 C1E003 29F0 668B84423E950000 EB1A 8D04AD00000000 29E8 C1E002 01E8 668B8482D68A0000 90909090` | The countdown loader's branch selector, rewritten (51 bytes, 4 spare) so that `(product-4)` is compared unsigned against 14: codes 4..18 use `PROD.DAT` as before, everything else (including mass-driver destinations) uses the installation's own `INST.DAT` cycle. Mass drivers now fire every 6 turns. |

For every valid product code the patched code behaves identically to the original.

### v1.10

Sierra's v1.10 release (March 1995) did not fix any of this: its release notes don't
mention mass drivers, and the code still has the same unchecked lookups and unguarded
divisions. The code moved (LE object 1 now starts at file offset `0x45054`) and two
sites are compiled with different registers, so they are re-encoded. Same fixes,
same lengths:

| obj1 offset | v1.01 equivalent | original | patched |
|---|---|---|---|
| `0x1C8F7` | `0x2E5B7` | `83FA04 7C40 8D42FC 6BC00E` | `83EA04 83FA0F 733D 6BC20E` (`imul eax,edx,14`: v1.10 keeps the row offset in `eax`) |
| `0x1C8D4` | `0x2E594` | `89442434 8B6C2434` | `89C5 85ED 740D 9090` (identical) |
| `0x1C929` | `0x2E5E8` | `89442434 8B6C2434` | `89C5 85ED 740D 9090` (identical) |
| `0x18B0A` | `0x2A89C` | `31FF 668BB83E950000 89D0 C1FA1F F7FF` | `0FB7B83E950000 92 99 85FF 7501 47 F7FF` (the first 16 bytes of the v1.01 edit; the instruction after it differs in v1.10 and is left alone) |
| `0x1C3E6` | `0x2E0A1` | `83FD04 7D0D 6BC334 668B8406D68A0000 EB1A 8D45FC 890424 8B2C24 8D04C500000000 29E8 668B84463E950000` | `8D45FC 83F80E 7715 89C5 8D04C500000000 29E8 668B84463E950000 EB0F 6BC334 668B8406D68A0000 90909090` (44 bytes; v1.10 holds the product in `ebp` and the kind in `ebx`) |

The other three divisions in v1.10's cost routine are safe, as in v1.01: one is reached
only for product code 4 exactly, one only for installation kinds 0x16/0x19/0x1A, and
one already checks for zero.

The autosave isn't ported to v1.10 yet: the slack after object 1 isn't empty padding
there, so it needs a different code cave, and the save routine and turn-tick method
still have to be located.

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
`ALFIX.COM` is about 2 KB. MD5 of the included build: `6c887208c5898830a3f3529cdc00ee7a`.
The autosave routine is built separately with `nasm -f bin autosave.asm -o autosave.bin`;
its bytes are embedded in both patchers.

## Campaign guide

`guide.py` builds a browsable campaign guide from your own game files: all 60
technologies with their effect, the seven science levels each needs, research cost,
the prerequisites the game enforces, the factory or power-plant level each upgrade
unlocks, and the in-game lab reports and encyclopedia text; the technologies the story
depends on; and when each of the 27 cinematics plays. Like the patcher, it ships no
game content; the page is made locally.

```
python3 guide.py                          # from the game folder; writes guide.html
python3 guide.py GAME_DIR OUT.html
```

The story and cinematic sections are written from an analysis of the game's event
scripts. Each `RESOURCE.0xx` file is a small compiled module (32-byte `MZ` header, then
32-bit code) that the game calls with a table of about 150 callback functions; one of
them schedules `?:cinema.NNN`. Films 4, 6, 10, 21 and 27 aren't played by any event.

`TECH.DAT` and `TECHTXT.DAT` are byte-identical in v1.01 and v1.10, so the page is the
same for both.

Formats, as decoded:

- `TECHTXT.DAT` (and the other `*TXT.DAT` files): `u16` string count, `u16` 4, then
  count+1 `u32` offsets (the last marks the end), then NUL-terminated strings.
- `TECH.DAT`: 96 records of 25 bytes, 60 in use. Byte 0 is the kind (2 upgrade,
  4 component or theory, 3 story device, 1 the missile technology); bytes 2–8 are the
  science levels; bytes 9–11 are up to three prerequisite record numbers (`0x63` = none);
  byte 12 is the research cost; bytes 13–24 are six `u16` indexes into `TECHTXT.DAT`:
  effect line, "still needed" message, progress report, completion report, first
  encyclopedia entry, encyclopedia entry.

Two things are inferred rather than stored. Technology names aren't kept as text in
the game files, so each comes from the opening of its encyclopedia entry. The science
order (Astronomy, Geology, Electronics, Chemistry, Biology, Mathematics, Physics) is
read off which level each technology leans on: the plague and the mushroom synthesizer
on Biology, the Translation Constant on Mathematics, the black-hole and orbital devices
on Astronomy.

## License

The patchers, the assembly sources, and this write-up are © 2026 Trevor Johnson and
released under the GNU Affero General Public License v3.0 or later (see `LICENSE`).
Alien Legacy itself is © 1994 Sierra On-Line / Ybarra Productions and is not
included or licensed here.
