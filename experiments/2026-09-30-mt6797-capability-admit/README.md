# Admit the first capability query after START readiness

The [stage-trace boot](../2026-09-29-mt6797-capability-trace/results/runtime-1.json)
returned `-EIO` at stage 0 before a WRPLR read or command submission. Source
inspection identifies a deterministic state mismatch: a successful
`mt6797_start_observe_ready()` moves the INIT transaction from `START_READY`
to `INIT_IDLE`, while the capability query still requires `START_READY`.
Patch 0055 changes that sole gate to require `INIT_IDLE`; it retains the
firmware-ready, one-attempt, deadline and transport guards. There is no new
radio, calibration or packet DMA action.

The [focused host test](tests/test-capability.c) exercises the actual patched
HIF source. It first runs the START state transition before each query, then
checks the existing successful exchange, all 69 injected scalar access faults,
stale queue, malformed reply and deadline. It also proves the pre-readiness
phase is refused without HIF access. The previous test had incorrectly set
`START_READY` and `firmware_ready` together, hiding the live mismatch.

The next physical boot will test whether the corrected gate admits the one
bounded command and, if submitted, whether firmware returns a valid capability
event. A failed queue, TX, reply or parser stage remains a terminal observation
for that boot. A successful capability event establishes only a command/reply
exchange; network interface, association, traffic and radio safety need
separate evidence. Preserve the complete log and A53 regression, then return
to changed-boot Gemian through the reviewed path.

## Build and candidate

The clean pushed commit `9c7ef140eea1fc1fd0d2138c3828e95824e11ad8`
built on Buildbox as profile `mt6797-a53-wifi-capability-admit` and release
`7.1.3-gemini-a53-wifi-capability-admit`. The validated package inventory is
`3ea7068941d23a9559001c0630fac9445314eebd346267864b602fe396fdeba4`.
The private 52-member RAM root changed only `/init`'s release gate; firmware
remained hash-identical. The assembled candidate retained the prior booted
board DT at SHA-256
`cef9373ea3aa0e1a8a45a13b953ae95e48939b211e41a73052543be784ee3214`.
The [sanitized candidate receipt](results/candidate.json) pins full boot2
SHA-256 `f066866c178e38d77f18722f9e3286a6e98316997e28f2157c62f434f1aa1d4b`.
The [build receipt](results/build.json) records the package and focused test.

The guarded installer is bound to the current known-good Gemian boot and the
previous boot2 checksum. Offline candidate validation, Bash syntax and
ShellCheck passed. It will resolve logical boot2 from live GPT, recheck the
reviewed device guard, skip a matching full-partition checksum or otherwise
write, flush and require a matching full readback before clean shutdown. The
owner then selects boot2 physically. This candidate has not yet been installed
or booted; no mainline capability exchange is claimed.
