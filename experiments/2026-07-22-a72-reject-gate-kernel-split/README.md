# Experiment: isolate the corrected MT6797 A72 reject gate

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-22-a72-reject-gate-kernel-split` |
| Status | `hardware PASS for exact AI's eight-A53 console, USB, and native-restart baseline; CPU8/CPU9 rejection and all Cortex-A72 behavior pending` |
| Subsystem | ARM64 SMP and MT6797 CPU operations |
| Device variant | Current named Gemini PDA unit |
| Date(s) | 2026-07-22 |
| Investigator(s) | Project maintainers |
| Candidate | `AI` |

## Question or hypothesis

Does the corrected, fail-closed MT6797 Cortex-A72 PSCI method preserve the
hardware-passed Candidate AD runtime when it is the only kernel change after
patch 0087?

Candidate AI deliberately separates patch 0092 from the 0088--0091 regulator,
Device Tree, reset-controller, and observer work carried by AF/AH. Its kernel
must be built from the exact Candidate AD patch sequence (0001--0087) followed
only by the corrected 0092 patch. It keeps Candidate AD's exact resolved
configuration, initramfs, keymap, console helpers, USB gadget, keyboard,
simplefb, pstore, eight-A53 `maxcpus=8` policy, and native restart contract.
The final packaged DT is byte-exact Candidate AH, whose only semantic delta
from the hardware-passed AD final DT is:

```text
/cpus/cpu@200/enable-method: psci -> mediatek,mt6797-psci
/cpus/cpu@201/enable-method: psci -> mediatek,mt6797-psci
```

AI does not request CPU8 or CPU9 online. A runtime pass would isolate the
reject-gate kernel implementation from AF's regulator/reset/observer kernel
delta. A failure with an attributable AI identity would reject that isolated
kernel change. A grey screen without an exact AI USB or pstore identity would
remain an early-handoff observation problem and must not be interpreted as a
gate-path failure.

## Pinned inputs

- Linux source: `7.1.3`, tarball SHA-256
  `be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc`.
- Exact AD series through patch 0087: 88 entries, series SHA-256
  `124db1a0c4d3d4f5ee43d75bbced9d4b5f28a649ef92c04acdb8ccb67be4117a`,
  patchset SHA-256
  `efb79d0ced5ebee485e337f224075faaa4abf7eb7d5e6a38326383274cd75f93`.
- Corrected patch 0092 SHA-256:
  `cbd54d048e2233ffcb268174037248ade9ab8716f9816481d926b20b4bd3bba5`.
  Its `cpu_can_disable()` implementation returns `false`; the exact source
  identity is part of the gate.
- Candidate AI profile:
  `observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-a72-reject-gate`.
  It path-selects `patches/series-a72-reject-gate`; falling back to the
  top-level `patches/series` is invalid.
- Selected AI series: 93 physical lines and 89 patch entries, content SHA-256
  `b172d419cc1e331932e734dda57be076872a442719dd6d406b217d81547dfd00`,
  path-sensitive patchset SHA-256
  `ba2cd5a66bd1fcff6552674d6d875d363e4ef0a24cfd10ede4f304136f0dc0dd`.
- Exact AD resolved configuration SHA-256:
  `32dd13a6704e5fa591236ba114d43e8e7e1aeb3eb123d9d4f124b5f551301d46`.
  AD's original profile input SHA-256 is
  `37223bd4a7e2e3ed0852b9dfe3ea4f5e4268b4e7db69d9cf40eafabf75441a67`.
  AI reuses those fragment bytes and order under its path-selected profile,
  giving config-input SHA-256
  `ad93d6669bd261cf1171237328dd9209fd45b2c3ed2154e441a1951908da4ba1`;
  the resulting resolved configuration must still be byte-exact AD.
- Exact AD artifact `candidate-AD-smp8-final-a1b61d8c`, manifest SHA-256
  `c3aeccf2e6e18a0c4769b909ccf45a77f75cc3677fe61fbd786d0925154fc51f`,
  boot SHA-256
  `a1b61d8c34b5a447f1f672663f4e74fed6eb465b90154392a3c42f4db030826b`.
