# Smallest coherent reusable healthy-lifecycle change (design, not code)

After two bounded C2+C3 passes (runtimes 31, 32), the driver's join is still single-use: one
scan, one connect, one bounded data phase, then a terminal that cannot be re-armed. This note
proposes the smallest coherent change toward a reusable connect/disconnect/scan lifecycle,
grounded in the source inventory of the current 0179 driver. The ranked first milestone is a
**healthy two-lifetime successor** — one healthy join, healthy teardown, then a second healthy
join/scan in the same boot — as a concrete step toward the ordinary mac80211 station driver;
sustained operation (continuous traffic, connection monitoring) is still required afterward
and is not claimed by it. Source-supported reuse is the successor's **test hypothesis**, not a
fact asserted here, and not something a test could prove before the successor exists; the real
pre-code work is resolving the actual mac80211 and vendor ownership contracts below. The
crypto/replay boundary is a separate, required completion condition, not reduced by runtime
32's absent group 1 and not parked indefinitely.

## The current one-shot boundary (source-grounded recap)

From `mac.c` (2d7e5a33, HEAD 21066579): one scan is latched by `scan_used` (set before the
first write, never cleared); the join is latched by `join_retired`; `closing` is set
permanently at `remove_interface` and by every fatal; `first_error` is sticky. `sta_state`
upward transitions are monotone per-stage flags with no re-arm, bound to the single
`vif`/`join_ap`. The one terminal `fail_stop` (and `regulatory_stop`, branch 9) is the poison
path: it sets `first_error + closing + join_retired`, completes the waiters and frees the
queued/in-flight frames once. A healthy lifetime instead reaches `cleanup: stage=3` (channel
returned at stage 1, grant held through the data phase with the grant-tail reserving deauth
room), but still ends in `join_close`, which also sets `join_retired`.

## The proposed smallest change

Separate a **healthy retire** from the **poison retire**, re-arming only the former:

