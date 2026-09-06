# Live Wi-Fi NVRAM identity session

## Admission and finite budget

This is one read-only observation of the already-running known-good Gemian
system. Execute mode requires a new mode-0600 private admission JSON containing
the expected release, architecture and boot identity plus three SHA-256 values.
The admission is
created by the integration owner from already retained, independently audited
inputs; this implementation does not access those inputs.

The host starts exactly one pinned-host SSH process and streams exactly one
remote script. The remote deadline is 15 seconds, the host deadline is 20
seconds, and combined SSH output is capped at 8 KiB. A new mode-0700 attempt
directory is required and cannot be reused or overwritten. The default command
is a dry run and performs no SSH.

## Allowlist and refusal boundary

Before any file read, the remote script checks `uname -r`, `uname -m`, and
`/proc/sys/kernel/random/boot_id` against the admission, then obtains exactly
one Android init PID from `lxc-info -n android -sH -pH`. It requires state
`RUNNING` and one numeric PID. From that PID it reads only:

* `/proc/PID/mountinfo`, read only up to 256 KiB plus one
  oversize-detection byte and parsed only when no larger than 256 KiB,
  retaining only the exact `/nvdata` and `/data/nvram` mount relation;
* `/proc/PID/root/data/nvram/APCFG/APRDEB/WIFI`;
* `/proc/PID/root/vendor/bin/nvram_daemon`; and
* `/proc/PID/root/vendor/lib/libnvram.so` (the fixed ARM32 producer path; a
  separately present `lib64` copy is not inspected or treated as an
  alternative).

The three selected files must be regular, non-symlink files. WIFI must be
exactly 514 bytes and has its `0xaa` plus alternating-add/XOR trailer checked
in memory. The daemon and selected library are capped at 4 MiB. Their raw
digests are never printed by the host: the host writes the private digest
tokens to three mode-0600 files below the ignored mode-0700 attempt directory.
The public result contains booleans and bounded counts only.

The remote collector pauses after emitting `admission_ready=yes`. The host
durably creates and fsyncs the mode-0600 consumed marker, then sends the exact
`GEMINI-WIFI-NVRAM-CONSUME-v1` ACK; no mount or fixed-file read occurs before
that barrier. Initial identity, PID, host-key, or authentication refusal
consumes no read. Any timeout, drift, malformed output or inaccessible input
after the ACK consumes the attempt. There is no retry. A narrow pass requires stable identity, one
matching mount relation, valid 514-byte envelope, and all three private digest
matches. It does not establish restoration history, factory provenance,
board/RF applicability, firmware application, regulatory safety or transmit
authorization.

No sudo, mount, namespace entry, `lxc-attach`, service action, radio or rfkill
operation, firmware/calibration load, ioctl, debugfs, device node, sysfs write,
partition access, reboot, thermal sample or log dump is permitted.

## Owner session card

No physical action is needed. `/root` remains the sole device custodian. On a
future authorized run, verify the Gemian release, boot identity and recovery
key before invoking the exact command below; do not create a second admission
for a changed boot without review:

```sh
python3 experiments/2026-09-06-mt6797-wifi-live-nvram-identity/collect.py \
  --execute --admission <private-mode-0600-admission.json> \
  --attempt-dir artifacts/live-nvram-identity/attempt-<new-id>
```

The result is evidence only. It grants no permission to initialize the radio,
load firmware, restore NVRAM, select boot2 or run a mainline candidate.