- The only accepted Candidate AD kernel-package manifests are the two
  independently reproduced builds recorded by the AD experiment: SHA-256
  `1fbdb9aa20737e081cdcba2086f3ae435e702d44090e94e9cb47d0e3224816ab`
  and
  `c601cdc3b6317d98d6781fe8b64add043505c935da503f42233e2dd2a8a546f9`.
  The AI package validator rejects any other AD package before using its DTBs.
- Exact AD initramfs SHA-256:
  `166c0f03ab9ca1062f36d55132141b4be5f06187380d17ab2f6e9e7db75d1dd3`.
- Exact AH artifact
  `candidate-AH-ad-contract-af-kernel-split-e5ba6ee0`, manifest SHA-256
  `04b25bfc5e72645318273e03adc80191df7d52994acc7ade8202a64d95223997`,
  boot SHA-256
  `e5ba6ee0a257b804a02af11b83e733f861b89de17470470a497f07056b6b3197`.
- Exact AH final DT SHA-256:
  `27175804f052259c86ed068d2c318e83d5b2090f4aa705e063f9c9b33a4ca845`.
- Exact AF artifact `candidate-AF-a72-observer-initcall-fe43efa8`,
  manifest SHA-256
  `77e311af022e067185b9c9462137cfb73bb639ef0f29d9eb946d326097636e22`,
  boot SHA-256
  `fe43efa8c9d18174fec97ab7ad6cbe59bbc490df92366bcd254c55daa932d0a3`.
  AF is an exclusion oracle: AI must contain the same named reject method but
  must not reuse AF's kernel, configuration, or 0088--0091 features.

The AI package name, `Image`, `Image.gz`, `System.map`, and normalized build
record identities were intentionally not pinned before construction. Two
independent recovery-VM builds reproduce those package outputs. Two subsequent
Android-v0 constructions now reproduce the raw artifact and manifest
identities recorded below. A separate, storage-inert calibration also
reproduced the exact 16 MiB zero-padded hash twice, then removed both temporary
padded files without publishing either one. Guarded-installer derivation and
static validation are complete, and the separately gated exact logical
`boot2` installation and full readback are recorded below.

The calibrated full-partition identity
`8b7439dda7d50dfd509dd66acb5eeedda86d538f0b4f0fab9b328bcc93ed8b86`
is now source-enforced by `collect-cycle.sh`, `collect-runtime.sh`,
`validate-runtime.py`, `collect-recovery-evidence.sh`, and
`validate-recovery-evidence.py`. Their final source SHA-256 values are,
respectively,
`6dfb193a2eacf77fb5c588152338d4b304affe14bb81df05d53ee377db057366`,
`5fe46ea345e8ec94ea2253c26e7f359f0ba46fd1e792598086c891806b3617bf`,
`a1ca2a1a7a33eda0f9f52bbee8d964f3ed3004566183792f2eb4f446cffb1e38`,
`69e93eccc63d88c6d194da35a9e93283e7aa56a98432c6fbc6e99778a1ebe115`,
and
`234e33e013c86d3491377e902593113695e417ad0087aabda8858b35cbb5a1c7`.
The nested collector/validator pins match those identities. The combined
wrong-hash mutations prove that a caller and transcript cannot agree on a
different well-formed hash and pass.

Patch 0092 is a local diagnostic safety gate, not a submission-ready upstream
change. It deliberately blocks the unsupported A72 operation and has neither
an upstream submission claim nor a fabricated sign-off/DCO assertion.

## Safety boundary

The series contains no patch 0088, 0089, 0090, 0091, or 0093. The validator
rejects DA9211/DA9214 support, the MT6797 TOPRGU reset-provider addition, the
A72 resource observer, its DT node, `regulator_ignore_unused`, its initcall
blacklist, and any active CPU8/CPU9 request. The exact AD command line retains
`maxcpus=8`; CPU0--7 use generic PSCI and CPU8--9 remain offline. The custom
method's exact source returns `-EAGAIN` before `PSCI_CPU_ON` and reports that
CPU disable is unavailable.

