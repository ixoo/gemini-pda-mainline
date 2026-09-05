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
