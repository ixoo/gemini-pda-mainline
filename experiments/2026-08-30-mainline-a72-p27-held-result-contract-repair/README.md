# Experiment: accept the held P27 acquire result

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-30-mainline-a72-p27-held-result-contract-repair` |
| Status | `runtime crossed P27 and stopped at the isolation result contract; candidate retired` |
| Subsystem | MT6797 CPU8 binder and platform-effect owner contract |
| Device variant | Planet Computers Gemini PDA, named development unit |
| Date(s) | 2026-08-30 |
| Tracking issue | `docs/ROADMAP.md` late Cortex-A72 admission gate |

## Question or hypothesis

The exact P27 runtime attempt returned a complete successful physical acquire
with `p27_owned=1` and `sealed=0`, but the binder rejected it with `-EPROTO`.
Does matching the binder's acquire-result seal expectation to the platform
owner's intentional held state allow membership P27 completion without
weakening release or later-stage validation?

## Provenance and environment

- Parent: canonical Linux 7.1.3 series through patch `0449`.
- Parent source state: `7c82a444be80afc47304f2b620e49c7853600770bc2409d0d715bbcbc44b105c`.
- Parent integrity: `c76cb7d15244a1891f5e2d144ce92a4c30909e716e3fa746e82edc0d3ff80260`.
- Build and patch generation backend: Buildbox only.
- Admitted repository commit: `870980dd907856f62c021ddbf8b1b9e7d4c3658e`.
- Canonical patchset SHA-256: `ea68a1ab52a72451b8e7dbde73b143516765f45593e4aaa4cf1b2eaf0c17dd31`.
- Runtime source: the single-trigger result in the preceding
  [P27 attribution experiment](../2026-08-30-mainline-a72-p27-runtime-attribution/README.md).

## Safety assessment

The repair changes only a binder validation predicate and its KUnit fake. A
successful P27 acquire must be unsealed because ownership remains held for the
provider, isolation, SRAM, CPU_ON, and DCM stages; a release must remain sealed.
The patch adds no hardware operation, CPU request, CPU9 path, CPU_OFF path,
retry, retained-RAM write, storage access, timing change, or device action.

No device candidate may be constructed until deterministic replay, strict
style review, focused KUnit, and the production profile build all pass. CPU9
remains vetoed until CPU8 is reproducibly online.

## Associated code

- `scripts/source_edits.py` performs the two exact source edits.
- `scripts/generate_patch.py` creates and replays canonical patch `0450` from
  the pinned managed source.
- `scripts/generate-on-buildbox` enforces the clean Git-pinned Buildbox lane.

These scripts require no device access. The generator writes only a temporary
Git tree and a checksum-covered patch-review package on Buildbox.

## Procedure

1. Generate one normal format-patch from the exact post-`0449` source.
2. Require the binder result-shape helper to compare an explicit expected seal
   state: false only for P27 acquire and true for release, isolation, and DCM.
3. Make the KUnit P27 fake reproduce the production held-owner contract and
   preserve the malformed sealed-acquire rejection.
4. Replay the patch deterministically and reject any hardware/request call-count
   change or forbidden path.
5. Admit the patch canonically, run focused binder/transition KUnit on Buildbox,
   then build the production live-trigger profile on Buildbox.
6. Compose the package-exact provenance leaf with the proven serviceability DT,
   assemble and independently validate two exact LK containers, then deploy the
   full-partition candidate to live-GPT `boot2` with readback and shutdown.
7. On the exact selected boot, require the pristine armed pre-trigger state,
   issue one trigger without retry, capture the terminal status, and recover the
   retained transition ledger after the watchdog return to Gemian.

## Observations

- Buildbox generated exactly one patch from the checksum-pinned post-`0449`
  source, and deterministic replay reproduced it.
- The patch changes no physical-effect or CPU-request call count and adds no
  CPU9, CPU_OFF, retry, retained-RAM, storage, or device path.
- Strict Checkpatch reported zero warnings and zero checks. Its sole error is
  the intentionally absent DCO sign-off on the synthetic experiment author;
  this internal archive is not submission-ready.
- The exact generated patch SHA-256 is
  `bb050d483a31f79214e0fb7abd49408770a69998fdb771f9074c9da487e38fbc`.
- Focused no-network QEMU KUnit passed all 48 P24-owner, transition-executor,
  and binder cases with no physical CPU request, CPU_OFF, or retry.
- The production Buildbox package and two independently composed candidates
  passed package checksums, 32 LK gates, six negative container mutations, and
  byte-for-byte reproduction.
- The raw candidate SHA-256 is
  `df243481ab19dec4d6899c3478391140cc6602f5a5435e11229f7afb0d68ebb3`;
  its exact 16 MiB `boot2` SHA-256 is
  `fbe0bf76dd0cd88f1bc89043b72e9b7e4fe705568d8107b956eb6c3bd18593b5`.
- Live-GPT deployment replaced only the exact predecessor
  `e22db74764e70d11f75271012733b8922a6f231d46ce363dfad9fafacdec0a80`,
  matched the full readback, and ended in a confirmed clean shutdown.
- A first collector invocation was rejected as a tooling result because its
  source-pinned wrapper emitted source rather than executing the materialized
  probe. It made no trigger, hardware, retained-RAM, storage, or reboot request.
  The wrapper was repaired before the qualified attempt.
- Boot ID `0850abe2-400b-4c44-91f3-046a4a358614` matched the exact candidate,
  reached the USB/netcat serviceability gate, and showed the pristine armed
  state with CPUs 0--7 online, CPUs 8--9 offline, and zero prior executions.
- The sole trigger returned `-EPROTO` with one CPU8 request, no CPU9 request,
  no CPU_OFF or retry, lifecycle `TERMINAL`, last stage `ISOLATION`, and terminal
  class `FAULT_RETAIN_POSTISO`. P27 and provider ownership were retained.
- The acquire result remained the expected complete held P27 transaction:
  operation 1, error 0, attempted/completed mask `0x7`, SPM P27
  `0x10132 -> 0x10133`, ownership true, and seal false. No P27 release ran.
- The watchdog returned the device to Gemian with changed boot ID
  `e7181fd8-0e34-4f3d-87ba-e8208e51e664`. The checksum-valid 72-byte pstore
  payload preserves generation 7 before isolation and generation 8 terminal at
  isolation with terminal class 4.

## Analysis

The runtime's complete `0x7` acquire mask and `error=0` exclude a physical P27
failure. Production source intentionally leaves `sealed=false` while the owner
is `P27_HELD`; only failure and release paths seal the result. The current test
fake instead returns `sealed=true` for success, so its green success path does
not model the production contract.

The repaired runtime crossed that boundary: P27 was accepted, the provider was
acquired, and execution reached the isolation operation. Production isolation
sets the owner to `ISOLATED` and returns success after completing isolation,
PWRAP deassertion, and the guard delay, but intentionally does not seal the
result because P27 and provider ownership continue into SRAM, CPU_ON, and DCM.
The binder requires `sealed=true` at this boundary while the KUnit fake returns
sealed success, reproducing the same contract-model mismatch now isolated by
the exact `-EPROTO`, stage, retained-owner mask, and pstore record.

## Conclusion

Patch generation, deterministic replay, focused KUnit, production Buildbox
build, dual candidate reproduction, independent validation, guarded `boot2`
write, full readback, clean shutdown, exact runtime identity, one bounded
trigger, and retained recovery evidence pass. The P27 repair is successful at
its intended boundary. CPU8 remains offline because the next valid held result
was rejected at isolation; this candidate is retired and must not be repeated.

## Follow-up

Make only the isolation seal expectation and its KUnit fake match the production
held-owner contract, preserving sealed release and DCM completion. Repeat the
focused offline suites and production Buildbox build before considering one
changed successor boot. Do not prepare CPU9 until CPU8 is reproducibly online.