Artifact construction, ephemeral padding calibration, and installer
derivation/static validation are storage-inert and have no device interface.
The exact generated installer is the sole optional hardware-writing path. It
requires the installed full-partition AH predecessor, resolves logical `boot2`
from the live GPT, preserves a private full backup, permits one bounded 16 MiB
write, and requires synchronized, flushed, full-byte readback. The completed
operation passed those gates and did not reboot or select a slot. Runtime and
Cortex-A72 interpretation remain separate pending evidence gates.

## Associated code

- `scripts/validate-series-selection.py`: validates the manifest-selected
  `patches/series-a72-reject-gate` path, its explanatory header, exact AD
  entry prefix, corrected 0092, and path-sensitive patchset identity.
- `scripts/validate-lineage.py`: validates the exact AD, AH, and AF artifacts,
  including manifests, modes, shared userspace, and AH's whole-DT transform.
- `scripts/validate-package.py`: fail-closed source, series, patch,
  configuration, kernel, `System.map`, compiled-function audit, package DT,
  and provenance validator.
- `scripts/audit-mt6797-psci-cpu-boot.py`: preserves bounded objdump output
  and performs a control-flow/call audit proving every reachable boot-gate
  return is `-EAGAIN`, no CPU_ON path exists, and the disable gate is a
  call-free constant-false leaf.
- `scripts/test-compiled-gate-auditor.py`: synthetic direct/indirect call,
  branch, privileged-instruction, return-value, and disable-gate mutations.
- `scripts/test-package-validator.py`: series and kernel-policy mutation
  tests that require no AI package or device.
- `scripts/validate-package-reproduction.py`: validates both complete AI
  packages against exact AD, then compares every substantive byte and mode;
  only `generated_utc` and its derived manifest entry may differ.
- `scripts/build-candidate-ai.sh`: deterministic two-pass Android-v0 artifact
  builder for an already-built and validated AI kernel package.
- `scripts/finalize-artifact.py` and `scripts/test-builder-smoke.py`:
  fail-closed pre-manifest/final inventory, mode, publication-order, and
  synthetic package/artifact reproduction gates without VM or device access.
- `scripts/validate-boot.py`: canonical Android-v0 and exact component-lineage
  validator with no pinned AI output checksum.
- `scripts/test-boot-validator.py`: synthetic Android-v0 mutation suite that
  requires no AI artifact.
- `scripts/validate-artifact-reproduction.py`: exact inventory, mode,
  manifest, compiled-audit reproduction, lineage, boot validation, and
  two-tree reproduction gate.
- `scripts/derive-installer.py` and `scripts/test-installer-derivation.py`:
  derive the exact mode-0700 AI guarded installer from the byte-pinned AH
  installer through a reversible exact-count transform. Production exposes no
  calibration override; the test reconstructs the exact AH/AG/AF lineage,
  rejects 43/43 AI cases after the inherited 64/64 AF, 42/42 AG, and 58/58 AH
  suites, and requires one bounded live-GPT `boot2` write with no reboot or slot
  selection.
- `scripts/collect-cycle.sh`, `scripts/collect-runtime.sh`,
  `scripts/validate-runtime.py`, `scripts/test-runtime-validator.py`, and the
  two `test-collect-cycle-*.sh` scripts: cycle-bound, one-shot, read-only USB
  capture and mutation-tested live attribution. The inherited AC USB banner is
  not used as an AI identity; the exact AD config hash, both custom DT enable
  methods, all three gate symbols, CPU masks, 45+5-second stability, and dmesg form the
  live AI discriminator and must be paired with the exact installation
  readback record. Runtime success is only a subgate; it remains pending until
  the independent console and native-reboot subgates are decided. The cycle
  collector, runtime collector, and runtime validator each source-enforce the
  exact 16 MiB Candidate AI full-partition SHA-256 and reject a different
  well-formed caller attestation before accepting evidence. Cycle preflight
  ignores an ordinary default or `GATEWAY` route, exposes only a unique direct
  or scoped `10.15.19.x` route to the exact-interface checks, and rejects
  malformed, ambiguous, or directly mismatched routes.
