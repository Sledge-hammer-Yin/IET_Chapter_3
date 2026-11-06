"""Wait for the existing GLIO backend to finish the available trajectory."""
import argparse
import json
import os
from pathlib import Path
import signal
import time


def last_time(path):
    try:
        with path.open('rb') as stream:
            stream.seek(0, 2)
            size = stream.tell()
            stream.seek(max(0, size-8192))
            lines = stream.read().splitlines()
        for line in reversed(lines):
            fields = line.split(b',')
            if len(fields) == 12:
                return float(fields[0])
    except (OSError, ValueError):
        pass
    return None


def identity(pid):
    proc = Path('/proc') / str(pid)
    if proc.stat().st_uid != os.getuid():
        raise RuntimeError('Process is not owned by this account')
    return (proc/'stat').read_text().rsplit(')',1)[1].split()[19]


def wrapper_for(folder):
    argument = ('result_dir:=' + str(folder)).encode()
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():
            continue
        try:
            if proc.stat().st_uid != os.getuid():
                continue
            args = (proc/'cmdline').read_bytes().split(b'\0')
            if argument not in args or not any(b'roslaunch' in item for item in args):
                continue
            stat = (proc/'stat').read_text().rsplit(')',1)[1].split()
            parent = int(stat[1])
            parent_args = (Path('/proc')/str(parent)/'cmdline').read_bytes().split(b'\0')
            if str(folder).encode() in parent_args and (Path('/proc')/str(parent)/'comm').read_text().strip() == 'bash':
                return parent, identity(parent)
        except (OSError, RuntimeError):
            continue
    raise RuntimeError('Cannot identify the matching private run wrapper')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('run_dir', type=Path)
    parser.add_argument('--mode', default='TC_Surface')
    parser.add_argument('--hold-running-wrapper', action='store_true')
    parser.add_argument('--timeout', type=float, default=600)
    args = parser.parse_args()
    folder = args.run_dir.resolve()
    if not str(folder).startswith('/data/users/taslab_zxp/outputs/GLIO/Deep-Urban-1/'):
        raise ValueError('Unexpected output folder')
    held = False
    wrapper = None
    started = None
    def interrupted(signum, frame):
        raise KeyboardInterrupt('Backend wait interrupted')
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        if args.hold_running_wrapper:
            wrapper = wrapper_for(folder)
            deadline = time.monotonic()+7200
            while not (folder/'playback_finished.txt').exists():
                if identity(wrapper[0]) != wrapper[1]:
                    raise RuntimeError('Run wrapper changed')
                if time.monotonic()>deadline:
                    raise RuntimeError('Playback wait expired')
                time.sleep(0.5)
            if identity(wrapper[0]) != wrapper[1]:
                raise RuntimeError('Run wrapper changed')
            os.kill(wrapper[0], signal.SIGSTOP)
            held = True
        started = time.monotonic()
        previous = None
        stable_since = started
        target = 'lc_result.csv' if args.mode=='LC' else 'tc_batch_result.csv'
        while True:
            latest = last_time(folder/'tc_sw_result.csv')
            batch = last_time(folder/target)
            now = time.monotonic()
            if latest != previous:
                previous, stable_since = latest, now
            gap = None if latest is None or batch is None else latest-batch
            if gap is not None and abs(gap) <= 4.0 and now-stable_since >= 10:
                status = 'complete'
                break
            if now-started > args.timeout:
                status = 'timeout'
                break
            time.sleep(2)
        result = {'status':status, 'wait_seconds':now-started,
                  'sliding_window_end_utc':latest, 'backend_end_utc':batch,
                  'tail_gap_seconds':gap,
                  'policy':'Wait for a stable front-end tail and backend coverage within 4 s; no data or estimator changes.'}
        (folder/'backend_drain.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result,indent=2),flush=True)
        if status != 'complete':
            raise RuntimeError('Backend did not catch up before the declared timeout')
    finally:
        if held:
            try:
                if identity(wrapper[0]) == wrapper[1]:
                    os.kill(wrapper[0], signal.SIGCONT)
            except OSError:
                pass


if __name__=='__main__':
    main()
