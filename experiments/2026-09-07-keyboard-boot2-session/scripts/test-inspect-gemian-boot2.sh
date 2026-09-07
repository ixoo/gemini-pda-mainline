#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
set -euo pipefail
export LC_ALL=C
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
script="$here/inspect-gemian-boot2.sh"
bash -n "$script"
shellcheck "$script"
grep -Fq "PARTNAME) partname=\$value" "$script"
# These are literal source assertions, not shell expressions in this test.
# shellcheck disable=SC2016
grep -Fq '[ "$devtype" = partition ] && [ "$partname" = boot2 ]' "$script"
# shellcheck disable=SC2016
grep -Fq '[ "$source" != "$target" ]' "$script"
# shellcheck disable=SC2016
grep -Fq 'checksum=$(sha256sum "$target"' "$script"
grep -Fq 'partition_writes=0' "$script"
if grep -Eq '(^|[[:space:]])(dd|poweroff|reboot|shutdown|mount|umount)([[:space:]]|$)' "$script"; then
	printf 'write, power or mount command found\n' >&2
	exit 1
fi
printf 'inspect-boot2-static=pass\n'
