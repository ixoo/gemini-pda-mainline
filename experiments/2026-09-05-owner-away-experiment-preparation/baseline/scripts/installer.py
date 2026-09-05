# SPDX-License-Identifier: MIT
"""Exact A53 adaptation of the reviewed installer, with no transport API."""
import hashlib
from pathlib import Path
import re
import runpy
import shlex

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
BASE = 'experiments/2026-08-14-mt6797-runtime-provenance-observer/scripts/install-boot2.sh'
DERIVER = 'experiments/2026-09-04-mt6797-thermal-snapshot/scripts/v4_installer_guard.py'
PINS = {BASE: 'deaa0e886a881132dd49ee1e3d5b0e6f776400f51fa86a8d0b7c791e979d12a8',
        DERIVER: '9c72675e3043dcf735c8a368800ce9297ca6c343d81283505e7030de82253211',
        'scripts/boot2-device-guard.sh': '0f0fc88ce4650590c6cb86f0ef5ce22b95b2a0f41c9b39b397e24e39cf9f0ebf'}
RECEIPT_NAME = 'a53-authenticated-baseline-deployment-2'

# A quiescent known-good OS is still required: these observations do not lock
# mounts or swap configuration. No helper enables/disables swap or mounts a FS.
STAGE_LIBRARY = r'''
a53_tmpfs_mount() {
    [[ -d /dev/shm && ! -L /dev/shm ]] || return 1
    [[ "$(readlink -f -- /dev/shm)" == /dev/shm ]] || return 1
    [[ "$(findmnt -rn -o TARGET,FSTYPE --target /dev/shm)" == '/dev/shm tmpfs' ]] || return 1
    [[ "$(stat -c '%u %a' -- /dev/shm)" == '0 1777' ]] || return 1
}
a53_no_swap() {
    awk 'NR != 1 || NF != 5 || $1 != "Filename" || $2 != "Type" || $3 != "Size" || $4 != "Used" || $5 != "Priority" {bad=1} END {exit (bad || NR != 1)}' /proc/swaps
}
a53_stage_identity() {
    local stage=$1 owner mode size links
    [[ "$stage" =~ ^/dev/shm/\.gemini-a53-${EXPECTED_CANDIDATE}\.[A-Za-z0-9]{8}$ ]] || return 1
    [[ -f "$stage" && ! -L "$stage" ]] || return 1
    read -r owner mode size links <<<"$(stat -c '%u %a %s %h' -- "$stage")" || return 1
    [[ "$owner" == 0 && "$mode" == 600 && "$links" == 1 &&
       "$size" =~ ^(0|[1-9][0-9]{0,7})$ ]] || return 1
    (( size <= EXPECTED_SIZE )) || return 1
}
'''

STAGE_FUNCTION = r'''
remote_stage() {
    local action=$1 path=${2:-none}
    "${ssh_command[@]}" "$target" \
        "sudo -n env STAGE_ACTION='$action' EXPECTED_STAGE='$path' EXPECTED_CANDIDATE='$CANDIDATE_SHA256' EXPECTED_SIZE='$BOOT2_SIZE' /bin/bash -s" <<'A53_STAGE'
set -euo pipefail
export LC_ALL=C
umask 077
fail() { printf 'staging refused: %s\n' "$*" >&2; exit 2; }
@LIBRARY@
a53_tmpfs_mount || fail 'staging mount is not the exact tmpfs'
case "$STAGE_ACTION" in
prepare)
    [[ "$EXPECTED_STAGE" == none ]] || fail 'unexpected prepare path'
    a53_no_swap || fail 'active or malformed swap state'
    available=$(df -P -B1 /dev/shm | awk 'NR == 2 && NF == 6 {print $4}')
    [[ "$available" =~ ^[0-9]{1,12}$ ]] && (( available >= EXPECTED_SIZE + 1048576 )) || fail 'insufficient tmpfs space'
    # Only this exact candidate's reconstructible staging copies are eligible.
    # Refuse unexpected names/owners/links before removing any stale file.
    shopt -s nullglob
    set -- /dev/shm/.gemini-a53-"$EXPECTED_CANDIDATE".*
    (( $# <= 1 )) || fail 'multiple stale staging files'
    for item; do a53_stage_identity "$item" || fail 'unsafe stale staging file'; done
    for item; do rm -f -- "$item"; done
    mktemp "/dev/shm/.gemini-a53-$EXPECTED_CANDIDATE.XXXXXXXX"
    ;;
cleanup)
    a53_stage_identity "$EXPECTED_STAGE" || fail 'unsafe cleanup path'
    rm -f -- "$EXPECTED_STAGE"
    ;;
*) fail 'unknown staging action' ;;
esac
A53_STAGE
}
'''.replace('@LIBRARY@', STAGE_LIBRARY)

