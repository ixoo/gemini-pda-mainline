# Isolated schema tool environment

The coordinator prepared a Buildbox-only environment at
`/workspace/gemini-pda/cache/validation-tools/schema-2026.6`. It supplies
dtschema 2026.6, pylibfdt 1.7.2.post2 and Yamllint 1.38.0. The dtschema version
matches the project's existing VM requirement, but no VM build or tool fallback
was used. [The setup receipt](results/schema-tools-setup.json) records all 18
resolved packages, original download URLs/hashes, temporary headers and the
compiled libfdt extension identity. [The host receipt](results/schema-tools-host.json)
pins the existing Python/compiler and confirms removal of staging state.

## Setup and observed limits

Read-only inventory found the required schema commands absent. Initial setup
refused before environment creation because Python development headers were
missing. No existing environment or system package was modified.

The successful setup reused the installed Python 3.11.2 and GCC 12.2.0. Its
headers came from the exactly matching Debian `libpython3.11-dev` package.
The 4,737,920-byte package matched the SHA-256 on the
[official download page](https://packages.debian.org/bookworm/amd64/libpython3.11-dev/download),
and its package/version/architecture control fields matched before use. Only
191 regular header files below `usr/include/` were copied into an exclusive
temporary directory after path/type/size checks. Libraries, maintainer scripts
and system package state were not installed. No Release signature check or
independent compiler/bootstrap reproducibility run is claimed.

The new virtual environment was created under a dedicated nonblocking lock.
Build tools were installed first, including SWIG 4.4.0 as required by the pinned
pylibfdt source. The runtime tools then installed with build isolation disabled,
using those explicit build tools and invocation-local header search paths.
Pip used the public PyPI index with isolated configuration, no retained download
cache, bounded network retries/timeouts and per-stage process/log limits.
Resolved download reports were retained beside the environment. This bootstrap
resolved transitive versions once; the resulting hash locks below pin replay.

`pip check` and all five requested tool version commands passed. Temporary
headers, package bytes and build staging were removed. Only the environment,
its metadata and lock remain on Buildbox. The host received JSON and hash-lock
text only, with no header, executable, wheel, source tree or private evidence.
Availability/version checks are not binding or DT validation results.

## Replay contract

Reuse the retained environment after checking its setup and executable/module
identities. Do not reconstruct it for an ordinary validation run. If it is lost,
start from a new managed directory under the same dedicated lock, check free
space, and install cleanup immediately after temporary state creation. Refuse
an existing incomplete or changed environment until its exact state is reviewed.

Use the recorded Python/bootstrap baseline, download and verify the exact header
package, and expose only its reviewed regular headers in temporary `CPATH`.
Create a fresh virtual environment with `python3 -m venv`. Install the complete
[build-tool lock](schema-build-requirements.lock) first, then the
[full environment lock](schema-tools-requirements.lock). Both use pip's
`--require-hashes --no-deps`; the second also uses `--no-build-isolation`.
Apply `--isolated --no-cache-dir --index-url https://pypi.org/simple`, keep the
environment's `bin` first on invocation-local `PATH`, and retain a pip report for
each phase. Never extend system Python or change shell startup files.

The locks select Linux x86_64/Python 3.11 wheels and the pinned pylibfdt source
archive; they are not a portable lock for other platforms. Remove temporary
header/source data after checking imports, `pip check`, tool versions and the
extension digest. A different extension digest needs explanation; the observed
digest alone is not a promise of bit-identical rebuilding.

For the admitted schema commands, prepend only
`/workspace/gemini-pda/cache/validation-tools/schema-2026.6/bin` to that command's
environment. Exact source/build verification, the shared build lock, full
diagnostics and the schema protocol remain separate requirements. No schema
command, kernel build, QEMU guest or device action ran during this setup.
