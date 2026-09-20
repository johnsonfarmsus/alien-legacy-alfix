#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Trevor Johnson
"""
alfix.py -- fixes the mass-driver divide-by-zero crash in Alien Legacy (DOS, v1.01)

    DOS/4GW Professional error (2001): exception 00h (divide by zero) at 180:001F75F5

Usage:  put this file next to AL.EXE and run:   python3 alfix.py
        (or:  python3 alfix.py /path/to/AL.EXE)

The script verifies the original bytes before writing anything, keeps a backup
as AL.EXE.ORIG, and does nothing if the file is already patched.  No game
files are distributed with this script; you need your own copy of the game.

Root cause and byte-level details: see README.md

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU Affero General Public License as published by the Free
Software Foundation, either version 3 of the License, or (at your option) any
later version. It is distributed WITHOUT ANY WARRANTY; see the LICENSE file.
"""
import hashlib, os, shutil, sys

ORIG_MD5 = "fb004009cb1dd703a143a5d9775c5b8c"
PATCHED_MD5 = "cc559fb99d9dd01bb5db44efdc669503"
PAGES = 0x3E324  # file offset of LE object 1, page 0 (verified against the fixup table)

# (object-1 offset, original bytes, patched bytes, description)
PATCHES = [
    (0x2E5B7, "83fa047c3f8d42fc6bd00e", "83ea0483fa0f733c6bd20e",
     "bounds-check the PROD.DAT row index (product codes 4..18 only)"),
    (0x2E594, "894424348b6c2434", "89c585ed740d9090",
     "zero-divisor guard, 1st idiv in per-turn cost loop"),
    (0x2E5E8, "894424348b6c2434", "89c585ed740d9090",
     "zero-divisor guard, 2nd idiv in per-turn cost loop (the crash site)"),
    (0x2A89C, "31ff668bb83e95000089d0c1fa1ff7ff89c2", "0fb7b83e950000929985ff750147f7ff89c2",
     "zero-divisor guard in the installation cost display routine"),
]


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else None
    if path is None:
        here = os.path.dirname(os.path.abspath(__file__))
        for name in ("AL.EXE", "al.exe", "Al.exe"):
            if os.path.exists(os.path.join(here, name)):
                path = os.path.join(here, name)
                break
    if path is None or not os.path.exists(path):
        sys.exit("AL.EXE not found. Put alfix.py in the Alien Legacy folder, or pass the path to AL.EXE.")

    data = bytearray(open(path, "rb").read())
    md5 = hashlib.md5(data).hexdigest()
    if md5 == PATCHED_MD5:
        print(f"{os.path.basename(path)} is already patched. Nothing to do.")
        return
    if md5 != ORIG_MD5:
        print(f"WARNING: {os.path.basename(path)} has an unexpected MD5 ({md5}).")
        print("This patcher was built against the v1.01 CD executable (md5 " + ORIG_MD5 + ").")
        print("Checking whether the patch sites still match...")

    # verify every site before touching anything
    for off, old, new, desc in PATCHES:
        cur = bytes(data[PAGES + off: PAGES + off + len(old) // 2]).hex()
        if cur == new:
            print(f"  already patched: {desc}")
        elif cur != old:
            sys.exit(f"ABORT: bytes at object offset {off:#x} don't match this executable "
                     f"(found {cur}, expected {old}). Nothing was changed.")

    backup = path + ".ORIG" if not path.lower().endswith(".orig") else path + ".bak"
    if not os.path.exists(backup):
        shutil.copy2(path, backup)
        print(f"backup written: {os.path.basename(backup)}")

    for off, old, new, desc in PATCHES:
        data[PAGES + off: PAGES + off + len(new) // 2] = bytes.fromhex(new)
        print(f"  patched: {desc}")
    open(path, "wb").write(data)
    print(f"done. {os.path.basename(path)} md5 is now {hashlib.md5(data).hexdigest()}")
    if hashlib.md5(data).hexdigest() != PATCHED_MD5:
        print("(note: not byte-identical to the reference patched build, but all four sites are patched)")


if __name__ == "__main__":
    main()