CLEANUP = r'''stage=
readback_tmp=
cleanup() {
    local status=$?
    trap - EXIT
    if [[ -n "${stage:-}" ]]; then
        remote_stage cleanup "$stage" >/dev/null || {
            printf 'error: private tmpfs staging cleanup unconfirmed\n' >&2
            [[ "$status" != 0 ]] || status=2
        }
    fi
    if [[ -n "${readback_tmp:-}" && -f "$readback_tmp" && ! -L "$readback_tmp" ]]; then
        printf 'discarded_readback_bytes=%s\ndiscarded_readback_sha256=%s\n' \
            "$(wc -c <"$readback_tmp" | tr -d ' ')" "$(sha256sum "$readback_tmp" | awk '{print $1}')" >&2
        rm -f -- "$readback_tmp" || status=2
    fi
    exit "$status"
}
trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM
'''


def digest(data):
    return hashlib.sha256(data).hexdigest()


def pinned_sources(repo=REPO):
    sources = {}
    for relative, expected in PINS.items():
        path = repo / relative
        if path.is_symlink() or not path.is_file() or digest(path.read_bytes()) != expected:
            raise ValueError('reviewed installer input changed: ' + relative)
        sources[relative] = path.read_bytes()
    return sources


def derive(sources, repo, candidate, foundation, userspace):
    """Pure text derivation. Callers must validate the private candidate first."""
    if set(sources) != set(PINS) or any(digest(sources[path]) != sha for path, sha in PINS.items()):
        raise ValueError('installer input pin differs')
    repo, candidate, foundation, userspace = map(Path, (repo, candidate, foundation, userspace))
    candidate_sha = digest((candidate / 'boot2-padded.img').read_bytes())
    manifest_sha = digest((candidate / 'candidate.json').read_bytes())
    if not re.fullmatch(r'candidate-[0-9a-f]{64}', candidate.name):
        raise ValueError('candidate directory identity')
    deriver = runpy.run_path(str(REPO / DERIVER))
    source = deriver['derive'](sources[BASE].decode(), sources['scripts/boot2-device-guard.sh'])
    # Recover the immutable historical staging root from its pinned source,
    # instead of publishing a home-directory path as a new policy/input.
    legacy_match = re.search(r'mktemp (/[a-z]+/[a-z]+)/\.gemini-provenance-observer', sources[BASE].decode())
    if legacy_match is None:
        raise ValueError('historical staging root absent')
    legacy_home = legacy_match.group(1)

    def replace(old, new, count=1):
        nonlocal source
        old = old.replace('@LEGACY_HOME@', legacy_home)
        if source.count(old) != count:
            raise ValueError('A53 installer anchor changed: ' + old[:70])
        source = source.replace(old, new)

    old_ssh = """ssh_command=(
\tssh -o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=5
\t-o ServerAliveCountMax=6 -o IdentitiesOnly=yes -o IdentityAgent=none
\t-o StrictHostKeyChecking=yes -i "$identity"
)"""
    new_ssh = """recovery_trust="$repo_root/artifacts/credentials/a53-recovery-known_hosts"
[[ -f "$recovery_trust" && ! -L "$recovery_trust" ]] || die 'recovery trust file missing'
[[ "$(sha256sum "$recovery_trust" | awk '{print $1}')" == d43262bd1f9c76d02eb633900f5e5502e2342d6c1b41586a2d7e524a2293768f ]] || die 'recovery trust identity changed'
ssh_command=(
\tssh -F /dev/null -o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=5
\t-o ServerAliveCountMax=6 -o IdentitiesOnly=yes -o IdentityAgent=none
\t-o StrictHostKeyChecking=yes -o "UserKnownHostsFile=$recovery_trust"
\t-o GlobalKnownHostsFile=/dev/null -o UpdateHostKeys=no
\t-o HostKeyAlgorithms=ssh-ed25519 -o PubkeyAcceptedAlgorithms=ssh-ed25519
\t-o PasswordAuthentication=no -o KbdInteractiveAuthentication=no
\t-o ProxyCommand=none -o ProxyJump=none -o ControlMaster=no -o ControlPath=none
\t-o ClearAllForwardings=yes -o ForwardAgent=no -o ForwardX11=no -i "$identity"
)"""
    replace(old_ssh, new_ssh)
    replace('ea603c1b1a64d4f1aa9cac3e53957a3e858a7ce04127f1aef36d4b0e8173cb02', candidate_sha)
    replace('ad92d496dfb4fd183c35e6e0f32ce626b2045528657fb2567d8561dd02540f1a', manifest_sha)
    replace('gemian-runtime-provenance-observer-rndis-1d303dda10b4', candidate.name)
    replace('2026-08-14-mt6797-runtime-provenance-observer', 'a53-authenticated-baseline')
    replace('provenance-observer', 'a53-authenticated-baseline', 7)
    replace('a53-authenticated-baseline-deployment-*', RECEIPT_NAME, 2)
    replace('a53-authenticated-baseline-deployment-N', RECEIPT_NAME)
    old_root = 'script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"\nrepo_root="$(cd -- "$script_dir/../../.." && pwd -P)"'
    replace(old_root, 'repo_root=' + shlex.quote(str(repo)))
    replace('manifest="$candidate_dir/SHA256SUMS"', 'manifest="$candidate_dir/candidate.json"')
    replace('size="$(stat -f \'%z\' "$candidate" 2>/dev/null || stat -c \'%s\' "$candidate")"',
            'size="$(python3 -c \'import os,sys; print(os.stat(sys.argv[1], follow_symlinks=False).st_size)\' "$candidate")"')
    replace('identity_mode="$(stat -f \'%Lp\' "$identity" 2>/dev/null || stat -c \'%a\' "$identity")"',
            'identity_mode="$(python3 -c \'import os,stat,sys; print(format(stat.S_IMODE(os.stat(sys.argv[1], follow_symlinks=False).st_mode), "o"))\' "$identity")"')
    script_dir = repo / HERE.relative_to(REPO)
    validator = script_dir / 'validate-candidate.py'
    receipt_parser = script_dir / 'deployment_receipt.py'
    validation = shlex.join(['python3', str(validator), '--foundation', str(foundation),
                            '--userspace', str(userspace)]) + ' --candidate "$candidate_dir"'
    old_manifest = '(cd "$candidate_dir" && sha256sum --check --strict SHA256SUMS >/dev/null) ||\n\tdie \'candidate manifest validation failed\''
    replace(old_manifest, validation + ' >/dev/null || die \'independent candidate validation failed\'')
    # Bind the executable to these local inputs too, so replacing it after
    # derivation cannot silently alter the validation or receipt interpretation.
    checks = ''
    for path in (validator, receipt_parser):
        checks += '[[ "$(sha256sum ' + shlex.quote(str(path)) + ' | awk \'{print $1}\')" == ' + digest(path.read_bytes()) + " ]] || die 'validation tool changed'\n"
    replace('for command in awk basename', checks + 'for command in python3 awk basename')
    replace('fail() { printf \'error: %s\\n\' "$*" >&2; exit 2; }\n',
            'fail() { printf \'error: %s\\n\' "$*" >&2; exit 2; }\n' + STAGE_LIBRARY)
    old_stage = '''\t[[ "$EXPECTED_STAGE" =~ ^@LEGACY_HOME@/\\.gemini-a53-authenticated-baseline\\.[A-Za-z0-9]+$ ]] ||
\t\tfail 'unsafe staging path'
\t[[ -f "$EXPECTED_STAGE" && ! -L "$EXPECTED_STAGE" ]] || fail 'staging file is unsafe'
\tread -r owner mode stage_size <<<"$(stat -c '%U %a %s' "$EXPECTED_STAGE")"
\t[[ "$owner" == gemini && "$mode" == 600 && "$stage_size" == "$EXPECTED_SIZE" ]] ||
\t\tfail 'staging identity changed'
'''
    replace(old_stage, '''\ta53_tmpfs_mount && a53_no_swap && a53_stage_identity "$EXPECTED_STAGE" || fail 'private tmpfs staging gate failed'
\t[[ "$(stat -c '%s' -- "$EXPECTED_STAGE")" == "$EXPECTED_SIZE" ]] || fail 'staging size changed'
''')
    write = '\tboot2_device_guard "$target" "$majmin" "$root_major_minor" >/dev/null || fail \'pre-write block identity changed\'\n'
    replace(write, '\ta53_tmpfs_mount && a53_no_swap && a53_stage_identity "$EXPECTED_STAGE" || fail \'staging changed before write\'\n' + write)
    replace('single_value() {\n', STAGE_FUNCTION + '\nsingle_value() {\n')
    old_cleanup = '''stage=
cleanup_stage() {
\t[[ -z "${stage:-}" ]] || "${ssh_command[@]}" "$target" \\
\t\t"test ! -e '$stage' || rm -f -- '$stage'" >/dev/null 2>&1 || true
}
trap cleanup_stage EXIT HUP INT TERM
'''
    replace(old_cleanup, CLEANUP)
    replace("stage=\"$(\"${ssh_command[@]}\" \"$target\" 'umask 077; mktemp @LEGACY_HOME@/.gemini-a53-authenticated-baseline.XXXXXXXX')\"",
            'stage="$(remote_stage prepare)" || die \'private tmpfs staging preparation failed\'')
    replace('[[ "$stage" =~ ^@LEGACY_HOME@/\\.gemini-a53-authenticated-baseline\\.[A-Za-z0-9]+$ ]]',
            '[[ "$stage" =~ ^/dev/shm/\\.gemini-a53-${CANDIDATE_SHA256}\\.[A-Za-z0-9]{8}$ ]]')
    upload = 'set -euo pipefail\nEXPECTED_STAGE=$1\nEXPECTED_CANDIDATE=$2\nEXPECTED_SIZE=$3\n' + STAGE_LIBRARY + r'''
a53_tmpfs_mount && a53_no_swap && a53_stage_identity "$EXPECTED_STAGE" || exit 2
[[ "$(stat -c '%s' -- "$EXPECTED_STAGE")" == 0 ]] || exit 2
cat >"$EXPECTED_STAGE"
a53_tmpfs_mount && a53_no_swap && a53_stage_identity "$EXPECTED_STAGE" || exit 2
[[ "$(stat -c '%s' -- "$EXPECTED_STAGE")" == "$EXPECTED_SIZE" ]] || exit 2
'''
    upload_command = shlex.quote('sudo -n /bin/bash -c ' + shlex.quote(upload) + ' a53-upload')
    old_upload = '''\t"${ssh_command[@]}" "$target" \\
\t\t"test -f '$stage' && test ! -L '$stage' && cat >'$stage' && chmod 600 '$stage'" \\
\t\t<"$candidate" || die 'candidate upload failed'
'''
    replace(old_upload, '\t# Expand this command only in the remote shell.\n\t# shellcheck disable=SC2016\n\tupload_command=' + upload_command + '''
\t"${ssh_command[@]}" "$target" "$upload_command '$stage' '$CANDIDATE_SHA256' '$BOOT2_SIZE'" \\
\t\t<"$candidate" || die 'candidate upload failed'
''')
    replace('"${ssh_command[@]}" "$target" "rm -f -- \'$stage\'"', 'remote_stage cleanup "$stage" || die \'private staging cleanup failed\'')
    replace("printf 'experiment=a53-authenticated-baseline\\n'", "printf 'experiment=a53-authenticated-baseline\\ncandidate_manifest_sha256=" + manifest_sha + "\\n'")
    replace('poweroff_rc=$?\nset -e\n', 'poweroff_rc=$?\nset -e\n[[ "$poweroff_rc" == 0 || "$poweroff_rc" == 255 ]] || die \'shutdown request failed\'\n')
    final_receipt = '} >>"$summary"\n(cd "$evidence_dir" && sha256sum deployment-summary.txt >SHA256SUMS)'
    check_receipt = shlex.join(['python3', str(receipt_parser), '--candidate-sha256', candidate_sha,
                              '--candidate-manifest-sha256', manifest_sha])
    replace(final_receipt, '} >>"$summary"\n' + check_receipt + ' --receipt "$summary" >/dev/null || die \'deployment receipt refused\'\n(cd "$evidence_dir" && sha256sum deployment-summary.txt >SHA256SUMS)')
    # All successful local temporary state has been removed before exit. Keep
    # EXIT cleanup active so a final signal still cannot resume the installer.
    replace('trap - EXIT HUP INT TERM\n', '')
    if legacy_home in source or 'SHA256SUMS >/dev/null' in source or source.count('of="$target"') != 1:
        raise ValueError('obsolete staging/manifest or write inventory')
    return source
