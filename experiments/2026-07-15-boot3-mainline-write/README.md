# Boot3 mainline candidate write

Date: 2026-07-15 (UTC)

This experiment records one explicitly authorized write of the current
LK-compatible Linux candidate to the non-primary `boot3` partition on the
named Gemini PDA. The device address and credentials are intentionally omitted
from this tracked record.

## Target and safeguards

- Target device node: `/dev/mmcblk0p31`
- GPT logical name: `boot3`
- Target size: `16,777,216` bytes (16 MiB)
- Original read-only backup:
  `artifacts/device-partitions/20260715T020041Z/mmcblk0p31-boot3.img`
- Original backup SHA-256:
  `1fa78de9f8744a6818bcef2f6773737939f84364de982413910d4958d6d21513`
- No other partition was written. Preloader, RPMB, NVRAM, GPT, and the
  primary boot path were not touched.

The candidate payload is 15,714,304 bytes, so it was padded with zeroes to
the exact 16 MiB target size before writing. The padded image was streamed
through SSH to `sudo dd` with `bs=4M,conv=fsync,status=none`; the sudo
password was entered interactively and is not recorded here.

## Candidate and verification

- Package: `linux-7.1.3-gemini-6116c9e7da3f`
- Candidate: `guest:~/artifacts/boot-candidates/20260714-77-diagnostics4/linux-7.1.3-gemini-6116c9e7da3f.boot.img`
- Unpadded candidate SHA-256:
  `4cc0cc0df784e7ff79633884e2b093e3c2bc1d9c6f74f01af972a7034e88997c`
- Padded 16 MiB write-image SHA-256:
  `1c8954f116bd1a54844c80b3a5c21506ec6e21753059dd961456705b6ca5100d`
- Full-device read-back SHA-256:
  `1c8954f116bd1a54844c80b3a5c21506ec6e21753059dd961456705b6ca5100d`

The read-back hash exactly matches the padded write image. The original
backup was re-hashed after the write and still matches its recorded digest.

## Result and limits

- `hardware_write=mmcblk0p31`
- `write_result=success`
- `readback=full_partition_sha256_match`
- `runtime_boot=not_attempted`

This proves only that the bytes were written and read back correctly. The
device has not been rebooted, and no claim of Linux boot, peripheral support,
or recovery behavior is made. Any next boot test must use the UART console,
stable power, and a known-good recovery path; if the device does not boot,
restore the saved boot3 image from the separate recovery workflow.
