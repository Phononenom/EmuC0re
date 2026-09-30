#!/usr/bin/env python3
"""Writes the Homebrew Browser manifest for this payload.

    mkmanifest.py <title> <payload.bin> <payload.elf> <out>

The browser installs each emulator as /savedata0/homebrew/<title>/ with a
payload.bin (the blob, verbatim) and this manifest, which is plain key=value
lines:

    title=<title>
    reserve=0x...   bytes of JIT shared memory the launch must reserve
    data_off=0x0    this blob is code + embedded .data image, copied whole
    data_size=0x0

reserve is EXACTLY the reservation mklua.py computes for @@JIT_SIZE@@ --
__data_start page-aligned up, i.e. code plus .data's initial image -- then
aligned up to whole 256KB chunks, the granularity the browser remaps JIT
memory at. .bss is deliberately NOT in the reservation: _start maps it
anonymously itself (boot.inc), so charging it against the JIT pool would
only shrink the number of payloads a session can run.
"""
import os
import subprocess
import sys

PAGE  = 0x4000
CHUNK = 0x40000

# The whole JIT region the browser can offer. A payload needing more cannot
# be launched by it at all, so exceeding it is a build failure, not a
# warning -- finding out on the console costs a game relaunch.
POOL_MAX = 0xC0000


def linker_syms(elf, names):
    """Same readelf lookup mklua.py uses, so both tools agree by
       construction."""
    out = subprocess.run(["readelf", "-sW", elf], capture_output=True, text=True).stdout
    syms = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 8 and parts[7] in names:
            syms[parts[7]] = int(parts[1], 16)
    missing = [n for n in names if n not in syms]
    if missing:
        raise SystemExit("mkmanifest: missing linker symbols: %s"
                         % ", ".join(missing))
    return syms


def main():
    if len(sys.argv) != 5:
        raise SystemExit(__doc__)
    title, binary, elf, out = sys.argv[1:5]

    blob = open(binary, "rb").read()
    data_start = linker_syms(elf, ["__data_start"])["__data_start"]

    jit_size = (data_start + PAGE - 1) & ~(PAGE - 1)
    reserve  = (jit_size + CHUNK - 1) & ~(CHUNK - 1)

    # The blob is copied into the JIT mappings whole, so it must fit the
    # reservation. mklua.py already enforces the tighter
    # blob <= __data_start bound at pack time; this catches a manifest made
    # from a stale bin/elf pair rather than re-litigating that check.
    if len(blob) > reserve:
        raise SystemExit(
            "mkmanifest: blob (%d B) exceeds its 0x%X reserve -- the browser "
            "would truncate the image loading it" % (len(blob), reserve))
    if reserve > POOL_MAX:
        raise SystemExit(
            "mkmanifest: reserve 0x%X exceeds the browser's 0x%X JIT region"
            % (reserve, POOL_MAX))

    text = ("title=%s\n"
            "reserve=0x%X\n"
            "data_off=0x0\n"
            "data_size=0x0\n" % (title, reserve))

    d = os.path.dirname(out)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)

    print("mkmanifest: %s" % out)
    print("  blob      %8d B  (code + .data init)" % len(blob))
    print("  reserve   0x%X  (%d x 256KB chunks)"
          % (reserve, reserve // CHUNK))


if __name__ == "__main__":
    main()
