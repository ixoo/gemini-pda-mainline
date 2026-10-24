#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Console progress indicator, opt-in: patch a work directory's rendered host
files so that, when TP_CONSOLE_PROGRESS=1 is in the run environment, the
device-side leaf and the throughput helper's device script rewrite a fixed
six-line block on the frame-buffer console (/dev/tty0) at their stage and
chunk markers. Unset, nothing changes. The screen is not evidence and is
never graded; the leaf reports how many lines it wrote.

usage: console_progress.py <work-dir>   (after bind-candidate rendered hosts/)
"""
import sys
from pathlib import Path

LEAF_SAY = r'''# Console progress indicator (host-side opt-in injection; the screen is not
# evidence). Six fixed lines, cursor-addressed, rewritten in place. The first
# write error ends all writes; nothing here can fail the run.
CP=1
CP_VARIANT='__CP_VARIANT__'
cp_lines=0; cp_dead=0; cp_t0=$($BB cut -d. -f1 /proc/uptime)
cp_link() {
    /lib/ld-linux-aarch64.so.1 --library-path /lib /bin/iw dev wlan0 link 2>/dev/null |
        $BB awk '/signal:/{s=$2} /freq:/{f=$2} /width:/{w=$2} END{if(s=="") print "-"; else printf "%s dBm  %s MHz  %s\n", s, f, w}'
}
cp_say() {
    [ "$CP" = 1 ] && [ "$cp_dead" = 0 ] || return 0
    cp_el=$(( $($BB cut -d. -f1 /proc/uptime) - cp_t0 ))
    if $BB printf '\033[H\033[K%s\n\033[K%s\n\033[K%s\n\033[K%s\n\033[K%s\n\033[K%s\n' \
        "gemini-pda  wifi $CP_VARIANT   boot ${EXPECTED_BOOT%%-*}" \
        "stage   $1" \
        "cycle   1/1     chunk  -/5  -" \
        "rate    -          elapsed  ${cp_el}s" \
        "link    $(cp_link)" \
        "verdict $2" > /dev/tty0 2>/dev/null; then cp_lines=$((cp_lines+6)); else cp_dead=1; fi
    return 0
}
cp_say capture running
'''

LEAF_EDITS = [
    ("stage=start\n", "stage=start\n" + LEAF_SAY),
    ("stage=supplicant_start\n", "stage=supplicant_start\ncp_say join running\n"),
    ("            wifi_sshd_ready=1\n", "            wifi_sshd_ready=1\n            cp_say data running\n"),
    ("stage=finish\n", "stage=finish\ncp_say teardown running\n"),
    ("stage=boot_after\n",
     "stage=boot_after\n"
     "if [ \"$overall_rc\" = 0 ]; then cp_say done PASS; else cp_say done \"FAILED: rc=$overall_rc\"; fi\n"
     "$BB printf 'console_progress_lines=%s console_progress_dead=%s\\n' \"$cp_lines\" \"$cp_dead\"\n"),
]

HELPER_CP = r'''cp() { [ "__CP_FLAG__" = 1 ] || return 0; printf "$@" > /dev/tty0 2>/dev/null || true; }
'''


def inject_leaf(leaf: bytes, variant: str) -> bytes:
    text = leaf.decode()
    for old, new in LEAF_EDITS:
        if text.count(old) != 1:
            raise ValueError('console progress: leaf anchor changed: %r' % old)
        text = text.replace(old, new.replace('__CP_VARIANT__', variant))
    return text.encode()


def patch_prepare(path: Path):
    s = path.read_text()
    old = "    leaf = retained.replace(old,b'    pc_result=0 # throughput: no periodic probes during measurement')\n"
    if s.count(old) != 1:
        raise ValueError('prepare anchor changed')
    new = old + ("    console_progress = os.environ.get('TP_CONSOLE_PROGRESS') == '1'\n"
                 "    if console_progress:\n"
                 "        sys.path.insert(0, str(here))\n"
                 "        import console_progress as cp_mod\n"
                 "        leaf = cp_mod.inject_leaf(leaf, os.environ.get('TP_CONSOLE_VARIANT', 'run'))\n")
    s = s.replace(old, new)
    old = "    plan = {'schema':1,"
    if s.count(old) != 1:
        raise ValueError('plan anchor changed')
    s = s.replace(old, "    plan = {'schema':1,'console_progress':console_progress,'console_is_evidence':False,")
    old = "           'TP_SOURCE_ROOT':str(cohort),"
    if s.count(old) != 1:
        raise ValueError('env anchor changed')
    s = s.replace(old, "           'TP_CONSOLE_PROGRESS':'1' if console_progress else '0','TP_CONSOLE_VARIANT':os.environ.get('TP_CONSOLE_VARIANT','run'),\n" + old)
    path.write_text(s)


def patch_helper(path: Path):
    s = path.read_text()
    old = "clock() { $BB awk '{printf \"%.0f\\n\", $1*1000000000}' /proc/uptime; }\n"
    if s.count(old) != 1:
        raise ValueError('helper clock anchor changed')
    s = s.replace(old, old + HELPER_CP)
    old = "        printf 'TP2_PROGRESS direction=%s chunk=%s phase=start ns=' \"$dir\" \"$i\"; clock\n"
    if s.count(old) != 1:
        raise ValueError('helper start anchor changed')
    s = s.replace(old, old + "        cp '\\033[3;1H\\033[Kcycle   1/1     chunk  %s/5  %s\\n' \"$i\" \"$dir\"; t0=$(clock)\n")
    old = "        printf 'TP2_PROGRESS direction=%s chunk=%s phase=end rc=%s bytes=%s ns=' \"$dir\" \"$i\" \"$rc\" \"$n\"; clock\n"
    if s.count(old) != 1:
        raise ValueError('helper end anchor changed')
    s = s.replace(old, old + ("        t1=$(clock); if [ \"$dir\" = RX ] && [ \"$t1\" -gt \"$t0\" ]; then r=$($BB awk -v b=\"$n\" -v d=\"$((t1-t0))\" 'BEGIN{printf \"%.2f\", b*8000/d}'); else r=-; fi\n"
                              "        cp '\\033[4;1H\\033[Krate    %s Mbit/s\\n' \"$r\"\n"))
    old = "    script = r'''\n"
    if s.count(old) != 1:
        raise ValueError('helper script anchor changed')
    # Substitute the flag at composition time from the run environment.
    old2 = "def remote_script(boot, host):\n"
    s = s.replace(old2, "import os as _cp_os\n\n\n" + old2, 1) if 'import os as _cp_os' not in s else s
    marker = "    script = r'''"
    idx = s.index(marker)
    end = s.index("'''", idx + len(marker)) + 3
    s = s[:end] + ".replace('__CP_FLAG__', '1' if _cp_os.environ.get('TP_CONSOLE_PROGRESS') == '1' else '0')" + s[end:]
    path.write_text(s)


def main():
    work = Path(sys.argv[1])
    hosts = work / 'hosts'
    patch_prepare(hosts / 'throughput-prepare.py')
    patch_helper(hosts / 'throughput-helper.py')
    (hosts / 'console_progress.py').write_text(Path(__file__).read_text())
    for name in ('throughput-prepare.py', 'throughput-helper.py', 'console_progress.py'):
        compile((hosts / name).read_text(), str(hosts / name), 'exec')
    print('console progress injected into', hosts)


if __name__ == '__main__':
    main()
