# First Phase B deployment, device test pending

This preparation was consumed by [runtime 1](RUNTIME_1.md), which failed common
init before WLAN and returned to confirmed changed-boot Gemian. The deployment
and pre-test observations below describe the state before that test.

Status: installed and fully read back; device cleanly shut down. No mainline
boot, host RF transmission or join result has been observed for this candidate.
The owner must physically select boot2; the laptop remains the sole custodian.

The [guarded deployment receipt](results/deployment-1.json) pins candidate
`6ecc057c390e6c9acb3480a52950a7261d7f4678c43da5688dcc1724e2bb778f`
and its matching independent full-partition readback. Live Gemian was verified
as kernel `3.18.41+`, Debian 9.13, boot
`9ade2913-f209-43b4-a2d3-3ed773f673b4`. The live GPT resolved boot2 with device
number `179:30`, distinct from root `179:29`. Inactive/unmounted/non-root and
stable-power gates passed immediately before writing. The current C1-5
predecessor matched its retained candidate and guarded installation receipt.
No fresh predecessor backup was made; the verified project-wide backup remains
the recovery foundation. No protected partition or device table was written.

The installer synced/flushed the write, verified full readback, preserved its
receipt and requested clean shutdown. Subsequent reachability was absent.
The prepared capture and session both passed offline against the actual
deployment receipt, candidate, private firmware/record/userspace and credentials.
The private session directory initially had the wrong mode and was corrected
to 0700 before those checks; no device command was attempted by preparation.
Shell syntax and ShellCheck passed, and host fixtures reject duplicate/incomplete
join evidence and shell-unsafe or out-of-scope AP input. Repository checks pass.

The next action is the owner-operated boot2 handoff followed by the exact
[bounded protocol](PROTOCOL.md). Wi-Fi remains incomplete: this admission tests
management exchange only; data, WPA2 keys and operational network testing follow.
Raw installation, AP inputs and subsequent captures stay private. Published
metadata excludes personal endpoints, paths, identities and credentials.