- `scripts/collect-recovery-evidence.sh`,
  `scripts/validate-recovery-evidence.py`, and their synthetic tests: one
  read-only pre-snapshot/disconnect/reconnect/post-snapshot recovery cycle with
  a 1,200-second minimum deadline, exact known SSH identity, exact recovery
  kernel/root checks, and stale-pstore comparison. A valid same-cycle AI USB
  transcript supplies optional exact attribution; without it, inherited
  Candidate L/AC/AB strings have zero identity weight and the result is
  `INCONCLUSIVE`. The recovery collector and recovery validator enforce the
  same full-partition identity, completing the five-layer source pin.

## Build procedure

1. Run `validate-series-selection.py` and require the exact path, series, and
   patchset identities above. Do not substitute the global series.
2. In the recovery VM, build profile
   `observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-a72-reject-gate`
   first through `./scripts/dev-vm build-kernel`, which intentionally forwards
   no `GEMINI_*_ROOT` override. Build the second copy through `./scripts/dev-vm
   run env ... ./scripts/kernel build` with explicit independent source, build,
   and artifact roots. No new fragment is used: the resolved configuration
   must be byte-exact AD.
3. Run `validate-package.py` separately on both packages, supplying one of the
   two exact accepted AD packages and the exact corrected 0092 patch. Then run
   `validate-package-reproduction.py`; a final-artifact comparison alone is
   insufficient.
4. Run `build-candidate-ai.sh` once for each independently built package,
   supplying exact AD, AH, and AF artifacts and separate external output
   parents.
5. Run `validate-artifact-reproduction.py` on the two outputs. Require the
   complete 20-member trees to be byte- and mode-identical, and record the
   package, kernel, raw-container, compiled-audit, manifest, Android-v0, and LK
   results. Verify an exported tree's exact manifest again on the host.
6. In two independent temporary paths, append exactly 9,396,224 zero bytes to
   the exact 7,380,992-byte raw image, require both 16 MiB results to have
   SHA-256
   `8b7439dda7d50dfd509dd66acb5eeedda86d538f0b4f0fab9b328bcc93ed8b86`,
   verify both tails are entirely zero, and remove both padded files. This
   publishes an identity, not a padded artifact or installer. Derive and
   validate any guarded `boot2` installer separately.

Suggested VM-side invocations use explicit interpreters because this scaffold
does not rely on executable file modes:

```sh
python3 scripts/validate-series-selection.py \
  --repository /path/to/pinned/repository

KERNEL_PROFILE=observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-a72-reject-gate \
  ./scripts/dev-vm build-kernel

./scripts/dev-vm run env \
  KERNEL_PROFILE=observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-a72-reject-gate \
  GEMINI_SOURCE_ROOT=/home/julien.guest/src/candidate-ai-reproduction \
  GEMINI_BUILD_ROOT=/home/julien.guest/build/candidate-ai-reproduction \
  GEMINI_ARTIFACT_ROOT=/home/julien.guest/artifacts/candidate-ai-reproduction \
  ./scripts/kernel build

python3 scripts/validate-package.py \
  --ad-package /path/to/exact-ad-package \
  --candidate-package /path/to/ai-package \
  --patch-0092 /path/to/pinned/repository/patches/v7.1.3/0092-arm64-mediatek-gate-MT6797-A72-PSCI-boot.patch

python3 scripts/validate-package-reproduction.py \
  --first /path/to/first-ai-package \
  --second /path/to/second-ai-package \
  --ad-package /path/to/exact-accepted-ad-package \
  --patch-0092 /path/to/pinned/repository/patches/v7.1.3/0092-arm64-mediatek-gate-MT6797-A72-PSCI-boot.patch

bash scripts/build-candidate-ai.sh \
  --package /path/to/ai-package \
  --ad-package /path/to/exact-ad-package \
  --ad-artifact /path/to/candidate-AD-smp8-final-a1b61d8c \
  --ah-artifact /path/to/candidate-AH-ad-contract-af-kernel-split-e5ba6ee0 \
  --af-artifact /path/to/candidate-AF-a72-observer-initcall-fe43efa8 \
  --output-parent /path/outside/repository
```

## Predeclared result oracle

