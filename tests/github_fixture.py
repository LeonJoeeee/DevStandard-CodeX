"""A stateful GitHub boundary double; git and command consumers remain real."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MODEL = 'gpt-6.1-sol'
IDENTITY = 'Codex, gpt-6.1-sol at high, read-only'

FAKE_GH = r'''#!/usr/bin/env python3
import json, os, signal, sys
from pathlib import Path
p = Path(os.environ['GH_FIXTURE'])
s = json.loads(p.read_text())
a = sys.argv[1:]
s.setdefault('calls', []).append(a)
def save(): p.write_text(json.dumps(s))
def out(value):
    save()
    print(json.dumps(value))
    sys.exit(0)
def field(name):
    for flag in ('-f', '-F', '--field', '--raw-field'):
        for i, item in enumerate(a[:-1]):
            if item == flag and a[i+1].startswith(name+'='):
                return a[i+1].split('=', 1)[1]
    if '--input' in a:
        return json.load(sys.stdin).get(name)
    return None
def mutation_before(method):
    ledger = Path(os.environ['REVIEW_LEDGER'])
    s.setdefault('boundary_ledgers', []).append(json.loads(ledger.read_text()) if ledger.exists() else None)
    fault = s.get('mutation_fault')
    if fault and fault['method'] == method:
        s.pop('mutation_fault')
        if fault['outcome'] == 'unknown':
            save()
            print('request outcome unknown', file=sys.stderr)
            sys.exit(1)
        return fault['outcome']
def mutation_after(comment, outcome):
    if outcome:
        save()
        if outcome == 'empty-response':
            sys.exit(0)
        if outcome == 'crash':
            os.kill(os.getppid(), signal.SIGKILL)
        else:
            print('remote success; response lost', file=sys.stderr)
        sys.exit(1)
    out(comment)
if a[:2] == ['repo', 'view']: out({'nameWithOwner': 'owner/project'})
if a[:2] == ['issue', 'view']: out({'body': s['issue'], 'state': 'OPEN', 'title': 'Fix acceptance'})
if a[:2] == ['pr', 'view']:
    r=s['pr'];out({'title':'Fix acceptance', 'body':s['description'], 'headRefOid':r['head']['sha'],
                  'baseRefOid':r['base']['sha'], 'baseRefName':r['base']['ref'], 'state':'OPEN'})
if a[:2] == ['pr', 'checks']: out([{'name':'test', 'bucket':'pass'}])
if a[:2] == ['pr', 'diff']: print('code.txt'); save();sys.exit(0)
if a[:2] == ['pr', 'merge']:
    s['merged']=a;out({'merged': True})
if a and a[0] == 'api':
    endpoint=next((x for x in a[1:] if x == 'user' or x.startswith('repos/')), '')
    method=a[a.index('-X')+1] if '-X' in a else 'GET'
    if endpoint == 'user': out({'login':'owner'})
    if endpoint == 'repos/owner/project': out({'default_branch':'main'})
    if endpoint == 'repos/owner/project/pulls/1':
        s['pr_reads']=s.get('pr_reads', 0)+1
        if s.get('race') and s['pr_reads'] > s['race']:
            s['pr']['head']['sha']='c'*40
        out(s['pr'])
    if endpoint.startswith('repos/owner/project/git/ref/heads/'):
        out({'object':{'sha':s['pr']['base']['sha']}})
    if '/compare/' in endpoint: out({'behind_by':s.get('behind',0), 'status':'ahead'})
    if endpoint.endswith('/check-runs'):
        page={'total_count':len(s['checks']), 'check_runs':s['checks']}
        out([page] if '--slurp' in a else page)
    if endpoint == 'repos/owner/project/issues/2/comments':
        out([s.get('issue_comments', [])] if '--slurp' in a else s.get('issue_comments', []))
    if endpoint == 'repos/owner/project/issues/1/comments':
        if method == 'POST':
            outcome=mutation_before(method)
            c={'id':s['next_id'], 'user':{'login':'owner'}, 'body':field('body'),
               'html_url':'https://github.com/owner/project/pull/1#issuecomment-'+str(s['next_id'])}
            s['next_id']+=1;s['comments'].append(c);mutation_after(c, outcome)
        out([s['comments']] if '--slurp' in a else s['comments'])
    if '/issues/comments/' in endpoint:
        c=next(x for x in s['comments'] if x['id']==int(endpoint.rsplit('/',1)[1]))
        if method == 'PATCH':
            outcome=mutation_before(method)
            c['body']=field('body')
            mutation_after(c, outcome)
        out(c)
save()
print('Unexpected gh request: '+repr(a), file=sys.stderr)
sys.exit(2)
'''


class GitHubFixture:
    def __init__(self):
        self.temp = tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR'))
        self.root = Path(self.temp.name).resolve()
        self.project = self.root / 'project'
        self.project.mkdir()
        self.env = {**os.environ, 'GH_FIXTURE': str(self.root / 'github.json')}
        self.ledger = self.project / '.git/codex-method/reviews/owner/project/1.json'
        self.env['REVIEW_LEDGER'] = str(self.ledger)
        self.git('init', '-b', 'main')
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        (self.project / 'code.txt').write_text('base\n')
        self.git('add', '.')
        self.git('commit', '-m', 'base')
        self.base = self.git('rev-parse', 'HEAD').strip()
        self.git('checkout', '-b', 'task/2-acceptance')
        (self.project / 'code.txt').write_text('base\nhead\n')
        self.git('commit', '-am', 'head')
        self.head = self.git('rev-parse', 'HEAD').strip()
        self.pr = {'state':'open', 'head':{'sha':self.head, 'ref':'task/2-acceptance'},
                   'base':{'sha':self.base, 'ref':'main'}}
        self.save({'pr':self.pr, 'description':'architecture: YES\nA tested change.',
                   'issue':'## Goal\nFix acceptance.\n## Bounds\nReview lifecycle.\n## Done-check\nBehavioral tests.',
                   'comments':[], 'next_id':100,
                   'checks':[{'id':1, 'name':f'merged-result / {self.base} / {self.head}',
                              'status':'completed','conclusion':'success',
                              'app':{'id':15368, 'slug':'github-actions'}}]})
        bins = self.root / 'bin'
        bins.mkdir()
        (bins / 'gh').write_text(FAKE_GH)
        (bins / 'gh').chmod(0o755)
        self.env['PATH'] = str(bins) + os.pathsep + os.environ['PATH']
        self.output = self.root / 'packet'
        installed = self.command('install', '--host-version', '0.160.0')
        if installed.returncode:
            raise AssertionError(installed.stderr)

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.project), *args],
                                       text=True, stderr=subprocess.DEVNULL)

    def state(self):
        return json.loads(Path(self.env['GH_FIXTURE']).read_text())

    def save(self, state):
        Path(self.env['GH_FIXTURE']).write_text(json.dumps(state))

    def command(self, script, *args):
        return subprocess.run([sys.executable, str(ROOT / 'scripts' / script), *map(str, args),
                               '--project', str(self.project)], cwd=self.project,
                              env=self.env, text=True, capture_output=True)

    def start(self):
        return self.command('review-packet','start',1,'--issue',2,
                            '--architecture-level','yes','--output',self.output,
                            '--model',MODEL,'--effort','high','--host-version','0.160.0')

    def publish(self, verdict=None):
        started = self.start()
        if started.returncode:
            raise AssertionError(started.stderr)
        data=json.loads(started.stdout)
        attempt=data.get('comment_id', data.get('attempt'))
        path=self.root / 'verdict.md'
        path.write_text(verdict if verdict is not None else self.verdict())
        return self.command('review-packet','publish',1,'--issue',2,
                            '--attempt',attempt,'--verdict',path)

    def verdict(self, goal='Yes', floor1='Pass', floor2='Pass'):
        ready='Yes' if (goal, floor1, floor2)==('Yes','Pass','Pass') else 'No'
        return (f'Reviewer: {IDENTITY} — reviewed {self.head}\n\n'
                f'### Goal verdict\n{goal} — the pinned change was checked.\n\n'
                f'### Floor\n1. Evidence-backed completion claim: {floor1} — evidence checked.\n'
                f'2. Authorization and scope: {floor2} — authorized tree checked.\n'
                f'Ready to merge: {ready} — decided by Goal and Floors.\n\n'
                '### Notes\nNone.\n')

    def guard(self, *args):
        return self.command('guard','merge','--repo','owner/project','--pr',1,*args)

    def close(self):
        self.temp.cleanup()
