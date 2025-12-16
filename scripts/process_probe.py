#!/usr/bin/env python3
"""Process probe for Windows: launch target (python main.py) and record short-lived processes.
Run from repository root: python scripts/process_probe.py
"""
import time
import psutil
import subprocess
import os
import sys
from collections import defaultdict

TARGET = [sys.executable, 'main.py']
TIMEOUT = 20.0
POLL_INTERVAL = 0.05  # 50ms

def snapshot_procs():
    procs = {}
    for p in psutil.process_iter(['pid','ppid','name','create_time','cmdline']):
        info = p.info
        procs[info['pid']] = info
    return procs


def main():
    root = os.path.abspath(os.getcwd())
    print('Working dir:', root)
    print('Launching target:', ' '.join(TARGET))

    before = snapshot_procs()

    # start target process
    proc = subprocess.Popen(TARGET, cwd=root)
    target_pid = proc.pid
    print('Target pid:', target_pid)

    seen = {}  # pid -> {'create':ts, 'terminate':ts or None, 'info':info}

    start = time.time()
    end_time = start + TIMEOUT

    # initialize seen with before snapshot
    for pid,info in before.items():
        seen[pid] = {'create': info.get('create_time', None), 'terminate': None, 'info': info}

    while time.time() < end_time:
        now = time.time()
        for p in psutil.process_iter(['pid','ppid','name','create_time','cmdline', 'status']):
            info = p.info
            pid = info['pid']
            if pid not in seen:
                seen[pid] = {'create': info.get('create_time', now), 'terminate': None, 'info': info}
        # mark terminated
        # build current set
        current = set(p.pid for p in psutil.process_iter())
        for pid in list(seen.keys()):
            if pid not in current and seen[pid]['terminate'] is None:
                seen[pid]['terminate'] = time.time()
        # break if target finished and a short grace period passed
        if proc.poll() is not None:
            # give a small grace window to capture very short-lived children
            time.sleep(0.5)
            break
        time.sleep(POLL_INTERVAL)

    # ensure we waited for target to exit or kill if still running
    if proc.poll() is None:
        try:
            proc.terminate()
            proc.wait(timeout=2)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

    # finalize terminate times
    current = set(p.pid for p in psutil.process_iter())
    for pid in list(seen.keys()):
        if seen[pid]['terminate'] is None and pid not in current:
            seen[pid]['terminate'] = time.time()

    # analyze
    created_during = []
    for pid,rec in seen.items():
        c = rec['create']
        t = rec['terminate']
        info = rec['info']
        if c is None:
            continue
        # if created after start
        if c >= start - 0.001 and c <= time.time():
            lifetime = (t - c) if (t is not None) else (time.time() - c)
            created_during.append((pid, info.get('ppid'), info.get('name'), info.get('cmdline'), c, t, lifetime))

    # sort by create time
    created_during.sort(key=lambda x: x[4])

    print('\nProcesses created during monitoring window:')
    for pid, ppid, name, cmdline, c, t, lifetime in created_during:
        c_s = time.strftime('%H:%M:%S', time.localtime(c)) + f'.{int((c%1)*1000):03d}'
        t_s = '-' if t is None else time.strftime('%H:%M:%S', time.localtime(t)) + f'.{int((t%1)*1000):03d}'
        print(f'PID={pid} PPID={ppid} NAME={name} LIFETIME={lifetime:.3f}s CREATED={c_s} TERMINATED={t_s}')
        if cmdline:
            print('  CMD:', ' '.join(cmdline))

    # focus on short-lived (<1s) processes
    short = [p for p in created_during if (p[6] is not None and p[6] < 1.0)]
    if short:
        print('\nShort-lived processes (<1.0s):')
        for pid, ppid, name, cmdline, c, t, lifetime in short:
            print(f' PID={pid} NAME={name} LIFETIME={lifetime:.3f}s PPID={ppid}')
    else:
        print('\nNo short-lived processes detected during monitoring window.')

if __name__ == '__main__':
    main()
