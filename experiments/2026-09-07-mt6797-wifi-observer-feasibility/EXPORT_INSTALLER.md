# Export installation preparation

The [first installation and physical attempt](EXPORT_ATTEMPT_1.md) now have
results. Installation/readback passed; the USB export did not complete.
The deriver now selects only the [second diagnostic session](EXPORT_SESSION_2.md)
and its new `wifi-export-deployment-2` evidence directory. Its generated remote
gate is byte-identical to the first installer's; only package/checksum,
preceding-boot and evidence-directory identities differ. The exact generated
shell again passed all 19 deployment cases and four external-identity refusals.

[The deriver](export-installer.py) reuses the pinned historical installer and
the current reviewed block-device guard. The generated script stays private.
It is bound to the externally supplied padded-image/session digests and the
preceding authenticated Gemian boot UUID. Its local checks join the selected
filesystem, seven current startup files and 46-patch kernel receipt before
derivation. It accepts only the validated export package, never a cycle action.

The changes to the guarded installer are candidate/manifest identities,
experiment/staging/evidence names, local repository location, portable size
measurement, disabled SSH host-key updates and an exact preceding-boot check.
The remote GPT resolution, current/root/mount/holder/swap checks, two stable
power samples, predecessor comparison, single write, flush and full independent
readback remain inherited. An already matching partition skips the write.
The temporary upload retains the reviewed private-file staging path and cleanup;
no new partition backup is made. Verified installation ends in clean shutdown.

The generated shell passed syntax and ShellCheck. The existing deployment-shell
fixture runner was supplied the actual generated shell: all 19 cases passed,
including mounted/root identity changes immediately before writing, changed
predecessor, corrupt staging, low power and failed readback. No actual device
operation occurs in those fixtures. The first local derivation refused because
the source mapping used the archive name `init`; mapping it to the existing
`startup-init.sh` corrected the lookup before any installer was produced.

Run the deriver with `--candidate`, `--filesystem`, `--padded-sha256`,
`--session-sha256`, `--boot-id` and a new private ignored `--output` path.
Review that exact output before invoking it with its exact `--target`,
`--candidate-dir` and `--evidence-dir` arguments. Derivation is not installation.
No physical boot request is permitted until installation/readback and shutdown
are recorded. The [export session](EXPORT_SESSION.md) separately requires a
prepared receiver and attribution to the PDA's physical USB connection.