| Result | Decision |
| --- | --- |
| Exact AI reaches the full AD runtime oracle for 45+5 seconds; CPUs 0--7 advance, CPUs 8--9 stay offline, the text console is visibly working, and native reboot works | `PASS`: the corrected reject gate is compatible with the proven eight-A53 baseline. A later, separate test may exercise one rejecting CPU8 request under its own isolation/watchdog contract. |
| Exact AI reaches USB or pstore but faults, stalls, changes CPU masks, resets, or presents an attributable grey/no-text console | `FAIL`: remove/split the reject-gate kernel implementation before any regulator, reset, observer, or active-A72 work. |
| Series, config, DT, installed hash, or runtime identity differs | `INVALID`: correct lineage; do not interpret hardware behavior. |
| Owner-selected AI produces no exact AI USB/pstore identity | `INCONCLUSIVE`: add an earlier independent observation path; do not repeat the identical artifact solely for another screen observation. |

## Observations

Two complete kernel packages were built in separate roots of the AArch64
recovery VM. Their `generated_utc` values are
`2026-07-22T17:18:49Z` and `2026-07-22T18:21:10Z`. The corresponding
`SHA256SUMS` files have SHA-256
`97b9741a4c99ae2f83e19eb2b47640dacb702b73de5fa4dfcfa85404c3685df6`
and
`44eb5f57395ce7282fbf4dc98af19a507840954438a384369f8edc5d308a3bc5`;
the corresponding `provenance/build.json` files have SHA-256
`76e44e539ca8bc3ec03eb378bc02001b5d8312a357a94b8a919f43972682d818`
and
`6ed6f855c7b422e1646335763e50580618ae6528a49d982d7be74c718b963ab7`.
Both exact package manifests verify.

The package-reproduction validator accepted 225 members with identical
substantive payload bytes and modes, exact 0775 directory inventory and modes,
and identical normalized build provenance. The only permitted difference is
`generated_utc` and its derived `provenance/build.json` manifest entry. Both
packages contain `Image` SHA-256
`fb2c02601a07b49781b97ef9d39b79218db1c158ce1547a2ea53df7fb1e51fe2`,
`Image.gz` SHA-256
`b87984a570567ef47f151024612889f7d5d49b938c10bd08f0aecfea47b481a9`,
`System.map` SHA-256
`622945b38e025db7ee7719f2fa3132e17f8ad0158651e2f77e57918a76ac384d`,
exact AD configuration SHA-256
`32dd13a6704e5fa591236ba114d43e8e7e1aeb3eb123d9d4f124b5f551301d46`,
Gemini package DTB SHA-256
`510669e70cd39df3c0e1a1b4c806c0eeaa8e0b0fe02e037ee1bf405d39498af8`,
and compiled-gate audit SHA-256
`67519ff0a82376e2d0628f7061af474b0df6427c0f54878717a6c6b1d672a525`.
The compiled lifecycle gate was audited independently in both packages.

The build retained the known pre-existing `ranges_format` diagnostic for the
unrelated MT6797 `usb@11271000` empty `ranges` property with differing cell
counts; it is not introduced by corrected patch 0092. All current host-only
negative suites pass: 32 package-policy, 61 compiled-gate, 21 builder and
finalization, 18 Android-v0 validator, 30 runtime-attribution, and 26 recovery
evidence mutations were rejected. The mocked no-interface, one-shot cycle, and
recovery-collector shell contracts also pass without device access. See the
[package-reproduction record](results/kernel-package-reproduction-ai-20260722.txt).

