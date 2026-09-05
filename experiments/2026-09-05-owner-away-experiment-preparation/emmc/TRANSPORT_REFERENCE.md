# Transport selection lesson

For the named Gemini running its known-good Gemian OS, authenticated LAN SSH
and the experimental mainline USB SSH path are different transports. Absence
of the mainline USB interface or route only blocks USB transport; it must never
be used to declare Gemian LAN SSH unavailable. Authenticate the current OS
through its reviewed endpoint before choosing the next protocol. An owner boot
or screen description is useful context, not an authenticated kernel identity.

Observation: after two empty USB identity timeouts, an owner-requested bounded
Gemian LAN check succeeded without diagnostics and returned the retained kernel
and unchanged previously confirmed Gemian boot identity. See the
[boolean diagnosis](HOST_CONNECTION_DIAGNOSIS.json) and
[current-state receipt](OWNER_REQUESTED_CURRENT_STATE.json). This does not prove
why physical selection did not produce an observed mainline session.

The [one-shot mainline host prerequisite](mainline_host.py) inspects local
interface/address/route state without device packets. Its `identity_once` entry
requires the local gate before any claim or transport; absent, inactive,
ambiguous or conflicting routes refuse locally. It is for a separately admitted
new mainline observation only, never a retry, polling loop or Gemian LAN gate.
The existing immutable runtime and admission receipts remain unchanged.

Coordinator integration may place the durable transport lesson in the normal
operational reference. No personal endpoint, key or private evidence location
is needed in that reference.
