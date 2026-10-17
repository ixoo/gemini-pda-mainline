# CCMP6: terminal completion-observation candidate

Status: physically booted with changed identity and the new symbol verified;
Phase A passed, no join result yet, 2026-10-17. The
[successor review](CCMP_COMPLETION_SUCCESSOR.md) owns the diagnosis, hypothesis,
finite protocol and decision branches. This is a measurement candidate, not a
transport repair or maintained Wi-Fi.

## Frozen kernel and candidate

One ordinary Buildbox build completed at `2026-10-17T22:07:35Z`, clean pushed
input `6a34397c3cda3b5a5a6847b9e84bd6e54f48bdee`, 32 jobs, modules disabled.
The owner authorized direct SSH submission for this independent session.
A local `BUILD_MODULES=false` argument was rejected before submission; the
actual submitted build used the required `BUILD_MODULES=0`. No extra kernel
build or device trial resulted from that argument error.

| Identity | Value |
| --- | --- |
| Profile | `mt6797-a53-wifi-ccmp-completion-observe` |
| Package inventory SHA-256 | `2123631e0983775991172e84ff4a10b5ebb396cf2d77872995d74780e1e60732` |
| Image.gz SHA-256 | `aa8aee95b4ec00e1759087e846a4f709fc42ae17dab2f482d7d22fc915c801ee` |
| Patchset SHA-256 | `bcdee9dfc912a8f7fec55c31b8d7680a8ea2a68710e81f4802dc55deed60f90d` |
| Config SHA-256, identical to C5 | `483e0165368ce521f7f6e082e5acbc612c26badab7cacdc1e1cd60166f15c350` |
| Built MAC SHA-256 | `216b899cc84f56a55698fc3b7688a5e7d526e068711bdc90eeffe76916ec14ed` |
| Real candidate receipt SHA-256 | `d12ea43d7ddc4e0f9b836bcc7d9db081a06dc640a091b087cdaba8c5fd4865c2` |
| Raw boot.img SHA-256 / bytes | `e8b715ceb182a33b2e5a3152da5cb73a33cac2fee987c5a506d4f4bdbaf7ea46` / 12673024 |
| Full boot2 SHA-256 / bytes | `fbb5eb729638bec7afb435782b1dbb73219ff3e52469b0aa946ca26073ff3091` / 16777216 |

The [build validation](results/ccmp6-build-validation.json) records the
847-member package. Ordinary fetch verified its inventory. The actual applied
source passed the helper ASan/UBSan fixture; HIF, header, other driver files
and consys match C5. The built System.map contains
`mt6797_ccmp_observe_terminal`; require this symbol on the new live boot in
addition to deployment/boot identity checks, without publishing its address.

The [compositor](build-ccmp-candidate-6.py) uses real validated package pins.
The [receipt](results/ccmp-stable-monitor-candidate-6.json) and its
[runtime copy](runtime-ccmp6/results/candidate.json) are byte-identical.
All six composed members were independently size/hash/mode verified;
configuration, DT and RAM are byte-identical to C5. The parent remains the
verified private C32 candidate, not a newly constructed RAM root.
`integration_source_commit` `1e20191a` denotes the bounded MAC authoring
snapshot exported as 0196, not a standalone Linux revision; the complete
kernel inputs are pinned by the project build commit and patchset above.

## Fresh tooling and historical source lookup

Fresh prepare/installer/capture/host/session wrappers bind receipt 6 and
`capture-ccmp6` / `session-ccmp6`, reusing the frozen one-cycle leaf, no-scan
route, helper ownership and reviewed recovery. Completed C5 tools, receipt,
private captures and candidate remain unchanged. No binding-only rebuild.

The actual installer requires three historical source pins. The public base
script changed after its pin; offline preparation correctly refused the
current bytes. Recover the base from `cac47380`, verify its required
`deaa0e88…` digest, and retain the exact pinned deriver and device guard.
Use ignored, non-symlink regular files; do not edit the frozen sources or pins.

C6's `GEMINI_INSTALLER_SOURCE_ROOT` optionally selects that three-file source
store. `GEMINI_PRIVATE_REPO` retains the actual credential/tool checkout and
derived `repo_root`. Omitting the optional variable preserves the old lookup.
The [source test](tests/ccmp6-installer-sources-test.py) checks both defaults,
separate roots, unchanged pin/derive functions, altered-byte and symlink
refusal. No credentials are copied into the source store.

