# Reviewed metadata-only `core` package-parent amendment

This amendment applies prospectively after two pre-execution stops and changes
only the source-parent rule in [WORK_ITEM.md](WORK_ITEM.md). Every other bound,
guard, refusal and acceptance predicate remains in force.

## Attempt lineage and escalation

- Contract dispatch: `cb7747a7c04eadf14af1dcc925cb362da6b7c3d5`.
- Frozen-input repair dispatch:
  `cfe500d5d8b62b5102b588c2f8f1e26236ecbf56`.
- First stop: the contract referred to a frozen `inputs.json` that was absent.
  No RE-VM, package, database or private input was accessed.
- Second stop: exact RECORD inspection found
  `vmlinux_to_elf/__init__.py` and
  `vmlinux_to_elf/core/kallsyms.py`, but no
  `vmlinux_to_elf/core/__init__.py`. The source-forcing rule refused an
  unadmitted package parent before package or private-input execution. See
  [PREFLIGHT.md](PREFLIGHT.md).
- Sol Medium independently approved the narrow metadata-only rule below at
  `2026-09-07T00:44:53Z`. It rejected a general namespace-source exception.

## Exact prospective rule

After installing the audit guards and terminal source-forcing prefix finder,
load the exact RECORD-backed top-level `vmlinux_to_elf` source. Then create one
fresh `ModuleType("vmlinux_to_elf.core")` solely as import topology. Before
insertion require that `sys.modules` contains neither that name nor any
descendant and that the top-level package has no `core` attribute.

Resolve the one permitted core directory using minimal directory stat and
containment checks only. Every path component must be nonsymlink, the resolved
directory must be beneath the exact installed distribution root, and it must
equal the parent directory of every admitted pinned core source. These checks
do not permit directory content discovery or executable code loading.

The synthetic module must have:

- exact `__name__` and `__package__` equal to `vmlinux_to_elf.core`;
- no `__file__` or `__cached__`, no loader and no executable code;
- a `ModuleSpec` with exact name, `loader=None`, `origin` equal to the frozen
  non-filesystem marker `synthetic-metadata-only`, and exactly one
  `submodule_search_locations` entry equal to the resolved core directory;
- `__path__` as a separate immutable one-element tuple containing only that
  same directory; and
- the top-level package's `core` attribute bound to that exact module object.

Freeze the complete constructor/bootstrap source, its SHA-256 and all metadata
in `loader.json` before private Image content access. The synthetic parent does
not count against the existing sixteen executable-source-module cap because it
executes no source.

The prefix finder is terminal for every `vmlinux_to_elf.*` request after the
guards are installed. Only this exact synthetic parent, the already admitted
database leaf stub and explicitly whitelisted RECORD-backed `.py` modules may
resolve. It must never defer to `PathFinder`, a namespace loader, an ordinary
source/bytecode loader or any other finder. Every executable core child must
retain exact source-forced loader, spec, origin, RECORD hash/size and in-memory
code provenance and counts toward the cap.

After import and after the single parser construction, require all synthetic
parent metadata, search paths, spec identity and top-level binding to be
unchanged. Any added parent attributes may only be exact child-module bindings
whose identities and source-forced provenance appear in `loader.json`.

## Additional refusals

Stop on any existing, preloaded or replaced `vmlinux_to_elf.core` module or
descendant; preexisting top-level `core` binding; `NamespaceLoader` or ordinary
finder participation; extra, relative, symlinked or mutable search location;
parent path/spec/binding drift; filesystem read, loader, file, cache or code
attached to the synthetic parent; unrecorded child or attribute; duplicate
origin; source-count overflow; or inability to prove every executable child's
source identity. Existing database-path, bytecode, open/write/network,
dependency, detector, sentinel, restoration and construction-count refusals
remain unchanged.
