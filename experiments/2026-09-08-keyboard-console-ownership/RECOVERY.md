# Recovery confirmation simplification

For new baseline sessions, recovery is now judged by the actual return to
Gemian, not by how the old SSH connection ends:

1. Preserve the available log before requesting recovery.
2. Send the guarded reboot request once. Accept its complete identity frame,
   including the reboot helper's normal announcement. A bounded SSH timeout
   after that frame leaves return confirmation pending; it is not a failed
   recovery result.
3. Confirm the known-good Gemian release over authenticated SSH with a boot ID
   different from both the prior Gemian boot and the mainline boot.

The active baseline finisher rejects incomplete or interrupted requests,
unexpected output and a reboot helper that returns. Its existing deadline and
one-request limit remain. A missing or unchanged Gemian boot cannot pass.
Successful return no longer needs a separate supplemental timeout review.

This fixes both observed checker defects: requiring SSH exit before the deadline
and rejecting the normal reboot-helper announcement. No target command, kernel,
initramfs, credential, installer or transport option changed. The already
installed candidate passed independent validation again and needs no rebuild.
The updated checker has not been exercised in a new hardware session.

Old phase receipts are recognized by the one retained finisher source hash and
are verified using their original parser. They cannot execute new actions.
This preserves the completed [session result](RESULT.md), including its original
incomplete request witness. The existing supplemental verifier and the prepared
disconnect test's actual dependency both still pass without editing raw evidence.
Source pins were updated for the changed verifier implementations.

Validation: 51 session-checker tests, 25 aggregate-verifier tests, four legacy
supplemental tests, seven disconnect tests and six prerequisite tests passed.
The new cases cover timeout plus normal wrapper output followed by changed-ID
Gemian, no recovery pass for an unchanged boot, request interruption and partial
output, and refusal to execute historical admissions. The new full aggregate
case passes through the ordinary verifier without a supplement. Candidate and
installer validation, generated Bash syntax and ShellCheck also passed.
