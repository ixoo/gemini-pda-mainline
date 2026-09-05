#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Run only in an assigned userspace Buildbox window; never builds a kernel.
set -euo pipefail
umask 077
export LC_ALL=C SOURCE_DATE_EPOCH=0 PYTHONDONTWRITEBYTECODE=1 PYTHONOPTIMIZE=0
unset CPATH C_INCLUDE_PATH CPLUS_INCLUDE_PATH LIBRARY_PATH COMPILER_PATH GCC_EXEC_PREFIX REALGCC CFLAGS CPPFLAGS LDFLAGS
[[ $# == 2 || $# == 3 ]] || { echo 'usage: build-monitor.sh EXACT_REVISION MANAGED_ROOT [disabled|capture]' >&2; exit 2; }
revision=$1
managed=$2
mode=${3:-disabled}
[[ $mode == disabled || $mode == capture ]]
kind=keyboard-monitor
binary_name=keyboard-monitor-disabled
production_entry=disabled
compile_flags=()
if [[ $mode == capture ]]; then
  kind=keyboard-capture
  binary_name=keyboard-monitor
  production_entry=enabled-admission-v1
  compile_flags=(-DKEYBOARD_MONITOR_ENABLED=1)
fi
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repository=$(git -C "$here" rev-parse --show-toplevel)
[[ $revision =~ ^[0-9a-f]{40}$ ]]
[[ $(uname -s) == Linux && $(uname -m) == x86_64 ]]
[[ $(git -C "$repository" rev-parse HEAD) == "$revision" ]]
[[ -z $(git -C "$repository" status --porcelain) ]]
[[ $(git -C "$repository" remote get-url origin) == https://github.com/ixoo/gemini-pda-mainline.git ]]
git -C "$repository" branch -r --contains "$revision" | grep -q origin/
[[ -d $managed && ! -L $managed && $managed == /workspace/* ]]
[[ $(realpath "$managed") == "$managed" ]]
exec 9>"$managed/.userspace.lock"
flock -n 9
stage="$managed/.keyboard-monitor-stage"
[[ ! -L $stage ]]
[[ ! -e $stage ]] || rm -rf -- "$stage"
mkdir -m 0700 "$stage"
cleanup() {
  result=$?
  trap - EXIT
  if [[ $result != 0 ]]; then
    diagnostic="$managed/keyboard-monitor-failure-$revision"
    if [[ ! -e $diagnostic && ! -L $diagnostic ]]; then
      mkdir -m 0700 "$diagnostic"
      for log in configure.log build.log tests.txt full-duration.json full-duration.stderr disconnect.json disconnect.stderr; do
        if [[ -f $stage/$log && ! -L $stage/$log ]]; then
          head -c 2097152 "$stage/$log" >"$diagnostic/$log"
        fi
      done
      printf 'exit=%s\n' "$result" >"$diagnostic/result.txt"
    fi
  fi
  rm -rf -- "$stage"
  exit "$result"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' HUP TERM
df -Pk "$managed" | awk 'NR==2 {if ($4 < 524288) exit 1}'
mkdir "$stage/package" "$stage/package/licenses" "$stage/musl-build"
cc=$(command -v aarch64-linux-gnu-gcc)
ld=$(command -v aarch64-linux-gnu-ld)
qemu=$(command -v qemu-aarch64-static)
printf '%s  %s\n' c7b8890354c8ddc0364addfeb8968597e197627bd1e338fb6ed705b578803846 "$cc" \
  e09a889c78a75e73ed096c9fa28905599e6813298b9ac839d10b02ffa96e7b08 "$ld" | sha256sum --check --strict
{
  printf 'repository_commit=%s\n' "$revision"
  for tool in "$cc" "$ld" "$qemu" "$(command -v aarch64-linux-gnu-as)" \
    "$(command -v aarch64-linux-gnu-ar)" "$(command -v aarch64-linux-gnu-strip)" \
    "$(command -v aarch64-linux-gnu-readelf)" "$(command -v aarch64-linux-gnu-nm)" \
    "$("$cc" -print-prog-name=cc1)" "$("$cc" -print-libgcc-file-name)"; do
    sha256sum "$(realpath "$tool")"
  done
  "$cc" --version
  "$qemu" --version
  dpkg-query -W gcc-12-aarch64-linux-gnu binutils-aarch64-linux-gnu qemu-user-static
  if [[ $mode == capture ]]; then
    for tool in unshare ssh python3; do sha256sum "$(realpath "$(command -v "$tool")")"; done
    unshare --version
    dpkg-query -W util-linux openssh-client python3
  fi
} >"$stage/package/tool-inputs.txt"
curl --fail --location --proto '=https' --max-time 120 --max-filesize 1082499 \
  -o "$stage/musl.tar.gz" https://musl.libc.org/releases/musl-1.2.6.tar.gz
printf '%s  %s\n' d585fd3b613c66151fc3249e8ed44f77020cb5e6c1e635a616d3f9f82460512a "$stage/musl.tar.gz" | sha256sum --check --strict
[[ $(stat -c %s "$stage/musl.tar.gz") == 1082499 ]]
tar -xzf "$stage/musl.tar.gz" -C "$stage"
musl="$stage/musl-1.2.6"
printf '%s  %s\n' b870108ec5e7790e9f9919064f1b9421d62d5f9b0e6c230c6adf7ea2da62e97b "$musl/COPYRIGHT" \
  aa6574f8049f80f3b0a464bc20ab377a57bc0d3464478ac7ccb500f10002cd78 "$musl/configure" \
  ef7baf50ae403b3bf40c7403754daac024de9acf3c83e9b7b4cb9f80eaead343 "$musl/tools/musl-gcc.specs.sh" | sha256sum --check --strict
(
  cd "$stage/musl-build"
  timeout 120 env CC="$cc" CROSS_COMPILE=aarch64-linux-gnu- \
    CFLAGS="-Os -ffile-prefix-map=$stage=. -fdebug-prefix-map=$stage=." \
    "$musl/configure" --target=aarch64-linux-musl --disable-shared --enable-wrapper=gcc \
    --prefix="$stage/musl-install" >"$stage/configure.log" 2>&1
  timeout 600 make -j4 >"$stage/build.log" 2>&1
  timeout 120 make install >>"$stage/build.log" 2>&1
)
compiler="$stage/musl-install/bin/musl-gcc"
for replica in one two; do
  mkdir "$stage/$replica"
  timeout 60 "$compiler" -std=c11 -Os -static -ffunction-sections -fdata-sections \
    -Wall -Wextra -Werror "${compile_flags[@]}" "-ffile-prefix-map=$repository=." "-ffile-prefix-map=$stage=." \
    -Wl,--gc-sections,-u,keyboard_monitor_run "-Wl,-Map,$stage/$replica/monitor.map" \
    "$here/monitor.c" -o "$stage/$replica/monitor"
  aarch64-linux-gnu-readelf -h "$stage/$replica/monitor" | grep -q AArch64
  if aarch64-linux-gnu-readelf -l "$stage/$replica/monitor" | grep -q INTERP; then exit 1; fi
  if aarch64-linux-gnu-readelf -d "$stage/$replica/monitor" | grep -q NEEDED; then exit 1; fi
  aarch64-linux-gnu-nm --defined-only "$stage/$replica/monitor" | grep -Eq ' T keyboard_monitor_run$'
  grep -q keyboard_monitor_run "$stage/$replica/monitor.map"
  aarch64-linux-gnu-strip --strip-all "$stage/$replica/monitor"
  [[ $(stat -c %s "$stage/$replica/monitor") -le 131072 ]]
done
cmp "$stage/one/monitor" "$stage/two/monitor"
mkdir -m 0700 "$stage/fixtures"
timeout 90 env MONITOR_TEST_WORK_ROOT="$stage/fixtures" MONITOR_TEST_CC="$compiler" \
  MONITOR_TEST_QEMU="$qemu" python3 "$here/test-monitor.py" >"$stage/tests.txt" 2>&1
python3 - "$mode" "$qemu" "$stage/one/monitor" <<'PY'
import resource, subprocess, sys
def limits():
    resource.setrlimit(resource.RLIMIT_FSIZE, (131072, 131072))
p = subprocess.run(sys.argv[2:], capture_output=True, timeout=5, preexec_fn=limits)
expected = b'refused: target-admission-disabled\n' if sys.argv[1] == 'disabled' else b''
if (p.returncode, p.stdout, p.stderr) != (2, b'', expected):
    raise SystemExit('full-engine production executable did not refuse exactly')
PY
if [[ $mode == capture ]]; then
  mkdir -m 0700 "$stage/full-duration-fixtures"
  timeout 260 python3 "$here/full-duration.py" --compiler "$compiler" --qemu "$qemu" \
    --work-root "$stage/full-duration-fixtures" --output "$stage/full-duration-evidence" >"$stage/full-duration.json" 2>"$stage/full-duration.stderr"
  timeout 45 unshare --user --map-root-user --mount --pid --fork --kill-child=KILL --mount-proc \
    python3 "$here/test-disconnect.py" --compiler "$compiler" --qemu "$qemu" \
    --package "$managed/userspace-dfeb746505b7ad01423e91e952e76620f845b048ae2e8c5cf8a311e0d4443e60" \
    --work-root "$stage" --output "$stage/disconnect-evidence" >"$stage/disconnect.json" 2>"$stage/disconnect.stderr"
  install -m 0600 "$stage/full-duration.json" "$stage/package/full-duration.json"
  install -m 0600 "$stage/disconnect.json" "$stage/package/disconnect.json"
  mv "$stage/disconnect-evidence" "$stage/package/disconnect-evidence"
  mv "$stage/full-duration-evidence" "$stage/package/full-duration-evidence"
fi
install -m 0700 "$stage/one/monitor" "$stage/package/$binary_name"
install -m 0600 "$stage/one/monitor.map" "$stage/package/monitor.map"
install -m 0600 "$stage/tests.txt" "$stage/package/fixture-tests.txt"
install -m 0600 "$musl/COPYRIGHT" "$stage/package/licenses/musl-COPYRIGHT"
install -m 0600 "$repository/LICENSE" "$stage/package/licenses/repository-LICENSE"
install -m 0600 /usr/share/doc/gcc-12-aarch64-linux-gnu/copyright "$stage/package/licenses/GCC-copyright"
printf 'repository_commit=%s\nproduction_entry=%s\ndevice_action=none\n' "$revision" "$production_entry" >"$stage/package/provenance.txt"
python3 - "$here" "$stage" "$revision" "$binary_name" "$production_entry" <<'PY'
import hashlib, json, pathlib, sys, runpy
here, stage = map(pathlib.Path, sys.argv[1:3])
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
inputs = {p.name: sha(p) for p in [here/'monitor.c', here/'monitor-fixture.c', here/'test-monitor.py', here/'build-monitor.sh', here/'full-duration.py', here/'test-disconnect.py', here/'capture.py', here/'../baseline/scripts/provision.py', here/'../baseline/scripts/buildbox_userspace.py', stage/'musl.tar.gz']}
library = {str(p.relative_to(stage/'musl-install')): sha(p) for p in sorted((stage/'musl-install').rglob('*')) if p.is_file()}
result = {'revision': sys.argv[3], 'inputs': inputs, 'library_inputs': library,
          'stripped_bytes': (stage/'package'/sys.argv[4]).stat().st_size,
          'replicas_identical': True, 'full_engine_retained': True,
          'fixture_scope': 'scaled ARM64 Linux QEMU only; no evdev/VT or full-duration claim',
          'production_entry': sys.argv[5], 'device_action': 'none'}
if sys.argv[5] == 'enabled-admission-v1':
    result['capture_source_identity'] = runpy.run_path(str(here/'capture.py'))['source_identity']()
    result['full_duration_sha256'] = sha(stage/'package/full-duration.json')
    result['disconnect_sha256'] = sha(stage/'package/disconnect.json')
    result['fixture_scope'] = 'scaled ARM64 QEMU, full-duration harmless lifecycle and exact retained Dropbear disconnect; no device'
(stage/'package/manifest.json').write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
PY
(cd "$stage/package"; find . -type f -print0 | sort -z | xargs -0 sha256sum) >"$stage/SHA256SUMS"
mv "$stage/SHA256SUMS" "$stage/package/SHA256SUMS"
identity=$(sha256sum "$stage/package/SHA256SUMS" | awk '{print $1}')
destination="$managed/$kind-$identity"
[[ ! -e $destination && ! -L $destination ]]
mv "$stage/package" "$destination"
publication="$managed/$kind-published"
[[ ! -L $publication ]]
mkdir -p "$publication"
[[ ! -e $publication/$revision && ! -L $publication/$revision && ! -L $publication/.partial ]]
printf '%s\n' "$identity" >"$publication/.partial"
mv "$publication/.partial" "$publication/$revision"
printf 'validated_%s_package=%s\n' "${kind//-/_}" "$destination"
