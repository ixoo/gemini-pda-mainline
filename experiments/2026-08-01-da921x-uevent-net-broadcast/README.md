# DA921x original kobject net-broadcast wrapper

| Field | Value |
| --- | --- |
| ID | `2026-08-01-da921x-uevent-net-broadcast` |
| Status | `offline candidate validated; awaiting guarded deployment` |
| Subsystem | I2C, OF, kobject uevent, netlink namespaces |
| Device variant | Named Gemini PDA development unit |
| Investigator(s) | Julien Etienne and Codex |
| Tracking issue | Roadmap Gate 3 transport boundary |

## Question or hypothesis

Can the exact runtime-proven stage-23 event traverse the original
`kobject_uevent_net_broadcast()` wrapper once, with one namespace decision
selecting the untagged route and never the tagged route, while preserving the
same single receipt and zero-hardware serviceability baseline?

Stage 23 proved the original untagged delivery function directly. Stage 24
moves exactly one call boundary outward. Experiment-only observation is active
only for the retained target during the one synchronous wrapper call.

## Decision

- Stage 24 with one attempt, wrapper entry and return, namespace check,
  untagged route, socket, listener, allocation, broadcast, normalized return
  zero, one exact receipt, and no duplicate passes.
- Any tagged-route selection, extra call, topology change, receipt mismatch,
  or baseline change rejects attribution.
- Visual white/grey-screen and reboot behavior alone remains inconclusive.

## Safety and build policy

The experiment emits one intentional uevent multicast only after reconstructing
the proven stage-23 predecessor with checksum-pinned helpers. The matching
DA921x driver remains module-only and absent from the initramfs; the real client
remains unbound. The patch adds no driver, provider, I2C transfer, register
access, printk, or device-storage path.

Build only through `./scripts/build-kernel --backend buildbox` from an exact
clean pushed commit. Do not run a native VM kernel build unless the owner
explicitly requests one. The experiment-only patch has no DCO sign-off and is
not submission-ready.

## Associated code

- Patch `0145` adds the one-shot wrapper and namespace-route observation.
- `scripts/build-listener.sh` source-pins and mechanically derives the static
  stage-24 listener from the runtime-proven stage-23 listener.
- `scripts/build-candidate.sh` derives the exact LK candidate assembler from
  the validated stage-23 workflow.
- `scripts/install-boot2.sh` accepts only the exact stage-23 predecessor and
  stage-24 candidate, requires full readback, and shuts down after success.
- `scripts/collect-runtime.sh` reconstructs stages 21 through 23 with pinned
  helpers before invoking the separate stage-24 serviceability check.

## Follow-up

All 134 patches apply to the pinned Linux 7.1.3 source. The named profile
resolves the full stage-23 predecessor plus only the net-broadcast gate and
release `7.1.3-gemini-da921x-netwrap`. All 51 manifest profiles pass the
canonical-order invariant and all eight focused mutations are rejected. Strict
checkpatch has zero warnings and checks; its sole error is the intentionally
absent experiment-only DCO. Two static ARM64 helper builds were byte-identical.
Host and VM free-space checks passed with 91 GiB and 83 GiB available. Exact
identities are in `results/input-validation.txt`. No native VM kernel build or
device access was used.

Buildbox compiled exact clean pushed commit
`35054eab8644ccace1d2eb55d279b077d1a28928` with the intended release,
profile, patchset, and configuration. The fetched package passed its checksum
manifest. Two independent boot-container assemblies were byte-identical and
passed all 32 LK gates. One validated copy is retained below the ignored
artifact tree and both regenerable VM copies were removed. The guarded
installer and four-listener runtime chain passed syntax and ShellCheck. Exact
offline identities are in `results/offline-validation.txt`. Commit and push
these deployment inputs, then install only the selected candidate to live-GPT
resolved `boot2` from Gemian.
