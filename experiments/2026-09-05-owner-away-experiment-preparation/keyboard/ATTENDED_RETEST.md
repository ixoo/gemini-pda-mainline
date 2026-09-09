# Attended keyboard retest

Status: prepared offline; no deployment or boot selected; execution bindings disabled.

The owner clarified that they were absent for the first two prompts and pressed
Shift + Fn + 1 during prompt 3, which requested Shift + Fn + 3. The
[prior result](attended-session-result.json) therefore contains a known sequence
mismatch. It does not justify changing the driver, map or event limits.

Use the same candidate, monitor and 20-case protocol pinned by
[the original preparation](session-preparation.json), with the finite steps and
preservation rules in [the attended session](ATTENDED_SESSION.md). The new
measurement is the declared sequence with the owner watching from prompt 1.
No previous per-boot observation or consumed claim supplies this run's evidence.

The fresh installer purpose is `keyboard-capture-retest`, with fixed receipt
`a53-keyboard-capture-deployment-2`. Its derived SHA-256 is
`2c6632b0ec2a8fce3efe10a51093bfff41046a39698a38c8cdf8eaf5637c1560`.
Only the receipt namespace differs from the exercised installer. Local candidate
validation, Bash syntax and ShellCheck pass; the existing receipt-equivalence
fixture covers this purpose. No kernel or userspace rebuild is needed.

The prepared private session helper SHA-256 is
`e70c297f51a57855bf644cf6e7e9325ae748a7f2ed88654aea100ba720c23927`. It uses a fresh evidence directory
and excludes the last mainline boot `803cd938-3da1-442a-b593-f11ab9fe740c`
and last confirmed Gemian `a54cc501-f558-4081-8779-dee9858ea258` in addition to
its dependency boots. Revalidate the live predecessor at handoff. Only the
identity command is prepared; actual boot, reader, metadata, custody and capture
records must still come from this run. Recovery additionally requires a recorded
owner confirmation for this exact boot before the helper can request restart.

Before shutting down for boot2, confirm the owner is ready for that transition.
After physical selection and readable-screen confirmation, complete the same-boot
prerequisites. Start the timed capture only when the owner is watching and ready.
The owner confirmed the clarified sequence: hold left Shift and Fn, press and
release the displayed digit, release Fn and Shift, then press and release A with
no other key held. A tap always includes its release. Use short presses and
release every key before the next case.
Follow the current prompt, not the first missed one. The remaining navigation,
modifier and HELP cases follow the unchanged protocol. If any case is missed,
stop and preserve the incomplete result; do not repeat or silently catch up.

Preserve and seal evidence after completion or failure, then wait for owner
restart confirmation. A deadline does not authorize recovery while the owner is
responding. The coordinator remains available to discuss the screen before any
non-urgent restart. This preparation does not claim runtime keyboard support.
