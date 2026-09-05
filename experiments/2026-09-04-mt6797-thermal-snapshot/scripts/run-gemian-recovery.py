#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""One recovery run from an exact known-good-OS deployment/shutdown receipt."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CORE_SHA = 'da6de59f9be659be9b2e7e45a777028a6266cbc238188890ad6434f43eaf0364'
INSTALLER_SHA = 'c921cb5e11b74fc76bdeda893482db908cd17ae151985317bf2875a6d5bbc6e4'
GEMIAN_BOOT = '5d45171e-6c70-4fe4-99b6-715ac22ca826'
RECEIPT = ROOT / 'artifacts/device-install-evidence/thermal-snapshot-deployment-recovery-gemian-1/deployment-summary.txt'
RUN = ROOT / 'artifacts/runtime-captures/thermal-snapshot-recovery-gemian-1'


def checked(path, expected):
    if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError('source identity changed: ' + path.name)
    return path.read_text()


checked(HERE / 'run-recovery.py', CORE_SHA)
spec = importlib.util.spec_from_file_location('recovery_core', HERE / 'run-recovery.py')
CORE = importlib.util.module_from_spec(spec)
spec.loader.exec_module(CORE)


def sources():
    checked(HERE / 'run-recovery.py', CORE_SHA)
    checked(HERE / 'install-recovery-boot2.sh', INSTALLER_SHA)
    CORE.sources()
    checked(CORE.SOURCE_EVIDENCE, CORE.SOURCE_EVIDENCE_SHA)


def receipt():
    directory = RECEIPT.parent
    if directory.is_symlink() or not directory.is_dir() or directory.stat().st_mode & 0o777 != 0o700:
        raise ValueError('unsafe deployment evidence directory')
    if {p.name for p in directory.iterdir()} != {'deployment-summary.txt', 'SHA256SUMS'}:
        raise ValueError('incomplete or extra deployment evidence')
    for path in (RECEIPT, directory / 'SHA256SUMS'):
        if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o777 != 0o600:
            raise ValueError('unsafe deployment evidence file')
    raw = RECEIPT.read_text()
    sha = hashlib.sha256(raw.encode()).hexdigest()
    if (directory / 'SHA256SUMS').read_text() != sha + '  deployment-summary.txt\n':
        raise ValueError('deployment manifest changed')
    boot = CORE.module('observation_protocol').receipt(raw)
    if boot != GEMIAN_BOOT:
        raise ValueError('unexpected source Gemian boot')
    return raw, sha


def workload(capture, deployment):
    protocol = CORE.module('observation_protocol')
    state = CORE.module('observation_state')
    builder = CORE.module('build-recovery-runtime')
    classifier = CORE.module('classify-recovery-runtime')
    boot = protocol.receipt(deployment)
    raw = capture.transport((HERE / 'remote-observation-state.sh').read_text())
    capture.save('preflight.txt', raw)
    pre = state.validate_state(raw, record_identity=protocol.RECORD, deployment_boot=boot)
    if pre['boot_id'] in classifier.CLOSED_BOOTS | {GEMIAN_BOOT}:
        raise ValueError('consumed boot identity')
    if int(pre['thermal_temperature_millicelsius']) % 100:
        raise ValueError('initial temperature precision refusal')
    if pre['thermal_snapshot_path'] != protocol.PATH:
        raise ValueError('thermal device path changed')
    _, late = CORE.frame(raw)
    program = builder.build(pre['boot_id'])
    capture.save('program.sh', program)
    capture.seal('workload.requested')
    raw = capture.transport(program, workload=True)
    capture.save('runtime.txt', raw)
    result = classifier.classify(raw, pre['boot_id'], int(pre['thermal_temperature_millicelsius']))
    capture.save('runtime-classification.json', json.dumps(result, indent=2, sort_keys=True) + '\n')
    terminal = classifier.scalar(raw, 'post_status')
    post = capture.transport((HERE / 'remote-observation-state.sh').read_text())
    capture.save('postflight.txt', post)
    CORE.postflight(post, pre, late, terminal)
    result.update({'postflight': 'pass', 'host_postflight': 'pass',
                   'transport_sessions': capture.sessions, 'ordinary_thermal_reads': 2,
                   'workload_requests': 1, 'retries': 0, 'candidate_sha256': protocol.CANDIDATE,
                   'cycle_source': 'exact-Gemian-deployment-and-shutdown', 'source_boot_id': boot})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    sources()
    deployment, sha = receipt()
    if not args.execute:
        print('recovery_protocol=Gemian-cycle receipt=pass device_action=none')
        return 0
    link = CORE.module('run-observation').interface()
    capture = CORE.Capture(RUN, link)
    try:
        capture.save('deployment-summary.txt', deployment)
        capture.save('source-runtime-classification.json', CORE.SOURCE_EVIDENCE.read_text())
        result = workload(capture, deployment)
        result['deployment_receipt_sha256'] = sha
        capture.save('classification.json', json.dumps(result, indent=2, sort_keys=True) + '\n')
    except BaseException as error:
        capture.save('classification.json', json.dumps({'classification': 'refused-or-incomplete',
                     'reason': str(error), 'retry': 'forbidden',
                     'transport_sessions': capture.sessions}) + '\n')
        raise
    finally:
        capture.finish()
    print('classification=' + result['classification'])
    return 3 if result['classification'] == 'bounded-recovery-comparison-rejected' else 0


if __name__ == '__main__':
    raise SystemExit(main())
