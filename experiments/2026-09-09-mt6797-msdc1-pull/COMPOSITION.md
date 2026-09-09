# MSDC1 pinctrl topic composition

Status: both rebased compile profiles pass Buildbox validation.
No Gemini candidate or device operation is selected.

## Observed integration failure

At repository commit `049909f613319ca744dbe9c9530e517a8c31dbee`, the isolated
input-enable, drive and pull topics each applied to the pinned upstream
baseline. Applying input-enable patch 0001 followed by drive patch 0004 fails
in `pinctrl-mt6797.c`: both hunks expect the original register-table context.
The pull topic also uses the original context. Isolated compile results do
not establish that these topics compose.

Rebase 0004 after 0001 and 0006 after 0004, keeping each logical change in its
existing format-patch. Added and removed source-line multisets are identical
to the original patches; only context, insertion location and dependency
messages change. The resulting driver was reviewed for table and callback
placement. No field value, drive group or callback implementation changes.

The drive compile profile now selects 0001/0003/0004. The pull compile profile
selects all six topics in canonical order, including both generic error fixes.
The manifest and canonical series remain unchanged. The other 203 profiles
retain their effective inputs. Existing isolated receipts remain evidence for
their recorded repository commits; they do not validate this rebase.

## Validation

Both updated series apply without fuzz or rejects using `git apply` to the
pinned upstream file contents. The complete six-patch result equals the reviewed
composed source. The [composition receipt](composition.json) records source
identities, selected sequences and the effective-profile audit. The existing
72-case Schmitt-refusal and 64-case advanced-pull regressions pass against the
composed source. Strict checkpatch passes with only `MISSING_SIGN_OFF` excluded.

Build both changed profiles from clean pushed inputs:

```sh
KERNEL_PROFILE=mt6797-msdc1-drive-compile ./scripts/build-kernel --backend buildbox
KERNEL_PROFILE=mt6797-msdc1-drive-compile ./scripts/buildbox fetch-package
KERNEL_PROFILE=mt6797-msdc1-pull-compile ./scripts/build-kernel --backend buildbox
KERNEL_PROFILE=mt6797-msdc1-pull-compile ./scripts/buildbox fetch-package
```

The [two build receipts](composition-compile.json) record validated packages
from `2653ed44d37fa02c304eb1a0b1b8b7bb032a21ae`. All six prepared source files
match each profile's reviewed composition, the expected field-table and
callback symbols are linked, and MT6797/Paris/common-v2 are built in. Both logs
have zero compiler warning/error lines. Remote package validation and local
fetch inventory/checksums pass. Module linkage and device behavior were not
tested. Repository checks pass with the Linux-only provenance fixture deferred
to CI.

The binding patch is unchanged; its earlier focused schema result remains
applicable to the same binding bytes. There is no new board DT, SMT map, bias-tuning operation or
power sequence. Electrical validation and truthful upstream certification
remain separate requirements.
