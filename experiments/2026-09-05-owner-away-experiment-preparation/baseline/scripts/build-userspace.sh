#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
set -euo pipefail
umask 077
export LC_ALL=C SOURCE_DATE_EPOCH=0 PYTHONDONTWRITEBYTECODE=1
[[ $# == 2 ]] || { echo 'usage: build-userspace.sh EXACT_REVISION MANAGED_ROOT' >&2; exit 2; }
revision=$1
managed=$2
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
repository=$(git -C "$here" rev-parse --show-toplevel)
[[ $(uname -s) == Linux && $(uname -m) == x86_64 ]]
[[ $(git -C "$repository" rev-parse HEAD) == "$revision" ]]
[[ -z $(git -C "$repository" status --porcelain) ]]
[[ -d $managed && ! -L $managed && $managed == /workspace/* ]]
[[ $(git -C "$repository" remote get-url origin) == https://github.com/ixoo/gemini-pda-mainline.git ]]
git -C "$repository" branch -r --contains "$revision" | grep -q origin/
exec 9>"$managed/.userspace.lock"
flock -n 9
# One fixed staging name permits safe recovery after SIGKILL while holding lock.
stage="$managed/.a53-userspace-stage"
[[ ! -L $stage ]]
if [[ -e $stage ]]; then rm -rf -- "$stage"; fi
mkdir -m 0700 "$stage"
cleanup() { rm -rf -- "$stage"; }
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' HUP TERM
df -Pk "$managed" | awk 'NR==2 {if ($4 < 524288) exit 1}'
curl --fail --location --max-time 120 --output "$stage/source.tar.bz2" \
  https://matt.ucc.asn.au/dropbear/releases/dropbear-2026.94.tar.bz2
printf '%s  %s\n' e098034a843699200c8c977a991fff73159735bf795d5f72ef672c41a6b1ae81 "$stage/source.tar.bz2" | sha256sum --check --strict
tar -xjf "$stage/source.tar.bz2" -C "$stage"
source_dir="$stage/dropbear-2026.94"
mkdir "$stage/package" "$stage/package/licenses"
for replica in one two; do
  mkdir "$stage/$replica"
  install -m 0600 "$here/localoptions.h" "$stage/$replica/localoptions.h"
  (
    cd "$stage/$replica"
    "$source_dir/configure" --host=aarch64-linux-gnu --enable-static \
      --disable-zlib --disable-syslog --disable-shadow --disable-lastlog \
      --disable-utmp --disable-utmpx --disable-wtmp --disable-wtmpx \
      CFLAGS="-Os -ffile-prefix-map=$stage=. -fdebug-prefix-map=$stage=." \
      LDFLAGS=-static >configure.log 2>&1
    make -j4 PROGRAMS='dropbear dropbearkey dropbearconvert' >build.log 2>&1
    grep -q -- '-DLOCALOPTIONS_H_EXISTS' build.log
    aarch64-linux-gnu-gcc -dM -E -DLOCALOPTIONS_H_EXISTS -I. -I"$source_dir/src" \
      -include "$source_dir/src/options.h" - </dev/null >effective-options.txt
    while IFS= read -r option; do
      [[ $option == '#define '* ]] || continue
      grep -Fxq "$option" effective-options.txt
    done <localoptions.h
  )
done
for binary in dropbear dropbearkey dropbearconvert; do
  cmp "$stage/one/$binary" "$stage/two/$binary"
  aarch64-linux-gnu-readelf -h "$stage/one/$binary" | grep -q AArch64
  if aarch64-linux-gnu-readelf -l "$stage/one/$binary" | grep -q INTERP; then exit 1; fi
  install -m 0700 "$stage/one/$binary" "$stage/package/$binary"
done
for replica in one two; do
  for helper in keyboard-observe kmsg-capture; do
    if [[ $helper == keyboard-observe ]]; then
      helper_source="$here/../keyboard/keyboard-observe.c"
    else
      helper_source="$here/src/kmsg-capture.c"
    fi
    aarch64-linux-gnu-gcc -std=c11 -O2 -Wall -Wextra -Werror -static \
      "-ffile-prefix-map=$repository=." "$helper_source" -o "$stage/$replica/$helper"
  done
done
for helper in keyboard-observe kmsg-capture; do
  cmp "$stage/one/$helper" "$stage/two/$helper"
  install -m 0700 "$stage/one/$helper" "$stage/package/$helper"
done
python3 "$here/test-kmsg.py" >"$stage/package/kmsg-parser-tests.txt" 2>&1
install -m 0600 "$source_dir/LICENSE" "$stage/package/licenses/Dropbear-LICENSE"
install -m 0600 "$source_dir/libtomcrypt/LICENSE" "$stage/package/licenses/LibTomCrypt-LICENSE"
install -m 0600 "$source_dir/libtommath/LICENSE" "$stage/package/licenses/LibTomMath-LICENSE"
install -m 0600 "$here/localoptions.h" "$stage/package/localoptions.h"
install -m 0600 "$stage/one/effective-options.txt" "$stage/package/effective-options.txt"
python3 - "$here" "$stage/package/inputs.json" <<'PY'
import hashlib, json, pathlib, sys
here = pathlib.Path(sys.argv[1])
names = ('localoptions.h', 'scripts/build-userspace.sh', 'scripts/provision.py',
         'scripts/test-auth.py', 'src/kmsg-capture.c', '../keyboard/keyboard-observe.c',
         '../keyboard/protocol.h')
pathlib.Path(sys.argv[2]).write_text(json.dumps({name: hashlib.sha256((here / name).read_bytes()).hexdigest()
                                              for name in names}, indent=2, sort_keys=True) + '\n')
PY
python3 "$here/scripts/test-auth.py" --package "$stage/package" --work-root "$stage" >"$stage/package/auth-tests.json"
curl --fail --location --max-time 120 --output "$stage/busybox.deb" \
  https://ports.ubuntu.com/ubuntu-ports/pool/main/b/busybox/busybox-static_1.36.1-6ubuntu3.1_arm64.deb
printf '%s  %s\n' d96535e0402c011e0ee43449799df2f4504d44b842e4f2b3a6cbc845508eaafc "$stage/busybox.deb" | sha256sum --check --strict
dpkg-deb -x "$stage/busybox.deb" "$stage/busybox-root"
busybox="$stage/busybox-root/usr/bin/busybox"
printf '%s  %s\n' 52151e7f322f926b64049cdaa1410dc3ea6485525e0624b05813791c219ae933 "$busybox" | sha256sum --check --strict
python3 "$here/scripts/test-shell.py" --busybox "$busybox" --work-root "$stage" >"$stage/package/shell-tests.json"
EMMC_TEST_BUSYBOX="$busybox" EMMC_TEST_WORK_ROOT="$stage" python3 "$here/../emmc/test_packet.py" >"$stage/package/emmc-shell-tests.txt" 2>&1
install -m 0600 "$stage/busybox-root/usr/share/doc/busybox-static/copyright" "$stage/package/licenses/BusyBox-copyright"
{
  printf 'repository_commit=%s\nsource_sha256=%s\n' "$revision" e098034a843699200c8c977a991fff73159735bf795d5f72ef672c41a6b1ae81
  printf 'compiler=%s\n' "$(aarch64-linux-gnu-gcc --version | head -1)"
  sha256sum "$(command -v aarch64-linux-gnu-gcc)" "$(command -v aarch64-linux-gnu-ld)" | sed 's@  .*/@  @'
  printf 'independent_binary_builds=2\nbyte_identical=yes\ndevice_action=none\n'
} >"$stage/package/provenance.txt"
(cd "$stage/package"; find . -type f -print0 | sort -z | xargs -0 sha256sum) >"$stage/SHA256SUMS"
mv "$stage/SHA256SUMS" "$stage/package/SHA256SUMS"
identity=$(sha256sum "$stage/package/SHA256SUMS" | awk '{print $1}')
destination="$managed/userspace-$identity"
[[ ! -e $destination && ! -L $destination ]]
mv "$stage/package" "$destination"
printf 'validated_userspace_package=%s\n' "$destination"
