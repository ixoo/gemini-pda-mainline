# Focused main-branch dispatcher proposal

[MAIN_DISPATCH.patch](MAIN_DISPATCH.patch) is an unapplied patch against the
reviewed userspace dispatcher. It adds `--branch` with exactly two choices:
`main` and the existing worker branch (the unchanged default). Both the local
branch/published-HEAD check and remote branch allowlist use the selected value.
No arbitrary ref, dirty checkout, unpublished commit or alternate origin is
admitted. Fetch-only still retrieves the exact published revision/package.

After review and application, a clean exact published main checkout can invoke:

```sh
python3 experiments/2026-09-05-owner-away-experiment-preparation/baseline/scripts/buildbox_userspace.py --keyboard-monitor --branch main
```

The source revision remains the local HEAD, checked against origin/main before
dispatch and again after the build. Remote checkout is Git-fetched. The patch
does not change compilation inputs, package validation, locks or execution
ceilings. Its applicability and proposed Python/embedded-shell syntax were
checked offline. Before an execution window, extend the existing mocked routing
tests for main and rejection of a non-allowlisted branch. No build ran and the
separate enabled eMMC runtime residue was preserved.

## Coordinator integration

The proposal is now applied to the dispatcher. Independent routing tests cover
main build/fetch, retained worker build/fetch and refusal of an unlisted branch
before transport. The archived proposal remains unchanged. No backend result
is implied by accepting this source change.

## Post-build publication refusal

The dispatcher now performs the claimed second exact branch advertisement
check after local HEAD/cleanliness verification and before fetch. Ref drift or
an empty advertisement preserves the successful build log/package and refuses
automatic collection. The six mocked routing methods include changed refs on
both allowed branches and both package kinds, empty post-build output, and
unchanged build/fetch-only behavior. These tests never contact Buildbox.

The timeout values are termination/wait targets, not guarantees of remote
cessation; see [the explicit limitation](MONITOR.md#dispatcher-completion-and-timeout-limits).
No timeout escalation, backend run or completed-receipt change is included.

Host correction checks at base `75636670d933b9231f36fddf2ce876801568f64e`:
all six mocked routing methods pass, including five post-build refusal variants;
Python/embedded Bash syntax, ShellCheck and the common repository gate pass
(192 profiles, unchanged metadata debt 37). This validates the correction's
host scope, not the coordinator's subsequently changed main checkout. The
original monitor fixtures and backend build were not repeated.

Project Planning independently applied and reviewed `8aeda777` on current
main. All six mocked routing methods and the common repository gate passed
(192 profiles; unchanged metadata debt 37). The successful build measurement
and acceptance receipt were preserved byte-for-byte. No backend repetition
or device action was needed for this correction.
