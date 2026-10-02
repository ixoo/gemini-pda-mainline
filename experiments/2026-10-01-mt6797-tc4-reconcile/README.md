# MT6797 exclusive normal TC4 reconciliation

The [boot-sleepy result](../2026-10-01-mt6797-boot-sleepy/results/runtime-1.json)
witnessed consumable post-configuration returned-page counters, with CPU/TC4
and free-pool deltas arriving in different amounts. Credit recycling was not
enabled. Patch 0073 adds original bounded accounting to the retained normal
owner; it does not reset its ledger or sequence history.

## Source contract and limits

The [pinned source identities](../2026-10-01-mt6797-tx-status/results/sources.json)
cover Planet gen3 revision `c5b0be85017ad0c599725e8273842efdbecdd88a`.
`hal.h:488–514` reads WTQCR0–7 into sixteen 16-bit returned counts;
`nic_tx.h:297–315` assigns free-pool index 14 and CPU index 15, placing
FFA in WTQCR7's low half and CPU in its high half. `nic_tx.c:55–63` maps
normal TC4 to CPU. `nicTxCalculateResource` at lines 420–424 accumulates
free-pool and per-queue completions independently; lines 471–504 distribute
only available pages against completed pages. `nicTxReleaseResource` at
lines 580–590 then adds those matched pages to each retained free ledger.

With only TC4 active, distribution reduces to the minimum of the two pending
counts. This implementation excludes speculative extra-TX completion and all
other traffic classes. Every other returned queue must remain zero, and
neither pending count may exceed the outstanding normal debit. Unknown queues,
over-release, failed phase or inconsistent credit state poison the session.
The existing explicit normal limit remains 26; no INIT-credit reuse occurs.

The HIF requires a complete zero returned-page baseline before normal commands.
Both post-record acquisitions retain one HIF lock, and the caller holds RTNL
against the only other normal sender, the regulatory notifier. Each complete
snapshot validates a shadow ledger; an invalid first snapshot stops before
the next read. A failed later snapshot or expired deadline poisons without
committing the earlier refund. Only a fully valid pair commits credit. The
observation-only API retains its behavior in older profiles. A new default-off
Kconfig option selects accounting for this isolated profile.

A zero baseline and sole host owner support attribution but do not prove
firmware-internal execution or configuration application. Returned pages are
resource accounting, not a command acknowledgement or RF measurement.

## One-boot protocol

Hypothesis: witnessed CPU and FFA deltas can reconcile the sole retained TC4
ledger without overflow, reset or speculative release. The unique observation
is the bounded matched refund and independently retained pending counts after
the existing configuration. Raw counter and ledger arrays stay private;
publication reports validated accounting and whether any credit was returned.

The [parent protocol](../2026-10-01-mt6797-boot-sleepy/README.md#one-boot-protocol)
owns the single WMT/START, source-ordered configuration, eight-packet boot drain,
active ownership and recovery budgets. This change adds no HIF read or write,
IRQ enable, firmware-own request, radio operation, interface or packet DMA.
Keep the initial one-snapshot and post-configuration two-snapshot acquisition
budgets and their one-second deadlines. No automatic retry or repeat of an
identical candidate follows a refusal. Unknown/nonzero baseline counters,
foreign queues, excessive pending returns, partial acquisition or fatal status
require a changed acquisition/ownership diagnosis. Successful bounded refund
permits implementing the runtime receive/event and command/packet lifetime;
it does not yet demonstrate a usable station.

Preserve the complete private log, exact mainline identity, same-boot wiphy
observation and A53 regression before reviewed recovery. Independently verify
changed-boot Gemian identity and carrier. Boot2 remains guarded, fully read
back and cleanly shut down; the owner selects it physically.

## Focused validation

`tests/tc4-reconcile-test.c` compiles the actual selected HIF implementation,
using the existing [compatibility shim](../2026-10-01-mt6797-normal-sets/tests/test-compat.h).
Strict C11 warnings-as-errors with ASan/UBSan pass for all free-page values
0–26 and CPU/FFA deltas 0–28, both arrival orders, matching pending returns,
zero returns, 16-bit maximum counts, invalid phases/pending state and unchanged
shared sequence history. HIF cases cover all 60 initial/pair transfer failure
positions, every dirty baseline/foreign queue in either snapshot, over-release,
missing accounting baseline, duplicate acquisition refusal and deadline expiry
after the final read. A valid early refund cannot survive a later failure.
The historical observation-only fixture also passes unchanged against this HIF.

Compile with `-std=c11 -Wall -Wextra -Werror -fsanitize=address,undefined
-fno-sanitize-recover=all`, including the exact prepared driver's directory and
the linked existing shim. Use a managed temporary output and remove it afterward.
These callbacks do not emulate hardware bus exceptions or firmware timing.
Linux 7.1.3 checkpatch reports zero errors/warnings with `--no-tree --no-signoff`;
optional spelling and const lists were unavailable. No synthetic DCO sign-off
or upstream submission readiness is claimed. The [clean pushed Buildbox build](results/build.json),
[candidate validation](results/candidate.json) and [offline tooling/session preflight](results/preflight.json)
passed. Both fixtures also passed against the actual prepared source on Buildbox.
No device test has run for this candidate.

Set `GEMINI_PRIVATE_REPO` to the checkout holding ignored private artifacts for
installer preparation and session tools. The first offline installer generation
failed before output because that caller setting was missing; supplying it
produced the validated installer. The exact capture/host preflight remains
pending a real deployment receipt.
