# Independent review: SPM key, CONN order and retained attribution

## Record and decision

Completed on 2026-09-05. **Accept the public-source findings and the limits of
the retained-analysis handoff; no concrete correction requested.** This is a
source and evidence-scope review. It is not independent repetition of the
private binary analysis, a current-boot observation or permission to write SPM.

Reviewed exact published inputs:

- [`SPM_KEY_ORDER.md`](https://github.com/ixoo/gemini-pda-mainline/blob/cf0d9f17b88423c432bc0ec32b845ef8a7d866bc/experiments/2026-09-05-mt6797-wifi-contract/SPM_KEY_ORDER.md),
  source ledger and receipt at `cf0d9f17b88423c432bc0ec32b845ef8a7d866bc`.
- [`RETAINED_SPM_ATTRIBUTION.md`](https://github.com/ixoo/gemini-pda-mainline/blob/850b05698d82c97655cba9552a2eb38d7c36d9ff/experiments/2026-09-05-mt6797-wifi-contract/RETAINED_SPM_ATTRIBUTION.md)
  and receipt at `850b05698d82c97655cba9552a2eb38d7c36d9ff`.

[Review receipt](results.json) records document identities and the exact scope.
The author's checkout was read only; no author's file was edited.

## Public-source checks

All 12 entries in the existing source ledger were independently fetched from
their exact public revision, with a 256 KiB response ceiling and 15-second
socket timeout, and matched both byte count and SHA-256. Sources were inspected
in memory; no vendor source tree or implementation was retained. The four
revisions are Planet `c5b0be85017ad0c599725e8273842efdbecdd88a`, Gemian
`d388d350cb2dda8f23b99be6fa5db9628896e87f`, upstream Linux
`4d7d9486c04d917265f64c55bd23b2cc4fe7749c`, and stable Linux
`199c9959d3a9b53f346c221757fc7ac507fbac50`.

The selected source supports these claims:

| Claim | Independent check |
| --- | --- |
| Shared SPM enable address/key | Register definitions place `POWERON_CONFIG_EN` at SPM `+0`, bit 0 and high-half project code `0xb16`; this gives the cited keyed enable value |
| Vendor initialization reaches the write | `spm_register_init` writes under `__spm_lock`; `spm_module_init` calls it; the PM initializer has an active call after the disabled legacy block |
| More than one vendor path | The SPM helper writes under its lock; selected OF WMT writes after external reset and before the CCF enable call; the actual CCF CONN function writes before choosing ON/OFF |
| Repeated request is not necessarily a transition | The CCF wrapper can return at its already-on state check before the transition callback; that lock path differs from the SPM helper's lock |
| Selected CONN order | Planet and Gemian functions agree: OFF protection, isolation, clock-disable, reset, separate primary/secondary clears and dual-ACK polling; ON clears clock-disable/isolation then releases reset/protection after ACKs |
| Legacy upstream difference | OFF performs SRAM handling, isolation, reset, then clock-disable; ON retains a SRAM helper access before releasing protection |
| Scoped upstream absence | The audited legacy/newer providers and MT6797 clock source contain no corresponding keyed shared-enable initialization; both legacy provider files match byte-for-byte |

Historical local patches 0047 and 0050 were also read: their MFG SRAM/domain
and preclock changes add no shared key initialization. The inactive WMT fallback
has its different reset/isolation/clock order and combined request clear; it is
not interchangeable with the selected CCF branch. Nothing here validates
unbounded polling, imports that fallback or establishes hardware equivalence
between the two OFF orders.

The public CCF and SPM lock paths are the evidence for separate normal-world
locking. Multiple mappings alone would not prove absence of a common lock,
and this review does not extend that claim to every firmware writer.

## Retained-report scope checks

Used the existing sanitized exact-boot audit from July 26, the August 6
TEE-owner disassembly report, and the new retained-attribution receipt. No raw
binary, disassembly, private provenance file or RE session was requested or
opened. The new report's private identity/mapping and individual store traces
are accepted as its author's recorded method; they were **not independently
reverified** here.

The reported boot-to-kernel-field-to-Image-to-ELF chain names the retained
primary-boot image, avoiding substitution of a filesystem kernel package.
The TEE extent `[0x1000,0x17e00)` and address bias `0xff3c0` agree with the
older sanitized report's inclusive endpoint. Its five CSPM keyed stores also
agree with the earlier reported count. Neither comparison establishes present
execution or exhaustive firmware coverage.

The new report distinguishes five normal-world SPM store sites from five secure
CSPM store sites. Its address distinction is essential: CSPM `0x11015000 + 0`
is not SPM `0x10006000 + 0`, and the older A72 SPM `+0x218` reference is MP2
control, not the shared enable register. The CONN ordering statement is scoped
to static control flow and mappings, not a completed transition receipt.

The parameterized secure SPM helper defeats a literal-only absence argument.
Its reported direct-call bounds give `0x210/0x214` for cluster indices 0/1 and
`0x220..0x23c` for CPU indices 0..7. Those finite offsets exclude `+0` only for
those traced calls. The report explicitly leaves indirect entries, computed
aliases, other constant constructions and other components open. Its corrected
MOVZ-aware search supersedes the incomplete preliminary query instead of
turning that preliminary zero into a negative finding.

## Acceptance limits and handoff

Treat “kernel enables shared SPM control” as the report's static attribution:
it contains those writes. It does not mean they ran in this boot, that LK never
writes the register, that enable state survives suspend, or that a new normal-
world owner can write or clear it concurrently. Same-value stores do not prove
universal idempotence. The existing refusal to infer a save/restore policy,
sole global owner or safe detach sequence is retained.

No additional source fixture is warranted for this document-only scope review.
No private RE, device, firmware execution, kernel build, backend or new hardware
observation occurred. No provider flag, global key write, CONN selection or
ordered roadmap change is introduced. The source order is suitable evidence
for a separately reviewed future per-domain capability; it does not admit that
implementation or settle its prerequisite and lifetime requirements.

Common repository checks passed for the two review files, with 190 profiles and
unchanged grandfathered metadata debt (37). JSON, local links, sensitive-data
exclusions and diff checks passed. No kernel/checkpatch/DT/hardware tests ran.
