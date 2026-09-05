#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Exact Git-based userspace build and validated-package fetch; no kernel tree.
set -euo pipefail
umask 077
export LC_ALL=C PYTHONDONTWRITEBYTECODE=1
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repository=$(git -C "$here" rev-parse --show-toplevel)
[[ $# == 0 ]]
[[ -z $(git -C "$repository" status --porcelain) ]]
[[ $(git -C "$repository" remote get-url origin) == https://github.com/ixoo/gemini-pda-mainline.git ]]
branch=$(git -C "$repository" branch --show-current)
[[ $branch == codex/a53-authenticated-baseline ]]
revision=$(git -C "$repository" rev-parse HEAD)
remote_revision=$(git -C "$repository" ls-remote --exit-code origin "refs/heads/$branch" | awk '{print $1}')
[[ $remote_revision == "$revision" ]]
output_root="$repository/artifacts/buildbox/$revision"
mkdir -p "$output_root"
[[ ! -L $output_root ]]
for path in "$repository/artifacts" "$repository/artifacts/buildbox"; do [[ ! -L $path ]]; done
[[ ! -e $output_root/userspace-build.log ]]
ssh -o BatchMode=yes -o ConnectTimeout=5 -o ForwardAgent=no buildbox \
  /bin/bash -s -- "$revision" "$branch" <<'REMOTE' | tee "$output_root/userspace-build.log"
set -euo pipefail
umask 077
revision=$1
branch=$2
[[ $revision =~ ^[0-9a-f]{40}$ && $branch == codex/a53-authenticated-baseline ]]
root=/workspace/gemini-a53-userspace
[[ ! -L $root ]]
mkdir -p "$root/checkouts"
exec 8>"$root/.dispatch.lock"
flock -n 8
checkout="$root/checkouts/$revision"
[[ ! -L $checkout ]]
if [[ ! -e $checkout ]]; then
  partial="$root/checkouts/.partial"
  [[ ! -L $partial ]]
  if [[ -e $partial ]]; then rm -rf -- "$partial"; fi
  mkdir "$partial"
  cleanup() { rm -rf -- "$partial"; }
  trap cleanup EXIT
  trap 'exit 130' INT
  trap 'exit 143' HUP TERM
  git -C "$partial" init -q
  git -C "$partial" remote add origin https://github.com/ixoo/gemini-pda-mainline.git
  git -C "$partial" fetch -q origin "refs/heads/$branch:refs/remotes/origin/$branch"
  [[ $(git -C "$partial" rev-parse "origin/$branch") == "$revision" ]]
  git -C "$partial" checkout -q --detach "$revision"
  mv "$partial" "$checkout"
  trap - EXIT HUP INT TERM
fi
bash "$checkout/experiments/2026-09-05-owner-away-experiment-preparation/baseline/scripts/build-userspace.sh" "$revision" "$root"
REMOTE
[[ -z $(git -C "$repository" status --porcelain) && $(git -C "$repository" rev-parse HEAD) == "$revision" ]]
package=$(awk -F= '$1=="validated_userspace_package" {n++; value=$2} END {if(n!=1) exit 1; print value}' "$output_root/userspace-build.log")
[[ $package =~ ^/workspace/gemini-a53-userspace/userspace-[0-9a-f]{64}$ ]]
manifest_sha=${package##*/userspace-}
stage="$output_root/.fetch-userspace"
destination="$output_root/userspace-$manifest_sha"
[[ ! -e $stage && ! -L $stage && ! -e $destination && ! -L $destination ]]
mkdir "$stage"
cleanup() { rm -rf -- "$stage"; }
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' HUP TERM
ssh -o BatchMode=yes -o ConnectTimeout=5 -o ForwardAgent=no buildbox \
  "cd '$package' && test \"\$(sha256sum SHA256SUMS | cut -d' ' -f1)\" = '$manifest_sha' && sha256sum -c --strict SHA256SUMS >/dev/null && tar -czf - ." >"$stage/package.tar.gz"
python3 - "$stage" "$manifest_sha" <<'PY'
import hashlib, json, os, pathlib, re, tarfile, sys
stage = pathlib.Path(sys.argv[1]); expected = sys.argv[2]
target = stage / 'package'; target.mkdir(mode=0o700)
with tarfile.open(stage / 'package.tar.gz') as archive:
    members = archive.getmembers()
    if len(members) > 40 or sum(m.size for m in members) > 33554432: raise ValueError('package size/inventory')
    for item in members:
        path = pathlib.PurePosixPath(item.name)
        if path.is_absolute() or '..' in path.parts or not (item.isfile() or item.isdir()): raise ValueError('unsafe package path/type')
        destination = target / path
        if item.isdir(): destination.mkdir(mode=0o700, parents=True, exist_ok=True)
        else:
            destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            with destination.open('xb') as output: output.write(archive.extractfile(item).read())
            destination.chmod(0o700 if item.mode & 0o111 else 0o600)
raw = (target / 'SHA256SUMS').read_bytes()
if hashlib.sha256(raw).hexdigest() != expected: raise ValueError('manifest changed in transfer')
seen = set()
for line in raw.decode().splitlines():
    match = re.fullmatch(r'([0-9a-f]{64})  \./(.+)', line)
    if not match: raise ValueError('checksum line')
    sha, name = match.groups()
    if name in seen or hashlib.sha256((target / name).read_bytes()).hexdigest() != sha: raise ValueError('inventory/checksum')
    seen.add(name)
if seen | {'SHA256SUMS'} != {p.relative_to(target).as_posix() for p in target.rglob('*') if p.is_file()}: raise ValueError('file inventory')
PY
[[ -z $(git -C "$repository" status --porcelain) && $(git -C "$repository" rev-parse HEAD) == "$revision" ]]
mv "$stage/package" "$destination"
printf 'fetched_userspace=artifacts/buildbox/%s/userspace-%s\n' "$revision" "$manifest_sha"
