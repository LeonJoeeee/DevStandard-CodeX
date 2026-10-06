#!/usr/bin/env python3
"""Deliver one complete role page inline (Windows entry).

This is the platform-neutral entry used by the Windows `commandWindows` hooks.json
entry; the shipped `hooks/session-start` bash script keeps the Unix entry. Both must
emit the same JSON for the same arguments: one synchronous handler, `additionalContextLimit=0`,
and the fixed 64,000 UTF-8 byte safety budget covering the whole additionalContext.
"""
import json
import sys
from pathlib import Path

CAP_BYTES = 64000
MARKER = '--- codex-method whole context ---\n'


def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except (AttributeError, ValueError):
        pass
    root = Path(sys.argv[1])
    args = sys.argv[2:]
    if len(args) > 1:
        return stop('one role argument is supported; numbered part delivery was removed')
    role = args[0] if args else 'orchestrator'
    page = root / 'reference' / (role + '.md')
    header = (f'codex-method operating context: reference/{role}.md\n'
              f'Resolve references from: {root}\n'
              'Follow this whole page before acting or replying; load referenced pages only at their triggers.\n'
              + MARKER)
    try:
        data = page.read_bytes()
    except FileNotFoundError:
        return stop('required role page is missing at ' + str(page))
    except OSError as error:
        return stop('required role page cannot be read: ' + str(error))
    if len(header.encode('utf-8')) + len(data) > CAP_BYTES:
        return stop('complete additionalContext exceeds the fixed 64000 UTF-8 byte budget; refusing partial context')
    try:
        text = data.decode('utf-8')
    except UnicodeDecodeError:
        return stop('required role page is not valid UTF-8: ' + str(page))
    if not text.strip():
        return stop('required role page is empty at ' + str(page))
    print(json.dumps({'hookSpecificOutput': {
        'hookEventName': 'SessionStart', 'additionalContext': header + text}}, ensure_ascii=False))


def stop(reason):
    print(json.dumps({'continue': False, 'stopReason': 'codex-method: ' + reason}))
    raise SystemExit(0)


if __name__ == '__main__':
    main()
