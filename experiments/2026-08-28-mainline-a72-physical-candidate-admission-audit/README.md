# Mainline CPU8 physical-candidate admission audit

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-28-mainline-a72-physical-candidate-admission-audit` |
| Status | `completed` source audit; direct late caller rejected; derived admission compositor selected |
| Subsystem | MT6797 CPU8 A34/A36 membership admission and physical binder entry |
| Device variant | Planet Gemini PDA, named development unit |
| Date(s) | 2026-08-28 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 7, first decision-bearing physical CPU8 candidate |

## Question or hypothesis

Can the hardware-free binder be turned into a safe physical candidate by only
enabling its Device Tree node and adding one late `add_cpu(8)` caller, or does
the exact full-series source still lack a production current-boot admission
edge?

The falsifiable direct-caller hypothesis requires the existing production APIs
to publish A34 bootstrap, mint and bind the exact A36 transaction, publish
P17/P18, and enter `add_cpu(8)` in one task without inventing evidence or
violating the retained-ledger and watchdog order.

## Provenance and environment

- Repository revision: `28adce23c56944368689bf5062fba0828d3a02d2`.
- Canonical series: 398 entries through patch `0406`.
- Exact series SHA-256:
  `3658f5ef79dd75fe079cdce4defca982778c94d033c9854e0ac4645f5c3eb4aa`.
- Exact Buildbox prepared-source state:
  `c0fd471b2fbc291a0793ba093fe95acbf972685031bde67cad7c89833292694c`.
- Exact prepared-source integrity:
  `2b1b2e9ba54fc0361cc3e6bdfba3478059c7750ac715e0b5d8d8a8b2e38246b1`.
- The source was inspected read-only on Buildbox. No source tree was copied.
- No VM kernel build or fallback was used.

Exact file identities and call-path findings are in the
[source audit](results/source-admission-audit-20260828.txt).

The I/O-free [admission model](scripts/admission_model.py) and its
[exhaustive runner](scripts/test_admission_model.py) freeze the selected
one-shot ordering and failure behavior before any kernel implementation.
The source-pinned [Buildbox generator](scripts/generate-on-buildbox),
[deterministic edits](scripts/source_edits.py), semantic
[source validator](scripts/validate_source.py), and five-case
[KUnit source](kernel/mt6797-a72-derived-admission-test.c) prepare two logical
patches. Their local syntax, ShellCheck, model, and definition checks pass in
the [local validation receipt](results/local-definition-validation-20260828.txt).
They have not yet been executed against the prepared kernel source: repository
policy correctly defers that Buildbox step until this exact work is signed,
pushed, and clean.

## Safety assessment

This audit is hardware-free. It made no kernel build, package, boot image,
device connection, retained-RAM write, watchdog takeover, regulator or secure
call, CPU request, partition write, reboot, or shutdown.

The direct-caller design is rejected before a build because it would have to
assert recovery ownership that cannot yet exist. The existing binder remains
default-off, no binder Device Tree node is enabled, and no production CPU8
request exists.

## Observations

The exact full-series source has only the definitions, and no external
production callers, for:

- `mt6797_a72_membership_publish_bootstrap()`;
- `mt6797_a72_membership_begin_up()`;
- `mt6797_a72_membership_publish_up()`; and
- `add_cpu(8)`.

`begin_up()` is not a usable public physical entry by itself. It consumes the
boot-local CPU8 attempt, mints the generation and cookie internally, and then
requires the caller's A36 record to already contain that newly minted identity.
The dormant test fixtures can predict the seeded identity; a production caller
must not.

The same A36 record still requires caller-supplied `da921x_page=0x80`,
`secure_sentinels_stable=1`, `pstore_console_available=1`, and
`watchdog_owned=1`. Current mainline has a stable composed physical snapshot
for topology, five DA921x data registers, platform state, protected clock, and
BigiDVFS, but no production source for those four assertions. In particular,
the provider snapshot deliberately performs no `PAGE_CON` access.

The watchdog assertion also creates a strict cycle:

1. A36 currently requires the watchdog to be owned before P17/P18 and before
   `add_cpu(8)`.
2. The binder correctly begins the retained transition ledger before arming
   the watchdog.
3. The binder is reached only by the MT6797 CPU-boot callback inside the
   `add_cpu(8)` request.

Arming the watchdog early would invert the proven ledger-before-watchdog order;
pretending readiness is ownership would manufacture evidence; and calling the
binder twice would violate its one-shot ownership. No direct caller can satisfy
the current graph.

## Analysis

The hardware-free binder result remains valid. The defect is at the still
dormant admission boundary, not in the executor or its physical callback
ordering. The A36 interface was introduced as a caller-supplied, source-only
record while all production paths were closed. It must now be converted into a
derived current-boot record before a physical caller exists.

The selected repair keeps the binder's already proven effect order intact:

1. while the physical source is registered, capture and validate the exact
   composed current-boot snapshot;
2. publish the exact A34 bootstrap from its proven replay class;
3. inside the membership owner, derive the CPU8 entry and A36 record from that
   snapshot and the immutable READY token, binding the internally minted
   generation/cookie without exposing them as caller assertions;
4. publish P17/P18 from the same controller task;
5. issue exactly one `add_cpu(8)` request;
6. in the binder, begin the retained ledger, arm the watchdog, and only then
   permit P27's first physical mutation.

The executable model passes success, both pre-consumption deferrals,
READY-token refusal, every post-consumption stage failure, repeat refusal, and
the complete recovery-order invariant. It records one CPU8 request only on the
request-bearing branches and zero CPU9, CPU_OFF, or retry operations.

The obsolete A36 page/recovery assertions must no longer authorize anything.
The real provider acquire owns its exact page-specific transaction, ledger and
watchdog success remain active binder results, and protected-clock and platform
facts come from the exact composed snapshot. A read-only binder-ready check may
reject before owner mutation, but it cannot stand in for watchdog ownership.

## Conclusion

`rejected` for the two-delta design consisting only of an enabled binder node
and a late `add_cpu(8)` caller at exact repository revision `28adce23` and
prepared-source state `c0fd471b`.

`confirmed` for the next bounded source slice: implement and exhaustively test
one derived CPU8 admission compositor plus a one-shot controller, preserving
ledger -> watchdog -> first-mutation ordering and keeping CPU9, CPU_OFF,
retries, and userspace triggers absent. This is a source admission result, not
hardware support.

## Follow-up

The authoritative next work is in
[Roadmap Gate 7](../../docs/ROADMAP.md#7-bring-up-cpu8). Build the repaired
hardware-free profile on Buildbox and run its bounded no-network tests before
assembling one distinct physical candidate. Only a validated candidate may be
installed to live-GPT inactive `boot2` under the standing safety gates.
