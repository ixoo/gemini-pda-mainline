# Attended installation outcome and offline correction

The candidate was not written. The sole baseline custodian remains assigned, but
all live access is paused while the coordinator clarifies an owner report of
physical boot2 selection. No Ready-for-boot2 baseline handoff was issued. A boot
of the previously installed artifact cannot be attributed to this candidate.

## Observed sequence

The exact frozen candidate passed local validation, and the initial device probe
passed live-GPT, inactive-target, power and identity checks. Active swap initially
prevented tmpfs staging. The separately admitted read-only ownership probes
identified a one-shot startup service using default swap options. A declared
shutdown helper was absent; the effect of a historical startup configuration
write was not established. Those helpers were never executed by this experiment.
The coordinator accepted a temporary direct swap adjustment preserving backing
configuration and leaving normal startup policy unchanged.

The first broad startup selector truncated relevant context. Its twenty-file
replacement found swap references but failed to recognize stanza/import lines
with POSIX character classes on the remote awk. The final three-file selector
using explicit space/tab matching produced actual service options and script
bodies. Host matching alone had not established remote compatibility. All prior
partial receipts remain unchanged; no failed probe was silently replayed.

One admitted temporary deactivation succeeded. The unchanged installer then
failed during upload, before invoking its write phase. Cleanup reported an
unsafe staging path and was unconfirmed. There was no completed deployment,
readback or shutdown receipt. A separately admitted read-only reconciliation
found no file or open descriptor in the exact candidate staging namespace.

One abort restoration returned nonzero with empty output. The subsequent
read-only reconciliation established the original backing, configuration,
unused state and default priority, with the canonical device-name spelling in
`/proc/swaps`. The coordinator accepted restoration at that observed Gemian boot.
The command's original nonzero receipt remains a false refusal by an
exact-spelling verifier, not a claim that restoration failed or never ran.
No additional toggle was performed to reproduce the old spelling.

Private immutable claims, exact executed sources, streams, process results and
classifications are under `artifacts/a53-authenticated/attended-install-1/`.
Raw startup text and private device metadata are not republished here. Shared
queue and physical-session messaging remain owned by the coordinator.

## Corrective source, not device admission

The uploader now prepares, streams and cleans its mode-0600 staging file as root
with passwordless sudo and requires uid zero. It retains the exact tmpfs, no-swap,
name, link-count, size, candidate, live-GPT, power and full-readback gates.
This avoids dependence on the lifetime of a non-root user's IPC objects across
separate SSH sessions. Logout cleanup such as logind RemoveIPC is a plausible
cause of the vanished original stage, not a confirmed cause from this receipt.
A single-session lifecycle would require a broader transport rewrite; the
root-owned adjustment preserves the reviewed deployment ordering.

SSH now uses the already pinned recovery trust file, checks its exact digest,
disables ambient configuration, global trust and host-key updates, and retains
strict host checking. The failed legacy transport attempted ambient known-hosts
updates which the host denied; those warnings do not establish the upload cause.
No trust file or host enrollment was changed.

The corrected installer uses a new evidence identity ending in `deployment-2`;
the failed `deployment-1` directory is preserved. The candidate bytes remain
unchanged. Corrected local derivation SHA256:
`fb62efa6fc74840698f6a2538963262d3949ee1678ee6d23fb7708654cd5ad8d`.
There is no admission to execute this revision.

The temporary swap verifier now accepts only the original or canonical spelling
and requires either to resolve to the exact same backing. It does not accept
arbitrary aliases or another zram device. Six inert fixture cases cover both
accepted spellings, changed resolution, another node, nonzero usage and changed
priority. This correction does not create a new mutation budget.

Validation: nine installer host tests passed in 8.112 seconds, including inert
success/skip, refusal, interruption, cleanup and pinned-trust mutation cases.
The alias fixture passed six cases in 0.031 seconds. Generated Bash syntax and
ShellCheck passed, and the actual candidate passed local-only validation. No
corrected device deployment, kernel build or hardware support result is claimed.