The [whole-shell review](results/ccmp6-installer-review.json) verifies the
603-line derived installer against the hash-verified frozen C5 installer,
with only exact identity, tool-path, program-digest and predecessor
substitutions. Bash syntax and ShellCheck pass; all gate/staging/write/
readback/shutdown logic and the guard's `0f0fc88c…` digest remain unchanged.
The derived shell SHA-256 is
`2642e42fc0f6f9ab1b74a738b5f2ea71ed3f9ad8d16581c77f3bf4d30fb282ed`.

## Validation and device handoff

Local and Linux repository checks passed, including Linux-only provenance
fixtures. C6 composition/config, real-receipt wiring, source-root and no-scan
failure/owned-child fixtures passed offline. The two new namespace fixtures
resolve their temporary root on macOS, matching production's canonical paths;
production namespace behavior was not changed. Kernel compilation passed.
Checkpatch's sole reported issue remains the intentionally absent truthful
DCO sign-off on this internal non-certifying proposal. No DT change or new
schema claim is made.

The observed Gemian boot before preparation was
`d09f829e-2a7e-4b5f-a240-b718c63f26ff`, release `3.18.41+`, aarch64.
Fresh live checks remain mandatory. The installer expects C5 full boot2
`776cccbe…` or an already matching C6; it must resolve logical boot2 from live
GPT and retain its inactive/unmounted/non-root/size/power/guard gates.
Require full C6 readback, flush and clean shutdown. The owner then physically
selects boot2. No automatic boot or alternate partition is admitted.

Keep Python 3.13 selected for CLI and child commands, and export the private
checkout, historical-source store, fresh runtime root and unchanged private
join binder through final receipt validation. Copy only the actual deployment
summary into session 6. Authenticate changed boot/release/new terminal symbol,
then execute one capture and one session, preserve/seal/quiesce, and perform
one reviewed return. The successor's existing finite budgets and result
branches remain binding; no unchanged-artifact retry or PN/length exception.

## Verified installation and pending physical selection

The [deployment scalars](results/ccmp6-deployment-scalars.json) record the
actual guarded C5-to-C6 write, sync/flush and matching full-partition readback.
Both live guards passed in the known-good Gemian boot named above; the stable
power gate passed. The device shut down and became unreachable. No reboot,
capture, session or runtime retry was requested. The owner must physically
select boot2 with USB connected before the single new capture/session.

Executed installer tooling was `4a383654`; the independently hash-verified
actual deployment summary is 942 bytes, SHA-256
`5ad73fc8ae57cd5bdf26f7d7ac4b827ffc276352ba4df2fa87fa509b049064c5`.
Its byte-exact mode-0600 copy is retained in the fresh session-6 directory;
the raw summary and private paths are not published. The artifact receipt's
original `physical_admission=false` remains composition metadata, not a
replacement for this separate deployment record or a runtime-support claim.

## Host source preflight after physical selection

The owner selected boot2. New boot
`71a631b3-5628-459b-a040-f4ea698baca5` reports the expected release/aarch64
and the new terminal symbol; the single capture completed with Phase A ready.
The first session CLI refused on the recovery v2 source pin before
`HOST.prepare`, a session claim, helper spawn or device commands. No join,
session execution, capture retry, boot retry or recovery request resulted.

The [source-routing review](results/ccmp6-session-source-review.json) records
the exact old host/return/v2 hashes, recovered from the retained public Git
revision preceding `a0887d2c`. Current public recovery sources were sanitized
after those pins. A private historical tooling cohort outside the active
checkout preserves all original
source checks rather than changing their expected digests.

Only the C6 laptop session adds optional `GEMINI_SESSION_SOURCE_ROOT`, reusing
the existing source remapper for RETURN_V2, SERVICE and BASELINE. Credential,
calibration, candidate and evidence roots remain separate and unchanged; no
credentials were copied. The focused source fixture checks these namespaces
and original recovery-pin rejection. Complete actual offline preparation now
passes without device action. Kernel, candidate, leaf, effect budgets and
recovery behavior are unchanged; the first real session remains unconsumed.
