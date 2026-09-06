# MT6797 EMI routing and overlap: bounded public-source sweep

## Record

- Status: **inconclusive**, public-source investigation accepted by Sol Medium
  review at `2026-09-06T08:08:15Z`.
- Date: 2026-09-06. Subsystem: EMI MPU / CONSYS resource ownership.
- Target variant: Gemini PDA / MT6797; no device observed in this item.
- Investigator: Astra Medium specialist; Sol Medium review and integration
  belong to the parent owner under [WORK_ITEM.md](WORK_ITEM.md).
- Frozen repository parent: `cf10a2f4a062c13b92b3a5a21e6a818db927d1b8`.
  [inputs.json](inputs.json) pins the three pre-existing sanitized records by
  whole-file SHA-256 and size. No private input was reopened.

## Question and safety boundary

Can exact public primary sources establish the AP or CONSYS effective EMI
domain, join WLAN traffic to that master/domain, or specify MT6797 MPU overlap
arbitration? This item is read-only public inspection and offline metadata
verification. It performs no device, VM, firmware, MMIO, SMC, radio, build,
partition or deployment operation. No source code is copied into the repository.

## Procedure and exact attempt inventory

[search-attempts.json](search-attempts.json) records each batch before its first
request, with exact query/locator, allowed source class, UTC times, all returned
hit URLs and dispositions, and response identities. Search snippets are discovery
only. The search service does not expose internal transport; the ledger makes
that limitation explicit. Direct file fetches disabled redirects and both
returned HTTP 200 without redirects.

| Batch | Branch | Requests | Result |
| --- | --- | ---: | --- |
| A1 | Routing assignment | 4 searches | Two hits in the first query, none in the other three; no admissible assignment-register lead |
| B1 | Overlap arbitration | 4 searches | 5, 9, 7 and 0 hits respectively; one immutable newer-SoC file-pair lead selected |
| B2 | Overlap arbitration | 2 file fetches | Two MT8192 TF-A files inspected; no explicit MT6797 compatible rule |

Total: **3 attempts, 10 requests, 2 newly fetched primary files**. Branch A
stopped after A1: the contract permits A2 to follow exact leads, but A1 supplied
none. Branch B reached its two-attempt cap. Unused request capacity is not a
reason to broaden the search. Search absence does not establish that an exact
source or assignment register does not exist.

## Observations and source rights

The only newly fetched corpus is the TF-A revision
`24ca0fa6ac4afa509a92e3a79bc855761619b6e5`, specifically its
[MT8192 EMI C file](https://git.trustedfirmware.org/plugins/gitiles/TF-A/trusted-firmware-a.git/+/24ca0fa6ac4afa509a92e3a79bc855761619b6e5/plat/mediatek/mt8192/drivers/emi_mpu/emi_mpu.c)
and
[header](https://git.trustedfirmware.org/plugins/gitiles/TF-A/trusted-firmware-a.git/+/24ca0fa6ac4afa509a92e3a79bc855761619b6e5/plat/mediatek/mt8192/drivers/emi_mpu/emi_mpu.h).
The whole decoded files are 3,146 and 3,371 bytes. Their hashes, source locators,
revision, fetch request and rights are frozen in `inputs.json`.

Both files carry BSD-3-Clause notices at lines 1–5. Inspection used process
memory only; no source file was written to disk, mirrored or retained in Git.
Repository additions are independently written metadata, prose and verifier
code. Discovery logs and unrelated history hits were not promoted to corpus.

The C setter writes a selected region's start/end/permission registers, and its
initializer sets region 1 inside the span of region 2. The header defines 16
domains, 32 regions and permission packing. Neither file states an explicit
multiple-match winner rule or an MT6797 compatibility contract. These are
observations about this exact MT8192 source, not MT6797 hardware facts.

## Analysis and verdicts

[verdicts.json](verdicts.json) separates observation from inference:

- AP routing, generic CONSYS routing and WLAN-routing applicability remain
  independently **unresolved**; no domain is selected.
- A hypothetical generic CONSYS-to-D2 chain alone cannot establish WLAN
  applicability. That requires an attributable WLAN fetch/data transaction
  joined to the same master and effective assignment/override chain.
- Overlap `priority_rule_established` is false. Setter call order, region
  numbering and successful setter returns do not establish hardware priority.
- `active_region_applicability_established` is separately false. Public source
  cannot establish the enabled/applicable regions at the WLAN-loading epoch.
  The composite overlap verdict must therefore remain unresolved even if a
  future exact priority rule is found.
- `policy_selection_allowed`, `device_action_allowed`, `hardware_support_claim`
  and `source_copy_allowed` are all false.

This sweep strengthens the audit trail, not the hardware claim. It found no
contradicting exact MT6797 semantics and cannot narrow the correct domain or
winning region. The nearby generation is explicitly excluded as proof.

## Offline checks actually run

Run from the repository root:

```sh
python3 experiments/2026-09-06-mt6797-emi-routing-source-sweep/verify.py
python3 -O experiments/2026-09-06-mt6797-emi-routing-source-sweep/verify.py
```

Result after integration repair 1: PASS under normal and optimized Python,
3 attempts / 10 requests / 2 primary files and **33 in-memory refusals** plus
one positive structural control. Fixtures cover co-mutated path/hash substitutions, missing/extra
corpus, independent routing promotions, WLAN promotion from generic CONSYS-D2
only, priority/active-region/compatibility promotions, rights or authority
expansion, fabricated attempts, undeclared queries, removed hits, reordered
requests and unknown citations. All six AP/CONSYS/WLAN predicate booleans have
separate unresolved-promotion and non-boolean refusal fixtures. The verifier
checks exact routing key sets and unresolved domain/predicate shape.

Production validation uses independent frozen record digests plus
semantic/count/chronology/citation checks and rehashes the three retained
sanitized inputs. In-memory fixtures bypass only the outer whole-record digest
gate and optional retained-file reads; independent corpus/retained identities,
rights and semantic guards still run. The generic CONSYS-to-D2 positive control
passes the structural dependency checker with WLAN unresolved; promoting WLAN
without WLAN attribution then fails full semantic validation with the exact
`WLAN prerequisite: complete CONSYS chain plus attributable WLAN fetch/data
joined to exact master/domain` reason, not a digest or CONSYS-promotion reason.
The control does not change or admit the frozen evidence record.

The verifier has no network access path. It cannot independently attest
remote source truth or defend against a reviewer changing its own constants.

Python syntax compilation without bytecode output, local Markdown-link checks,
new-file whitespace checks, verifier MIT SPDX check and `git diff --check` also
passed. No shell changed,
so bash/ShellCheck are not applicable. No kernel/build/device test was run; none
is implied by these metadata checks.

## Bounded handoff / next discriminator

Evidence: exact immutable newer-SoC source pair, complete predeclared attempt
ledger, frozen unresolved predicates and passing refusal checks. Attempts:
routing 1/2 (no eligible follow-up lead), overlap 2/2 (cap reached). Unresolved
question: exact MT6797 transaction-to-domain assignment and multiple-match rule.

The next discriminator is an attributable MT6797 assignment/bridge-security
register contract and a WLAN transaction joined to that exact master, plus an
explicit MT6797 arbitration rule with applicability conditions. An independent,
separately admitted observation of active regions at the WLAN-loading epoch is
still required after any source-only rule resolution. This is not a proposed
MMIO probe, fault trigger or permission to execute one. No adjacent work starts
here; [the roadmap](../../docs/ROADMAP.md) remains the sole ordered-work owner.