1. **Healthy-terminal reset, distinct from poison, guarded on both teardowns.** Re-arm the
   per-lifetime join_* state to the pre-join baseline only when **both** have completed: the
   worker's healthy cleanup (`cleanup: stage=3`, credits returned, slots retired, deauth done,
   no `first_error`, no refusal) **and** the mac80211 station teardown (the station is no
   longer `AUTHORIZED` and the vif's sta has gone back down through `sta_state`). Do **not**
   clear join_* at stage 3 while the station is still `AUTHORIZED` — that would desync the
   driver from mac80211's object. Before re-arm: drain the TX queue, the in-flight frame, the
   page/credit debt and the completions to a quiescent baseline; cancel the delayed work
   outside the mutex and the queue lock (as `join_close` already does); and advance the scan,
   channel and STA command identities (`join_channel_token`, `join_sta_sequence`,
   `join_last_sequence`, pid counters) so no stale or delayed event from the first lifetime is
   accepted in the second — a delayed credit/done/grant whose identity does not match the
   current lifetime is rejected, not applied. Enumerate token/sequence **wrap** (u8 token and
   sequence counters) so a wrapped value is not mistaken for a live one. `first_error`/
   `closing` are left untouched and are not cleared. `fail_stop`/`regulatory_stop` are
   unchanged: an ambiguous command, an ownership loss, or a regulatory retire still latches
   `first_error + closing + join_retired` device-wide and stays permanently non-rearmable.
2. **`scan_used` per scan cycle, not per driver lifetime.** Clear `scan_used` on a healthy
   scan completion only (the `retired=1` healthy scan summary), never on an error or an
   uncertain submission; a second `hw_scan` is then admitted. The "retire before the first
   write" rule for an uncertain activation is kept exactly.
3. **`sta_state` re-arm after a healthy disconnect.** A healthy downward teardown (the
   `new < old` path that today requests cleanup once then closes) that completes the healthy
   cleanup resets the stage flags so a subsequent `NONE → AUTH → ASSOC → AUTHORIZED` for the
   same `vif`/AP is admitted again; a teardown that hit the poison path does not.

Nothing else changes: the grant-tail safety (`data_deadline = min(budget_end, grant_end −
GRANT_TAIL)` and the reserved deauth grant room), the channel return at cleanup stage 1, the
mutex/worker cancel ordering, the single-vif/perm_addr binding, and the decoders all stay as
they are.

## Invariants preserved (non-negotiable)

- The poison path is never re-armed: `first_error`/`closing` on an ambiguous command or an
  ownership loss remain terminal; recovery there stays a full teardown/reload.
- Grant-tail and the reserved deauthentication keep their room; no data is attempted after a
  release, and the channel is still returned at cleanup stage 1.
- Each terminal still frees queued and in-flight frames exactly once; re-arm runs only after
  that free, under the same mutex/worker discipline.

## Resolved from source (no firmware or device needed)

- The healthy terminal (`cleanup: stage=3`) and the poison terminal (`fail_stop`) are already
  distinct code paths; the change adds a reset on the healthy one and touches neither the
  poison latches nor the free-once discipline.
- The per-lifetime join_* state that a re-arm must clear is fully enumerated in the struct and
  set/cleared only under the mutex; no retained mac80211 object pointer complicates it (copied
  state only — a safe choice, not a blocker).

## Source contracts to resolve before code (the real pre-code work)

These are source facts, not device tests; they are resolved by reading the pinned mac80211
and vendor source, and only an *actual unsupported* contract found there is a blocker.

1. **mac80211 callback ordering across a reconnect/rescan (pin from source).** The exact op
   sequence mac80211 drives for a second connect/scan — `sta_state` down to `NOTEXIST` and
   back up, `remove_interface`/`add_interface` vs `stop`/`start`, `cancel_hw_scan` then a new
   `hw_scan` — and which of those the driver must accept idempotently. The re-arm guard must
   match this ordering exactly (it is why re-arm waits for the station teardown, not stage 3).
2. **Vendor repeated station/key/channel create-delete contract (pin from source).** Whether
   the vendor command set supports deleting and re-creating the STA record, the keys and the
   channel grant within one firmware session (the add_peer/associate/remove and key
   add/remove/channel grant/return commands already used), with non-stale command identities.
   If the source shows a create/delete pair that is genuinely one-shot or an ownership the
   firmware does not let the host re-acquire, *that* is the blocker to name; absent such a
   finding, repeated create/delete is the successor's hypothesis, tested by the two-lifetime
   run, not assumed and not pre-refuted.
3. **Connection-monitor behaviour in the bounded test's scope.** The existing nullfunc/beacon
   monitor path (runtime 28: a locally generated reason-4 disconnect once unicast idles with
   no nullfunc admitted) is in scope for the finite two-lifetime protocol — the second
   lifetime must start from a clean monitor state — but it is not a sustained-operation claim
   and the bounded test does not assert continuous traffic.

Firmware/CONSYS reusability (a second join without a full WMT re-init) is the successor's
**test hypothesis**, measured by the two-lifetime run once the contracts above support it; it
is not a pre-code blocker and will not be treated as a proven fact before the run.

## Crypto/replay boundary (separate, required, not parked)

Independent of this lifecycle work and not satisfied by runtime 32's absent group 1; it needs
the keyID/TID/key-incarnation/authenticated-producer/reorder-and-retry semantics established
first, with no generic floor and no documented gap treated as shipping. The rejected
equivalences are not adopted here: a sequence-control duplicate is not a CCMP PN replay, a
missing delivery is not enforcement, a CIPHER_MISMATCH flag is not a replay verdict, and
natural retries are not a controlled replay attack. The crypto route stays open and is chosen
separately; it is not parked indefinitely.

## Not in scope / non-claims

This proposes no code and implies no completion. It does not widen to a full station stack,
does not touch the crypto path, and adopts none of the withdrawn RE function/producer claims.
The custodian and OpenCode rank it; a chosen step would then get its own proposal diff, source
resolution of uncertainty 1–2, checks and a reviewed test protocol before any build.
