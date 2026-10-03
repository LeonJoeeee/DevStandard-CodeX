#!/usr/bin/env python3
"""Every ADR amendment block must be announced by its status line, in the matching form.

`reference/adr.md` states the rule; this checks it. Run from the repo root.

    (date, see NNNN)  ->  `Amended by NNNN`, dated or not
    any other citation, or none  ->  `Amended (date)`

"Any other citation" is deliberate: a block may cite a commit, an issue, a PR, or an ADR
that *caused* the change without deciding anything about this one (`caused by NNNN`). None
of those is an amending ADR, so all pair with the citation-free status form.

Two things this does NOT do, both on purpose:

  * It does not police header *style*. A block written before the sanctioned form existed
    (`**Amendment DATE (issue #NN):**`) is parsed for its date and held to the same
    announcement rule — because the alternative is editing an already-merged block, which
    `reference/adr.md` forbids. Recognise the old shape; never rewrite it.
  * It does not resolve the `Status:` line — it resolves the `Status:` *block*, to the next
    blank line. Four ADRs wrap it across three or four physical lines, and assuming one
    line has already caused a real defect here (an amendment spliced mid-sentence).

A header must begin its line (optionally blockquoted). Header scanning skips backtick and
tilde fenced regions, so a template quoted inside prose or fenced code is not mistaken for
a real amendment — this repo writes ADRs *about* ADR conventions.
"""
import glob
import re
import sys

# Sanctioned: **Amendment (2026-08-13, see 0031):**  /  **Amendment (2026-08-13):**
# Legacy:     **Amendment 2026-07-24 (issue #56):**   (date outside the parentheses)
HEADER = re.compile(
    r'^>?\s*\*\*Amendment '
    r'(?:\((?P<date>\d{4}-\d{2}-\d{2})(?:,\s*(?P<cite>[^)]*))?\)'
    r'|(?P<legacy_date>\d{4}-\d{2}-\d{2})\s*\([^)]*\))',
    re.M,
)
SEE_ADR = re.compile(r'^see\s+(\d{4})\b')
FENCE = re.compile(r'^(?:> ?)? {0,3}(?P<run>`{3,}|~{3,})(?P<tail>.*)$')


def status_block(lines, path, problems):
    """The whole Status: block — never just its first physical line."""
    heads = [k for k, l in enumerate(lines) if l.startswith('Status:')]
    if not heads:
        problems.append(f'{path}: no `Status:` line')
        return None
    i = heads[0]
    j = i + 1
    while j < len(lines) and lines[j].strip():
        j += 1
    return ' '.join(x.strip() for x in lines[i:j]), j


def parse_status(status):
    """-> (pairs of (adr, date), ADR numbers announced without a date, citation-free dates)"""
    pairs, dateless, dates = set(), set(), set()
    for m in re.finditer(r'Amended by (\d{4})(?:\s*\((\d{4}-\d{2}-\d{2})\)((?:,\s*\d{4}\s*\(\d{4}-\d{2}-\d{2}\))*))?', status):
        if m.group(2):
            pairs.add((m.group(1), m.group(2)))
            for c in re.finditer(r'(\d{4})\s*\((\d{4}-\d{2}-\d{2})\)', m.group(3) or ''):
                pairs.add((c.group(1), c.group(2)))
        else:
            dateless.add(m.group(1))
    dates.update(re.findall(r'Amended \((\d{4}-\d{2}-\d{2})\)', status))
    return pairs, dateless, dates


def unfenced(lines):
    """Body text outside CLOSED backtick and tilde fenced regions.

    A fence left open at EOF was never a fence: its lines go back into the body. Otherwise a
    stray opener would hide every amendment below it — trading this gate's false positive for a
    false negative, which is the worse direction.
    """
    body, held = [], []
    opened = None
    for line in lines:
        fence = FENCE.match(line)
        if opened:
            held.append(line)
            if (fence and fence.group('run')[0] == opened[0]
                    and len(fence.group('run')) >= len(opened)
                    and not fence.group('tail').strip()):
                opened, held = None, []
            continue
        if fence:
            run = fence.group('run')
            if run[0] == '~' or '`' not in fence.group('tail'):
                opened, held = run, [line]
                continue
        body.append(line)
    body.extend(held)          # unterminated: never a fence, so never hidden
    return '\n'.join(body)


def main():
    problems = []
    files = sorted(glob.glob('docs/adr/*.md'))
    for path in files:
        lines = open(path).read().split('\n')
        resolved = status_block(lines, path, problems)
        if not resolved:
            continue
        status, body_start = resolved
        pairs, dateless, dates = parse_status(status)
        name = path.split('/')[-1]

        for m in HEADER.finditer(unfenced(lines[body_start:])):
            date = m.group('date') or m.group('legacy_date')
            cite = (m.group('cite') or '').strip()
            adr = SEE_ADR.match(cite)
            if adr:
                n = adr.group(1)
                if (n, date) not in pairs and n not in dateless:
                    problems.append(
                        f'{name}: block ({date}, see {n}) — status line has no '
                        f'`Amended by {n}` for it')
            elif date not in dates:
                problems.append(
                    f'{name}: block ({date}'
                    + (f', {cite}' if cite else '')
                    + f') cites no amending ADR — status line has no `Amended ({date})`')

    for p in problems:
        print(p)
    if problems:
        print(f'\n{len(problems)} amendment block(s) the status line does not announce.')
        return 1
    print(f'{len(files)} ADRs: every amendment block announced by its status line')
    return 0


if __name__ == '__main__':
    sys.exit(main())
