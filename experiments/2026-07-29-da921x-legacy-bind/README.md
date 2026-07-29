# DA921x legacy identification-only integration

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-29-da921x-legacy-bind` |
| Status | `completed` |
| Subsystem | regulator, I2C, arm64 Device Tree |
| Device variant | Planet Computers Gemini PDA, named development unit |
| Date(s) | 2026-07-29 |
| Investigator(s) | Julien Etienne |
| Tracking issue | Roadmap Gate 2 |

## Question or hypothesis

Can the Gate 1 legacy DA921x contract be represented by a schema, a
Kconfig-isolated identification driver, and a Gemini board node such that
probe can issue only the captured fourteen-read transcript and cannot expose
a regulator provider or A72 consumer?

The normative design is
[`../2026-07-29-da921x-legacy-driver-contract/DESIGN.md`](../2026-07-29-da921x-legacy-driver-contract/DESIGN.md).

## Provenance and environment

- Kernel: pinned Linux 7.1.3 from `kernel/manifest.json`
- Canonical patches: `0123` binding, `0124` driver, `0125` board description
- Profile: `da921x-legacy-bind`
- Compiler: GCC 13.3.0; GNU ld 2.42
- Source SHA-256: `be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc`
- Patchset SHA-256: `815f9d3017b07bb2816df14a194022598b637c50642f301f89a2c39d768d14a1`
- Configuration SHA-256: `03c01ee708434809b9801cc9069040a972668bbebc1eb9f0b7cb4ddef1a95327`
- Detailed artifact identities: [`results/offline-validation.json`](results/offline-validation.json)
- Boot path: none; Gate 2 is offline-only

The patches use the repository owner's configured author identity but carry no
`Signed-off-by`. They are intentionally not submission-ready until the actual
author reviews the final commits and can truthfully make the DCO certification.

## Safety assessment

This gate performs no device access, boot, partition read, or partition write.
The driver has no write helper, regmap, PAGE_CON access, provider registration,
IRQ, PM, remove, or shutdown callback. The board node has no regulator outputs,
supplies, or A72 consumer. Static validation rejects any probe-time data write
or change to the fixed address/transcript contract before an artifact can be
considered.

## Associated code

- `scripts/validate-static.py`: patch/profile/manifest contract validator and
  negative mutation tests
- Gate 1 `scripts/validate-contract.py`: normative design-data validator
- `configs/gemini-da921x-legacy-bind.fragment`: isolated experiment policy

## Procedure

1. Validate the Gate 1 machine-readable contract.
2. Run `scripts/validate-static.py --self-test`.
3. Audit every manifest-selected patch series as a canonical-order
   subsequence.
4. Apply the canonical series to the pinned source.
5. Run binding-schema, DT, checkpatch, and focused compile checks.
6. Assemble the profile twice from the same verified source state in separate
   out-of-tree build directories, compare substantive inputs and packaged
   outputs, then remove the temporary build directories.

## Observations

- The Gate 1 validator reports 14 probe transactions, zero register-data
  writes, zero lifecycle transactions, and no provider.
- `scripts/validate-static.py --self-test` passes and rejects six unsafe
  mutations: a data write, retrying transfer, two-byte pointer write, wrong
  page2 address, provider-bearing board node, and wrong binding tuple.
- The manifest-series audit checks 30 profiles successfully.
- Focused `dt_binding_check` and Gemini `CHECK_DTBS=y` validation pass. The DT
  compile repeats only the existing MT6797 USB `ranges_format` warnings.
- Checkpatch reports zero code checks. It reports the intentionally missing
  `Signed-off-by`, long commit-body lines, and a MAINTAINERS consideration for
  the two new files; these remain submission-preparation work.
- Two builds used separate `gate2-a` and `gate2-b` out-of-tree directories and
  the same verified prepared source. Both artifact packages pass
  `scripts/validate-kernel-artifact`.
- Both builds produced byte-identical `Image`, `Image.gz`, `kernel.config`,
  `System.map`, and `mt6797-gemini-pda.dtb`. Their provenance differs only in
  `generated_utc`.
- No device, boot partition, storage device, or hardware bus was accessed.

## Analysis

The binding, board description, and compiled driver agree on the direct
primary/page2 topology. The driver has one direct combined-transfer call site
under a single root-adapter lock and no write, regmap, provider, IRQ, PM,
remove, or shutdown path. The negative mutation tests make the zero-write
claim executable rather than documentary.

The two independent builds close the offline reproducibility question. They do
not establish that the device will match, bind, or unbind successfully, nor do
they establish regulator-provider or A72 behavior.

## Conclusion

Confirmed for the pinned Linux 7.1.3 inputs: the isolated identification-only
stack is reproducibly buildable and its pre-boot contract permits only the
fixed fourteen-read probe. Roadmap Gate 2 is complete. This is not hardware
support evidence and no regulator provider is exposed.

## Follow-up

Roadmap Gate 3 is the first device boot. Before that boot, record the exact
kernel/DT/config hypothesis, unique probe-success and probe-failure evidence,
and decision-changing outcomes. Do not add an A72 consumer or regulator
provider in that experiment.
