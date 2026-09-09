# Console successor deployment and swap prerequisite removal

On 2026-09-09, the owner returned for attended device tests. The primary
integration coordinator took exclusive custody. Authenticated known-good
Gemian was `3.18.41+`, AArch64, boot ID
`6a5395c2-71d0-4392-a397-be3be83b049b`.

The first installer invocation passed the live-GPT boot2 and power checks but
refused active swap before staging or writing. Its refusal and empty receipt
directory were preserved privately. Separate bounded observations matched the
reviewed unused zram entry and startup policy. One reviewed temporary
deactivation completed on the same boot with ample memory. Only after reviewing
that result was a second installer invocation admitted.

The existing installer then wrote the exact candidate from [validation.json](validation.json)
to logical boot2, resolved as `/dev/mmcblk0p30`, device `179:30`; the live root was
separate at `179:29`. The predecessor padded digest was
`29f59c7f21a25b47d63d653857db9d7d0760d9a00f7193e098219699235f16f1`.
Write, sync, flush and independent full readback matched all 16 MiB of the
selected padded image:
`7d9eb0e20f145594ba5b9e56bbb809998c813d2517ce2f43b17074828459ea2a`.
Private staging/readback were cleaned, evidence flushed and clean shutdown
confirmed by subsequent unreachability. No automatic reboot or fresh backup
was performed. The parsed deployment receipt SHA-256 is
`cf9448e410ba378cee2b7f2317c10856532ffa2a01962813b262be05d6cb8e8f`.

The device is waiting for one owner boot2 selection. Installation does not
establish a mainline runtime result. The [first session](SESSION.md) remains the
console-ownership observation; the disconnect proof is still conditional.

## Owner-requested installer change

After this completed installation, the owner requested removal of the swap/RAM
prerequisite. The active A53 installer now permits non-target swap during
staging, upload and writing. It no longer requires zram deactivation or the
associated memory/ownership investigation. The old swap procedure is historical.
The existing block-device guard still rejects boot2 or its parent as active
swap, and retains its mounted/root/holder checks. Private tmpfs file identity,
space, power, checksum, readback and cleanup checks remain intact.

This is an installer-only change. Candidate bytes, the completed deployment
and its original installer identity remain unchanged. The revised default
installer derives locally as
`df0cbf108ef84eda76af0a7361534530a822861b7144704d682fe32236e6be9e`.
It was not executed on the device and does not require another installation.

Validation passed: 11 host installer methods, 39 generated remote-gate cases
and 10 staging cases, including active zram/non-target swap acceptance and
target-swap refusal. Candidate validation, generated Bash syntax and ShellCheck
also passed. No kernel build or mainline observation was run for this tooling
change. Raw device evidence remains private; this record contains only selected
state, sanitized boot identity and deployment digests.
