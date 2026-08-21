# DA921x provider-state export

## Status

Implementation input is prepared for Buildbox generation. No kernel patch has
yet been admitted, compiled, or used on the Gemini.

The first generation attempt from exact commit `9346a72ebfc1` passed the
managed-source integrity and all pinned parent-file checks, then stopped before
patch creation because one membership-test edit anchor had no exact match. The
fail-closed receipt is in
[`results/buildbox-generation-attempt-9346a72e.txt`](results/buildbox-generation-attempt-9346a72e.txt).
The guard now reports the rejected anchor's first line so the next retry can
correct only the attributable mismatch.

The diagnostic retry from `dd97fab23092` confirmed that `dedent()` had stripped
the two leading tabs from the transfer-body anchor. The second bounded receipt
is in
[`results/buildbox-generation-attempt-dd97fab2.txt`](results/buildbox-generation-attempt-dd97fab2.txt).
That one anchor now uses explicit tab-preserving strings; no proposed kernel
behavior changed.

Generation from `a5aae070142e` then passed source validation, generated the
three intended patches, and reproduced the edited commit by exact replay.
Strict checkpatch stopped on one long-prototype continuation-alignment check
in production patch `0313`, with zero errors and zero warnings. The bounded
receipt is in
[`results/buildbox-generation-attempt-a5aae070.txt`](results/buildbox-generation-attempt-a5aae070.txt).
The declaration now uses the standard break before its arguments; semantics
are unchanged.

Strict mode on `3fd493852c94` rejected that wrap because the declaration line
ended with an opening parenthesis. The bounded receipt is in
[`results/buildbox-generation-attempt-3fd49385.txt`](results/buildbox-generation-attempt-3fd49385.txt).
The private callback now has a shorter name, allowing conventional aligned
continuation without exceeding the line limit; its signature and behavior are
unchanged.

On `6f9b051cfabb`, production patches `0312` and `0313` passed strict
checkpatch. The first complete style pass over KUnit patch `0314` then found
one equivalent continuation-alignment check in a test-only zero-record helper,
again with zero errors and zero warnings. The receipt is in
[`results/buildbox-generation-attempt-6f9b051c.txt`](results/buildbox-generation-attempt-6f9b051c.txt).
The helper now has a shorter private name with ordinary aligned arguments.

## Question

Can the already registered DA921x A72 provider export one fresh, stable,
read-only five-register state record while preserving the provider registry,
endpoint, and root-I2C-adapter lock order?

The result must be attributable: two immediate complete samples under one root
adapter lock either match exactly or return `-EAGAIN`. Every error leaves the
caller's record all-zero. The path performs exactly ten reads on success and
performs no write, delay, retry, lifecycle transition, A34 evaluation, CPU
operation, boot image construction, or device action.

## Provenance

- Repository parent: `4b7535ee4a956c91ef6df3ba8451554af3410d35`.
- Canonical predecessor: patch `0311`.
- Managed prepared source state: `905fb7f5ead29cbe65eaf7f66e41433aea417c2ee15d751ebda6ddf79f19ad8e`.
- The four edited source-file identities are pinned in
  [`contract.json`](contract.json). Patches `0308`--`0311` do not edit those
  files.
- Generation and compilation run only on Buildbox from a clean pushed commit.
  No native VM build is permitted.

## Scope

The public platform-private provider ABI gains an optional snapshot callback.
The registry validates returned ABI, validity, reserved bits, and byte-width
raw values before publishing. A provider without the callback remains valid
for acquire/release and returns `-EOPNOTSUPP` for snapshots.

The DA921x callback serializes in the established order:

```text
provider registry mutex -> endpoint mutex -> I2C root-adapter lock
```

It temporarily sets adapter retries to zero, takes two immediate complete raw
samples, restores the retry count, and releases both locks. Local result
storage ensures observation does not modify the acquire/release transaction
ledger.

The hardware-free KUnit extension uses the existing unregistered in-memory I2C
adapter. It proves success, every negative and short read ordinal, an unstable
pair, the absent-provider boundary, and the optional-callback boundary.

## Planned procedure

1. Generate three logical patches on the exact Buildbox parent.
2. Require edited-source validation, exact replay, and strict checkpatch with
   zero errors, warnings, and checks.
3. Fetch only the validated patch package, review exact identities, and append
   the patches to the canonical series.
4. Add an isolated KUnit build profile and compile it through the explicit
   Buildbox backend.
5. Run the focused hardware-free suite under QEMU if the existing runner can
   consume the exact profile without broadening the test boundary.
6. Record and push evidence before selecting the protected-state composition
   step.

## Decision rule

Pass only when a successful snapshot has exactly one lock/unlock pair, ten
locked reads, zero writes and delays, zero adapter retries during transfer,
restored retries afterward, exact raw values, and an untouched provider
transaction ledger. Every transfer error, short read, or sample mismatch must
publish no state. No result in this experiment authorizes CPU8 or a device
boot.
