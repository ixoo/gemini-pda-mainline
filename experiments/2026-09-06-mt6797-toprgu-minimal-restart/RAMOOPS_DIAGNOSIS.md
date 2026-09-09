# Ramoops refusal: reservation exists, backend success unproved

## Recovered observation

The failed boot's earlier log-inspection output records the reserved interval
`0x44410000..0x444effff`, described as 896 KiB, no-map, non-reusable,
`ramoops@44410000`. It also records `ramoops_init()` returning zero and the
later `pstore_init()` returning zero. This rules out an entirely missing
ramoops reservation in that captured boot log. Neither initcall return proves
that a ramoops platform device bound or that the backend registered.

The attribution is deliberately limited. The original task's capture command
recorded a 91,589-byte `kmsg.log` with SHA-256
`46397056aa45e7909e6d41b7dd1df0eb9cfba4648b80eeaaa9fa71b8645e57c9`, matching
the existing [runtime receipt](results/runtime-20260906.txt). Its subsequent
read-only search of that same path printed these records:

| Log line | Record sequence | Observation |
| --- | --- | --- |
| 21 | 20 | Expected ramoops reserved interval and size |
| 309–310 | 308–309 | `ramoops_init()` called and returned zero |
| 1224–1225 | 1191–1192 | `pstore_init()` called and returned zero |

This follow-up recovered the earlier command output, **not the complete log
file**. The historical worktree's artifact directory is unavailable at its
recorded path, and a size/checksum search under the current checkout's
artifacts found no matching file. No claim of complete-log revalidation,
absence of all probe errors, or recovery of unique raw evidence follows.

## Static package check

The retained Buildbox package's base Gemini DTB was rehashed and matches
`d7b583545fc3b4916c363d9e4b70d0ee7aef815675ca8ba58894bdbaa2e1dccc` in the
[build receipt](results/buildbox-745ecaea.txt). Its ramoops node has compatible
`ramoops`, the same address and size, no `status` property, and record/console/
ftrace/pmsg sizes `0x1000`/`0x10000`/`0x1000`/`0x20000`. This check concerns
the base DTB, not a fresh reconstruction of the composed candidate or proof
that every property survived loader handoff.

## Next diagnosis

Keep the original refusal and consumed-candidate rule. The live zero address
and size remain inconsistent with the required successful backend. Do not
remove the preflight simply because reservation and initcall records exist.

Resolve the platform-device creation, matching and probe outcome for this
exact boot, using the full retained log if recovered and any attributable
retained DT/device metadata. An intact reservation does not establish the
live compatible/status properties, successful resource mapping or pstore
registration. Avoid rebuilding an unchanged DT merely to recreate a reservation
already observed. No cause has yet been isolated that justifies a corrective
kernel patch or another physical selection.

No device access, boot, register operation or kernel change occurred. This is
an incomplete offline diagnosis; the historical runtime classification remains
inconclusive and no restart was issued.
