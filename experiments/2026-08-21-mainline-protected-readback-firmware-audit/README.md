# Protected readback firmware audit

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-21-mainline-protected-readback-firmware-audit` |
| Status | `completed` |
| Subsystem | MT6797 MCUMIXED/CSPM and secure BigiDVFS readback |
| Device variant | Named Planet Gemini PDA unit |
| Date | 2026-08-21 America/New_York |
| Investigator | Codex with device owner |

## Question or hypothesis

Do canonical patches `0197` and `0198` already match the named Gemini's exact
firmware and recovered arbitration contracts closely enough to justify a first
runtime enablement of both read-only transports?

## Provenance and environment

- Repository audit commit parent:
  `741e1052f143b624b9a1200ead426887a921aa7a`.
- Clock transport patch SHA-256:
  `bd6389ec6c63fa587504fff95980d3deefb1c9162a7151eb51cf0b544e2496de`.
- BigiDVFS transport patch SHA-256:
  `e417a5a0006dcbf0325b035352a99c380d11d88f370c20fe029b2dffb2d705bd`.
- The exact live `tee1` and `tee2` partition identities were already captured
  read-only and both match the privately analyzed 2019 payload at SHA-256
  `2cd154f332ee72edb6dee431a68eb5f8b98b4dc05ee14e56591cfbffcf81a9b3`.
- Public protocol source is pinned to Gemian repository commit
  `8cfe6596a503612e3332d9c26e292a19525a7f07`; exact named-firmware behavior is
  pinned by the retained private payload analysis, not inferred from that
  source alone.

The exact input identities and cross-checks are in
[`contract.json`](contract.json) and the bounded result is in
[`results/audit-20260821.txt`](results/audit-20260821.txt).

## Safety assessment

This audit was entirely offline and read-only. It used already sanitized
results and canonical patch text. It did not contact the Gemini, read a live
partition, call secure firmware, acquire a hardware semaphore, construct a
boot image, write `boot2`, request a CPU, or create a new backup.

## Associated code

- [`scripts/validate.py`](scripts/validate.py) pins every referenced file and
  checks the decision-bearing transport and firmware-contract tokens.
- No kernel source tree or private firmware image is stored here.

Run from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 \
  experiments/2026-08-21-mainline-protected-readback-firmware-audit/scripts/validate.py
```

## Procedure

1. Pin the canonical `0197` and `0198` bytes.
2. Pin the prior live TEE-slot identity and exact private-payload ABI result.
3. Compare every hardware access, bound, address, return rule, and ordering
   rule in each transport with the named-firmware and public-owner evidence.
4. Reject combined runtime enablement if either transport omits a required
   protocol step or if an individual sample can publish partial state.

## Observations

The secure BigiDVFS transport uses only AArch64 SMC FID `0xc200035f`, exactly
the named payload's read-only `REG_READ` handler. Its four addresses are the
recovered B-PLL PCW, enable/post-divider, SRAM selector, and control words, all
inside the handler's `0x10220000/0xffffc000` window. It never references
`REG_WRITE` (`0xc200035e`) or the unimplemented getter FIDs. The handler returns
valid register words zero-extended and errors sign-extended, matching the
driver's upper-32-bit rejection rule.

That establishes ABI compatibility, but not yet an authoritative snapshot.
Patch `0198` performs four separate SMC calls and writes directly into the
caller's record. It neither clears the record before the first call nor takes
two complete matching samples. A transition or an intermediate error can
therefore leave a mixed or partial record, even though a caller that respects
the negative return must not consume it.

The protected-clock transport matches the recovered normal-world master port
at CSPM `+0x440`, its write-one acquisition/release protocol, 10 us poll, 200
iteration bound, keyed internal clock value, local IRQ exclusion, spinlock,
and LL/L/CCI register windows. The named TEE's `+0x448` access is a distinct
secure master port and confirms that firmware competes for the same protected
clock domain; it does not replace Linux's `+0x440` port.

Patch `0197` omits one recovered ordering rule: after acquiring the semaphore,
the historical owner waits 200 ns before the first MCUMIXED access. The driver
starts reading `ARMPLLDIV_MUXSEL` immediately. Its 10 us delays occur only
while polling failed semaphore acquisitions and do not satisfy the successful
acquire-to-first-read boundary.

## Analysis

The BigiDVFS transport's firmware identity is confirmed for the named unit,
but its publication semantics need hardening and hardware-free fault/stability
tests before a device run. The clock transport is not protocol-exact because
the required 200 ns settle is absent. This is an attributable implementation
gap, not a kernel-compile or firmware-identity uncertainty.

The existing compile-only profile remains useful: it proves both objects link
and the nodes remain disabled. It cannot validate the omitted timing or the
four-call BigiDVFS observation boundary.

## Conclusion

The hypothesis is **rejected** for combined runtime enablement of canonical
patches `0197` and `0198` as written.

- BigiDVFS named-firmware ABI: `confirmed`.
- BigiDVFS stable all-or-zero snapshot: `unproven`.
- Protected-clock resource/semaphore identity: `confirmed`.
- Protected-clock successful-acquire ordering: `rejected`; the 200 ns settle
  is missing.
- CPU8/CPU9 admission: remains closed.

No hardware-support claim follows from this audit.

## Follow-up

The ordered remediation is owned by
[`docs/ROADMAP.md`](../../docs/ROADMAP.md): repair the clock settle boundary,
make both transports publish all-zero on failure, add a stable BigiDVFS sample
rule and focused hardware-free tests, then build one read-only firmware
validation candidate before composing the sources under the transition/hotplug
owner.
