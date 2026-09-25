# Keyboard method for the A53 cold-boot gate

Status: the existing A53 image contains a usable keyboard observer; no new
boot image is needed for a keyboard-method trial. Repeat-aware classification
passes offline checks, but the method is not yet admitted on this image or
frozen for the ten-cold-boot series.

The [first board session](results/a53-service-ram-runtime-20260925.json)
authenticated release `7.1.3-gemini-a53-service-facilities` and verified
`console_status=ready`, `active_vt=tty1`, one matrix input device, no historical
automatic observer, and the map before and after the observation. Its private
observation stream has SHA-256
`e7ff211cbbfff00198bf6d9865fe014e69b674ac925a5b738119e8bd437a400c`.
This is console and input preflight evidence, not an owner key challenge.

The exact candidate initramfs is
`0bd75912a8f35f097b0e26a52e1f2756612a342c9ac78067e5f6dfae5b76163b`.
Parsing its 47 members found `/bin/keyboard-observe` at
`51ef03def5461b2c13367906b3184a2dae14ca2f7ba7e835740be6a7268fa223`
and `/etc/gemini-us.bkeymap` at
`02f8048d76aa0cedf73617b13ea03a2a4e74de88222cb1922d9d19630906675c`.
Both hashes match the live A53 observation; the helper is also the exact one
used in the earlier [focused two-step hardware capture](../2026-09-05-owner-away-experiment-preparation/keyboard/TTY_PATH_COMPARISON.md#focused-physical-validation-after-corrected-startup).
The A53 composition changed only `/init` among the accepted RAM members.

The embedded helper's `--diagnose` mode provides two 15-second windows after
a two-second idle check, with exact input identity, console-mode checks, bounded
event output and termios restoration. Its first prompt is a plain `1` tap; the
second is the Shift/Fn/1 chord followed by `A`. This existing mode avoids a
new helper binary or a boot-critical image change. The earlier physical capture
completed both windows, but its held chord generated valid repeats. The
[current focused analyzer](../2026-09-05-owner-away-experiment-preparation/keyboard/analyze-focused.py)
separates physical edges from VT bytes yet compares the latter with a
single-tap string. It therefore marks the repeated chord's VT output as a
mismatch even when the captured events account for every byte. Freezing that
strict comparison as the per-cycle gate would turn a valid hold into a false
failure.

The [repeat-aware analysis receipt](results/a53-keyboard-method-analysis-20260925.json)
pins the extended analyzer and its five focused tests. The optional mode keeps
the original strict `vt` field and adds `repeat_aware_vt`, calculated from the
recorded key presses, held modifiers and repeats. It reports mismatches for wrong
VT bytes and missing physical input. The existing parser still rejects loss,
incomplete output and failed console restoration. On the preserved earlier
hardware capture, both physical sequences match; the strict repeated-chord mismatch
remains, and the repeat-aware VT result matches both windows, including 51
repeats in the chord window. This reanalysis makes no new hardware claim.

One separately admitted A53 keyboard-method boot must verify the helper,
console exclusivity, bounded capture/export and changed-boot Gemian return on
this exact image. That trial asks a new keyboard question; it is not a repeat of
the consumed CPU/USB/log observation. No ten-cycle selection is made here.
