# Full compile through associated state and finite teardown

Status: build and hardware-free validation passed; no RF or device result.

Driver checkpoint `a709cb82b5a1f648381e0b3644224f0f4ee1c2d8` adds preparation
patches 0137–0139. The clean managed input was
`a9c1091ec285da55c25190e5e8cf0eaa6b7ce81e`; its intervening change adds only a
microSD experiment, with byte-identical manifest and Phase B series. The first
submission stopped at the pushed-HEAD preflight before any kernel job because
main advanced; after fast-forwarding the clean checkout the job was submitted
once. No kernel build was retried.

| Item | Identity |
| --- | --- |
| Builder | Buildbox-1, 32 jobs, modules disabled |
| Profile | `mt6797-a53-wifi-phase-b-compile`, 638 selected patches |
| Job | `a9c1091ec285da55c25190e5e8cf0eaa6b7ce81e-mt6797-a53-wifi-phase-b-compile-m0` |
| Completed UTC | `2026-10-06T02:44:03Z` |
| Package inventory | `d4f5add5d0767132468d2fdae268017b190a3f10db5c59a63f6c657be43d5320` |
| Release | `7.1.3-gemini-a53-wifi-phase-b-compile` |
| Image.gz | `ef4e4c75e8cbafcfa246488a490f73fb277825f5e925fdb78ab61a31b8e2c121` |
| Configuration | `153ea2d01db8edf518f28ebf01f5e28f1f94d08c649acbe4cca600430a8cdf2f` |
| Compiled board DTB | `07b097d581cae6208eea8387d534e14bb2c2bc30752b0d4b783f711284284734` |
| Phase B series | `ec8a3eddf16c7a3bf2c1caf533255f23d96488ff85a0ab182043c4b971cb0033` |

The terminal job is validated. Full package checksums, source/profile/commit
provenance, configuration/fragments and selected patch order passed both worker
validation and the standard laptop fetch. Linux `check-repository` passed,
including the artifact provenance checks skipped on macOS.

All four checked-in runners passed against the exact managed prepared source
with ASan/UBSan: peer callbacks, join-on/off handoff, actual HIF fault injection,
and 65,536 legacy-rate bitmap pairs plus high-bit rejection. The initial sandbox
peer run could not inspect `/proc` for LeakSanitizer; unchanged runners passed
outside that sandbox with sanitizers enabled. No leak check was disabled.

The build and fixtures validate host code only. Firmware application, kernel
concurrency, AP association, data and keys are unproven. Candidate and first
RF admission are separately pinned in [PROTOCOL.md](PROTOCOL.md).