Two independent Android-v0 constructions then produced byte- and
mode-identical 20-member artifact trees named
`candidate-AI-a72-reject-gate-1ecfc787`. The 7,380,992-byte raw boot image is
SHA-256
`1ecfc787fec2f5dc11c5b7d30eb4f11d34b0496e57daf42adea567f010282309`;
both artifact manifests are SHA-256
`b8c2953dd07e2a84a05e99f7bd0a981cbe593e928ba7507f16691279d82fa8cc`.
Both artifacts passed canonical Android-v0 validation, the retained-LK gate,
exact package binding, and the compiled fail-closed lifecycle audit. Their
payloads include exact `Image.gz`
`b87984a570567ef47f151024612889f7d5d49b938c10bd08f0aecfea47b481a9`,
`System.map`
`622945b38e025db7ee7719f2fa3132e17f8ad0158651e2f77e57918a76ac384d`,
AD configuration
`32dd13a6704e5fa591236ba114d43e8e7e1aeb3eb123d9d4f124b5f551301d46`,
AH final DT
`27175804f052259c86ed068d2c318e83d5b2090f4aa705e063f9c9b33a4ca845`,
AD initramfs
`166c0f03ab9ca1062f36d55132141b4be5f06187380d17ab2f6e9e7db75d1dd3`,
and compiled-gate audit
`67519ff0a82376e2d0628f7061af474b0df6427c0f54878717a6c6b1d672a525`.
The exported first artifact's complete manifest also verifies on the host.

A separate ephemeral calibration appended a 9,396,224-byte all-zero tail to
the raw image twice. Both independent 16,777,216-byte results had SHA-256
`8b7439dda7d50dfd509dd66acb5eeedda86d538f0b4f0fab9b328bcc93ed8b86`;
both zero tails were independently verified. The temporary padded files were
then removed and were never published or transferred to a device. See the
[artifact-reproduction record](results/artifact-reproduction-ai-20260722.txt).

A subsequent host-only preflight stopped before any device reboot because
`route -n get 10.15.19.82` resolved through the Mac's ordinary default route:
destination `default`, gateway `192.168.1.1`, interface `en0`, with the
`GATEWAY` flag. The original watcher treated its sole `interface:` line as a
Gemini-specific route and aborted. That aborted attempt remains preserved as
negative host evidence. The corrected parser ignores default/gateway routes
while retaining unique direct/scoped `10.15.19.x` interfaces for exact-link
comparison. A mocked reproduction accepts the observed default route as two
clean initial absences with zero collector invocations; a direct scoped route
on the wrong interface still fails closed. No device access, reboot, or write
was used for this correction.

The earlier ShellCheck findings are closed. Both SC2100 literal-state
assignments are quoted, and the intentional SC2016 remote-shell expansion has
a narrow documented suppression. All six Python host tests, all three
mocked-network shell host tests, `bash -n` for all seven shell scripts, AST
parsing for all 17 Python scripts, and recovery-VM ShellCheck for all seven
shell scripts pass. See the
[runtime/recovery pinning record](results/runtime-recovery-pinning-ai-20260722.txt).

The guarded installer was then derived from exact Candidate AH installer
SHA-256
`01768f0decaf621eebfcfbbf02eba64d15f3595207a1ce3c8ea1918f17656c91`.
The exact 34,462-byte mode-0700 production installer has SHA-256
`8d9d0ac258fdb031e840b2042c7abc1fc1fdf01cf6c6893bc24c234b6d9054f6`.
It pins the installed AH predecessor full-partition SHA-256
`f107a3e7483c02cb4b2540d185ef2a5fb1f77e4a0acc7b66fce16e37641f5012`
and exact AI padded SHA-256
`8b7439dda7d50dfd509dd66acb5eeedda86d538f0b4f0fab9b328bcc93ed8b86`.
The host suite passed `bash -n`, inherited 64/64 AF, 42/42 AG, and 58/58 AH
mutation rejections, and 43/43 AI rejections; recovery-VM ShellCheck passed.
An independent read-only fail-closed audit also passed. The derived contract
has one bounded live-GPT `boot2` write, exact backup/sync/flush/full-readback
gates, and no reboot or slot selection. See the
[installer-validation record](results/installer-validation-ai-20260722.txt).

