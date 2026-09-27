# A53 focused keyboard reader candidate

The first A53 keyboard-method trial reached an authenticated mainline boot but
the embedded `keyboard-observe` refused `--diagnose` before any key prompt.
The separately validated focused reader already supports that mode and has
been exercised on the PDA in a previous keyboard experiment. This candidate
replaces **only** that reader in the previously validated A53 service RAM
image. It retains the kernel, DTB, init script, console map, authentication,
logger and recovery path.

Run `build-candidate.py` with the exact private A53 candidate, the fetched
Buildbox focused-reader package identified by SHA-256
`477db0d31c2d2a5d9830022e7dc63288a4e8cd48717aa3cee9b25d4043cc1927`,
and `artifacts/a53-focused-keyboard` as the output root. The script validates
every parent candidate member and package inventory, the static AArch64 reader,
the single initramfs-member delta, LK container and full boot2 padding. The
result remains private and is not yet an admitted boot2 image.

For a later device trial, the hypothesis is that the exact A53 image will pass
the same CPU0–7, console, USB and complete-log checks while the focused reader
actually enters its two physical-key windows. The unique observation is a
verified changed mainline boot, the `--diagnose` header and one owner key
challenge with raw evdev and console bytes; this separates a method failure
from a keyboard translation failure. A reader refusal or console-exclusion
failure stops before input; missing USB or boot identity is inconclusive;
successful capture still needs repeat-aware analysis, complete log preservation
and changed-boot Gemian return before the method can be accepted. A new guarded
installer/session binding and finite budget are required before deployment.
No unchanged-image repeat or ten-cold-boot cycle is authorized by this
offline candidate.

## Offline composition result

The recipe at clean pushed commit `0f24d026` produced a private candidate with
boot SHA-256 `ea8adc12…18adac2` and exact 16 MiB boot2 SHA-256
`34b56a58…780020`. The [sanitized receipt](results/candidate.json) pins the
complete identities. An independent archive comparison found 47 matching
member names with only `bin/keyboard-observe` changed; that member retained
its mode. The kernel, Gemini DTB and config are byte-identical to the A53
parent, the LK container validated, and the full-partition padding and file
inventory rechecked. No device write, boot or keyboard action occurred.

The next implementation step is an exact guarded installer and session binding
for this new image. It must preserve the fresh Gemian predecessor, authenticated
USB observation, finite focused capture, complete log and reviewed return
requirements above. The private candidate is **not** selected for boot2 yet.
