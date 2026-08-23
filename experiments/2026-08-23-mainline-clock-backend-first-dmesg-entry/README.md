# Experiment: clock-backend entry in first dmesg

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-23-mainline-clock-backend-first-dmesg-entry` |
| Status | definition; not yet a boot candidate |
| Subsystem | read-free clock-backend registration and probe entry |
| Device variant | Planet Gemini PDA, MT6797 |
| Date(s) | 2026-08-23 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 7, protected clock-read qualification |

## Question or hypothesis

Can the clock backend register and enter its read-free probe on the exact
runtime-proven serviceability DT before any protected clock transaction is
attempted?

The predecessor qualified the signature-last writer, warm retention, record
format, and changed-ID Gemian enumeration at first dmesg record 1. An older
clock-entry experiment already placed checkpoints immediately before platform
driver registration and as the probe's first operation, but its sparse records
173 and 174 could not be enumerated and its writer had not yet been qualified.
This successor keeps those call sites while moving their records to first
dmesg records 1 and 2.

The exact discriminator is:

1. record 1 commits immediately before clock platform-driver registration;
2. record 2 commits as the clock probe's first operation;
3. the probe may allocate state, map its declared resources, acquire its clock
   handle without enabling it, initialize locks, and publish driver data; and
4. no protected clock read, BigiDVFS read, MMIO transaction, clock enable,
   transition owner, or CPU request occurs.

## Provenance and environment

- Qualified first-dmesg result: signed and pushed commit `db28c215`.
- Existing call-site patch:
  `0325-soc-mediatek-add-Gemini-clock-backend-entry-ledger.patch`.
- Parent profile: `da921x-current-service-control`.
- New profile: `da921x-clock-entry-first-dmesg`.
- New canonical patch:
  `0334-pstore-qualify-Gemini-clock-entry-in-first-dmesg.patch`.
- Expected release: `7.1.3-gemini-clock-entry-first-dmesg`.
- Build backend: Buildbox only; no native VM build.

## Safety assessment

The new option is default off. It retains the qualified exact Gemini
reservation, exact all-ones entry-header gate, payload/start/size/signature
commit order, full local readback, two-write ceiling, and no-clear/no-retry
policy. It owns only records 1 and 2 at `0x44410000` and `0x44411000`.

The candidate DT will be derived from the exact runtime-proven serviceability
DT and will change only the clock-backend node to `status = "okay"`. The
observer and BigiDVFS backend remain absent. The driver contains no read in its
probe path: resource mapping is allowed, but no mapped register is accessed and
the acquired clock is not enabled. CPU8 and CPU9 admission remain closed.

## Associated code

- `patches/v7.1.3/0334-pstore-qualify-Gemini-clock-entry-in-first-dmesg.patch`
- `configs/gemini-clock-backend-first-dmesg.fragment`
- `contract.json`
- `scripts/validate.py`
- `scripts/test-validate.py`

## Procedure

1. Validate the exact patch, profile, canonical-series placement, default-off
   mode, consecutive record ownership, inherited call sites, qualified writer,
   complete readback, live markers, and action veto inventory.
2. Commit and push the definition with a clean worktree.
3. Build the exact commit on Buildbox with
   `KERNEL_PROFILE=da921x-clock-entry-first-dmesg ./scripts/build-kernel --backend buildbox`.
4. Fetch only the validated package. Derive the candidate DT from the
   byte-identified serviceability DT by enabling only `dvfsp_clock_backend`,
   then independently validate the DT, configuration, image, and container.
5. From known-good Gemian, resolve inactive live-GPT `boot2`, require both
   owned headers exact empty plus the standing storage and power gates, write
   and fully read back the admitted candidate, then shut down cleanly.
6. Pre-arm live and changed-ID capture before one physical selection. Return to
   Gemian only after exact live identity, serviceability, and zero-action gates.
7. Recover pstore plus direct records 1 and 2 and classify the deepest durable
   checkpoint reached.

## Decision map

- Live probe-complete plus exact records 1 and 2 qualifies read-free clock
  registration, population, and probe. The next candidate may attempt exactly
  one protected clock read with before-call and after-return checkpoints.
- Record 1 only localizes the boundary after driver init and before probe entry;
  inspect platform population and binding without repeating an identical boot.
- Neither record keeps the boundary before clock driver init.
- Any serviceability loss without attributable records rejects the artifact.

No branch in this experiment authorizes a protected clock call, BigiDVFS call,
or CPU8/CPU9 admission.

## Conclusion

The local definition gates pass: exact patch identity and parse, record CRC and
length checks, inherited writer/call-site checks, 16 unsafe mutations, all 115
manifest-profile series invariants, eight invariant-auditor mutations, JSON,
and whitespace. Exact prepared-source apply, style, configuration, and compile
checks remain with Buildbox. The definition is not a boot candidate. See the
[prebuild result](results/prebuild-definition-20260823.txt).