The guarded installation then resolved exact live-GPT logical `boot2` as
`/dev/mmcblk0p30` (partition 30, 16,777,216 bytes), separate from active root
`/dev/mmcblk0p29`. Boot ID
`4dfa7e87-d7c7-416f-8c32-7271662d89bd` remained unchanged, and the stable
power sample was `0|1|1|Full|100|Good`. The private mode-0600 backup matched
the required AH predecessor SHA-256
`f107a3e7483c02cb4b2540d185ef2a5fb1f77e4a0acc7b66fce16e37641f5012`.
The remote post-flush checksum and full 16,777,216-byte local readback both
matched exact AI padded SHA-256
`8b7439dda7d50dfd509dd66acb5eeedda86d538f0b4f0fab9b328bcc93ed8b86`.
The private mode-0700 evidence directory's verified manifest is SHA-256
`e38696faaa11fe6ee78649c3af5edf183da7a48ca4eac5454fab3c2849faf25e`;
its deployment summary is SHA-256
`edb51a0dd139897c7b64a21a725db1ff7e4419edb85b12960611a1a813fb583a`.
Remote staging was removed. The installer neither rebooted nor selected a
slot. See the
[guarded installation record](results/boot2-install-candidate-ai-20260722.txt).

Candidate AI attempt 1 then passed the predeclared eight-A53 runtime baseline
on the named unit. The owner selected `boot2`, observed a working console, and
reported eight processors in `/proc/cpuinfo`. The visible `Candidate AB`
console label, `Candidate AC` USB banner, and observability-L release string
are expected inherited initramfs/baseline labels and have no independent AI
identity weight. Exact AI attribution instead combines the installed
full-partition hash above with configuration SHA-256
`32dd13a6704e5fa591236ba114d43e8e7e1aeb3eb123d9d4f124b5f551301d46`,
both `mediatek,mt6797-psci` CPU enable methods, and one live instance of each
of the boot-gate, disable-gate, and operations symbols.

The exact USB runtime had boot ID
`0e40af1b-e5b9-45ab-b554-c559a8283577` and remained attributable from
147.26 through 154.26 seconds of uptime. It reported CPUs 0--9 possible and
present, CPUs 0--7 online, CPUs 8--9 offline, and `nproc=8`; accounting for
every online CPU advanced over the five-second sample. The final masks were
unchanged. Because `maxcpus=8` omitted both A72 online controls, neither
CPU8 nor CPU9 was requested and the corrected rejection path was not
exercised. Eight online CPUs is therefore the expected AI result, not a
failure to enable the A72 pair.

A fresh-boot-ID-gated bare `reboot` then used the inherited absolute BusyBox
wrapper. The exact USB endpoint disappeared. Retained pstore places the
inherited AB request marker at 314.277066 seconds, watchdog-driver shutdown at
314.293250 seconds, and `reboot: Restarting system` at 314.302632 seconds. The
25.566 ms request-line-to-final-log interval is not command-to-reset or LK
latency. Gemian returned on `/dev/mmcblk0p29` with boot ID
`9937f1b6-8760-4a9f-8023-f46c15c2e43a`, changed from the prior known
recovery boot ID, and a read-only full `boot2` hash still matched exact AI.
No userspace watchdog, countdown, or post-cycle device write owned that
result.

The custom pre-cycle recovery observer had expired before attributable AI
runtime appeared. This pass therefore rests on exact live runtime, the gated
request, USB disappearance, and post-return pstore/readback; it is not a
validated two-snapshot recovery-collector cycle. See the
[attempt-1 runtime record](results/runtime-candidate-ai-attempt-1-20260722.txt).
CPU8/CPU9 gate execution and all Cortex-A72 power/online support remain
pending. The earlier package/artifact builds, ephemeral padding checks,
installer static validation, installation identity/readback, and
evidence-tooling checks remain build or provenance evidence rather than
runtime hardware-support evidence.

## Conclusion

`PASS for the isolated reject-gate change on the eight-A53 baseline`:
Candidate AI's corrected 0092-only package and Android-v0 artifact reproduce,
were installed through the guarded logical-`boot2` path, and remained exact
after the hardware cycle. Exact attributed runtime reached a working console
and USB service with CPU0--7 online and advancing, stayed alive beyond 154
seconds, and completed one native kernel restart back to Gemian with retained
shutdown/restart evidence and a changed boot ID. The inherited AB/AC labels do
not rename the artifact and are not used for attribution. This result accepts
the isolated kernel change as compatible with the proven eight-A53 baseline.
It does not exercise the fail-closed method: CPU8 and CPU9 were never
requested, so reject behavior, A72 power sequencing, and A72 online operation
all remain pending separate tests.
