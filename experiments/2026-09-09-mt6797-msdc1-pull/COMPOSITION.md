# MSDC1 pinctrl topic composition

Status: rebased input checkpoint; combined Buildbox compilation is pending.
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

Build results remain pending at this input checkpoint. The binding patch is
unchanged; its earlier focused schema result remains applicable to the same
binding bytes. There is no new board DT, SMT map, bias-tuning operation or
power sequence. Electrical validation and truthful upstream certification
remain separate requirements.
