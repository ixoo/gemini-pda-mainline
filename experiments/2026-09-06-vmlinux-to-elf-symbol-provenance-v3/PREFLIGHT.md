# Source-parent gate refusal

review_ready_utc = 2026-09-07T00:42:57Z

The amended execution dispatch resolved locally from `cfe500d5` to
`cfe500d5d8b62b5102b588c2f8f1e26236ecbf56`. The prospectively supplied
`inputs.json` was present. The exact contract hash and twenty dependency-file
hashes matched; excluded evidence was hashed only, never imported as tuples or
intervals. The coordinator was informed of the resolved full dispatch value.

Through the approved RE shell, pinned METADATA, RECORD, Kallsyms source,
launcher-script source, symbolizer source and writer source hashes matched.
Before executing any package code, a RECORD-only required-origin check found:

| Required source origin | Present in pinned RECORD |
| --- | --- |
| vmlinux_to_elf/__init__.py | yes |
| vmlinux_to_elf/core/__init__.py | no |
| vmlinux_to_elf/core/kallsyms.py | yes |

The contract requires a RECORD-backed source for every package module and
expressly refuses namespace sources. The required `core` package parent has
no admitted initializer origin under that rule. The permitted database stub
does not authorize synthesizing additional package parents. The specialist
stopped and informed the coordinator instead of inventing a loader exception.

The next discriminating decision was a prospectively exact metadata-only
parent-package rule, or a different admitted loading route. Any such rule had
to pin the allowed package-parent names, origins/search paths, lack of
executable code and exclusion of ordinary namespace/cache discovery.

No package was imported or executed, no loader/stub/subclass was constructed,
and no parser, detector or database sentinel was invoked. No private kernel,
database source/data/cache or prior private output was opened or hashed.
Kernel and remaining execution gates were not run because the earlier source
origin gate failed. No fresh private output child was needed; no raw result
exists. The RE shell was closed.

Executed host validation: supplied JSON parsing, contract/dependency SHA-256
checks, and `git diff --check`. Normal/optimized execution/refusal verification
was not constructed because no admitted loader method or binary result could
be frozen. Later instruction analysis remained blocked. No device, network,
build, commit, push or shared-file edit occurred.
