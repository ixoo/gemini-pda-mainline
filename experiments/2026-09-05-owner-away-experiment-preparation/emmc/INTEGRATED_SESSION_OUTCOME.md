# Integrated storage session: no read, evidence preserved, Gemian confirmed

The owner selected boot2 and subsequently confirmed power and readable text.
The single integrated identity attempt returned mainline at 821.69 seconds.
Its complete guard refused, without identifying the individual failed predicate;
the returned uptime independently exceeds the 400-second admission limit and
600-second logger lifetime. No live window or storage-read claim was created.
See [the immutable identity receipt](INTEGRATED_IDENTITY_REFUSAL.json).

A separately admitted use of the unchanged terminal-log exporter preserved all
available bounded files. The logger had stopped at its 600-second deadline:
1,746 records and 121,083 log bytes were retained, with failed/deadline-expired
status and exit 1. No signal or observer restart occurred. Complete preservation
supports recovery, while the log-export classification remains inconclusive for
the intended observation. [The preservation receipt](TERMINAL_LOG_PRESERVATION.json)
pins the command, source, raw manifest and decoded file identities; raw contents
remain private.

The separately admitted native recovery request timed out. Its exact output
does not override that incomplete transport result. A subsequent independent
Gemian LAN check passed with the expected kernel/architecture and a boot ID
changed from both the prior Gemian boot and this mainline boot. These scopes
remain separate in [the recovery receipt](TERMINAL_SESSION_RECOVERY.json).
The device was left running Gemian with sole custody retained. No storage read,
partition write, retry, shutdown or new selection followed the confirmation.

This attempt is closed without a storage measurement or support claim. Its
consumed identity admission cannot be replayed. A future session requires a
new reviewed admission and timely owner coordination; neither the later owner
reply nor preserved terminal log renews the old logging window. The retained
candidate is unchanged. Ordered work remains in [the roadmap](../../../docs/ROADMAP.md).

The coordinator reviewed all three sanitized receipts and independently ran
the 47 existing session-step tests, including pre-exited logger preservation,
partial-export refusal, evidence binding and recovery classification. They
passed in 29.133 seconds. This host verification does not turn the refused
hardware observation into a passing storage test.
