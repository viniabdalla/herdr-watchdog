"""Spec #1 L72-82, L115, L136, L145, L172-176: kit at external boundaries."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]


class KitBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root/'another-project'
        self.repo.mkdir()
        self.env = dict(os.environ, XDG_STATE_HOME=str(self.root/'state'),
                        KIT_FAKE_ROOT=str(self.root))
        self.git('init', '-b', 'integration')
        self.git('config', 'user.email', 'test@example.invalid')
        self.git('config', 'user.name', 'Test')
        (self.repo/'AGENTS.md').write_text('## Dispatch\nBranch de integração: `integration`\n'
            'Modelo dos executores: `gpt-6.1-sol`\nEsforço dos executores: médio\n'
            'Permissões dos executores: full access\nTestes obrigatórios: `python3 -m unittest`\n')
        (self.repo/'GLOSSARY.md').write_text('# Glossary\n')
        (self.repo/'docs/issues').mkdir(parents=True)
        (self.repo/'docs/issues/9-ticket.md').write_text('---\nnumber: 9\nstate: open\nparent: 1\n---\n\nAcceptance\n')
        self.git('add', '.')
        self.git('commit', '-m', 'base')
        self.base = self.git('rev-parse', 'HEAD')
        self.git('checkout', '-b', 'leader')
        (self.repo/'leader-only').write_text('not part of integration')
        self.git('add', '.')
        self.git('commit', '-m', 'leader change')
        fake = self.root/'herdr'
        fake.write_text('''#!/usr/bin/env python3
import json, os, pathlib, sys
root=pathlib.Path(os.environ['KIT_FAKE_ROOT']); args=sys.argv[1:]
with (root/'herdr.jsonl').open('a') as f:f.write(json.dumps(args)+'\\n')
if args[:1]==['--session']:args=args[2:]
path=root/'panes.json'
panes=json.loads(path.read_text()) if path.exists() else []
def pane(n,tab):return dict(pane_id='w9:p'+str(n),terminal_id='term'+str(n),tab_id=tab,workspace_id='w9',agent='codex',agent_session={'kind':'id','value':'thread'+str(n)})
if args[:2]==['tab','create']:
 p=pane(len(panes)+1,'w9:t'+str(len(panes)+1));panes.append(p);result={'root_pane':p,'tab':{'tab_id':p['tab_id']}}
elif args[:2]==['pane','split']:
 anchor=next(p for p in panes if p['pane_id']==args[2]);p=pane(len(panes)+1,anchor['tab_id']);panes.append(p);result={'pane':p}
elif args[:2]==['pane','list']:result={'panes':panes}
elif args[:2]==['pane','get']:
 p=dict(next(p for p in panes if p['pane_id']==args[2]))
 if os.environ.get('KIT_SESSION_ON_PROMPT') and not (root/'prompted').exists():p['agent_session']=None
 result={'pane':p}
elif args[:2]==['agent','prompt']:
 if os.environ.get('KIT_FAIL_PROMPT'):sys.exit('agent_prompt_stalled')
 (root/'prompted').touch()
 result={'status':'working'}
elif args[:2] in (['agent','start'],['pane','send-text'],['pane','send-keys']):
 if os.environ.get('KIT_FAIL_START') and args[:2]==['agent','start']:sys.exit('startup uncertain')
 result={}
else:sys.exit('Unexpected command: '+repr(args))
path.write_text(json.dumps(panes));print(json.dumps({'result':result}))
''')
        fake.chmod(0o755)
        self.env['HERDR_BIN_PATH'] = str(fake)
        gh = self.root/'gh'
        gh.write_text('''#!/usr/bin/env python3
import json, os, pathlib, sys
root=pathlib.Path(os.environ['KIT_FAKE_ROOT']);args=sys.argv[1:]
with (root/'gh.jsonl').open('a') as f:f.write(json.dumps(args)+'\\n')
p=root/'issue.json'
v=json.loads(p.read_text()) if p.exists() else dict(number=9,title='Ticket',state='OPEN',body='Acceptance',labels=[],url='https://example.invalid/9',comments=[])
if args[:2]==['issue','comment']:
 v['comments'].append(dict(body=pathlib.Path(args[args.index('--body-file')+1]).read_text(),author={'login':'test'},createdAt='2026-11-25T12:00:00Z'))
elif args[:2]==['issue','close']:
 if os.environ.get('KIT_FAIL_CLOSE'):sys.exit('close failed')
 v['state']='CLOSED'
elif args[:2]!=['issue','view']:sys.exit('Unexpected gh command')
p.write_text(json.dumps(v));print(json.dumps(v))
''')
        gh.chmod(0o755)
        self.env['PATH'] = str(self.root)+os.pathsep+self.env['PATH']

    def git(self, *args):
        return subprocess.check_output(['git','-C',str(self.repo),*args], stderr=subprocess.DEVNULL, text=True).strip()

    def cli(self, *args, ok=True):
        result = subprocess.run([str(ROOT/'watchdog'),'kit',*args,'--repo',str(self.repo)],
                                env=self.env, capture_output=True,text=True)
        if ok:self.assertEqual(result.returncode,0,result.stderr)
        else:self.assertNotEqual(result.returncode,0)
        return result

    def open(self, ticket='A', *extra, ok=True):
        return self.cli('abrir','--ticket',ticket,'--grupo','group-1','--lider','w9:p0',
                        '--workspace','w9','--leva','Theme A B','--aceite','docs/issues/9-ticket.md',
                        '--spec','docs/spec.md',*extra,ok=ok)

    def records(self):
        return json.loads(self.cli('listar','--grupo','group-1').stdout)['executors']

    def test_open_isolated_worktree_contract_and_confirmed_identity(self):
        # L72-80, L136, L173: wrong base, missing identity/contract or wrong model must fail.
        before=time.time()
        result=json.loads(self.open().stdout)
        self.assertGreaterEqual(result['created_at'],before)
        tree=Path(result['worktree'])
        self.assertEqual(self.git('-C',str(tree),'rev-parse','HEAD'),self.base)
        self.assertFalse((tree/'leader-only').exists())
        self.assertEqual(result['project'],str(self.repo))
        self.assertEqual(result['group'],'group-1')
        self.assertEqual(result['pane'],'w9:p1')
        self.assertEqual(result['terminal'],'term1')
        self.assertEqual(result['session'],'thread1')
        self.assertEqual(self.records()[0]['ticket'],'A')
        calls=[json.loads(s) for s in (self.root/'herdr.jsonl').read_text().splitlines()]
        start=next(c for c in calls if c[:2]==['agent','start'])
        self.assertIn('--no-daemon',start[start.index('--')+1:])
        prompt=next(c for c in calls if c[:2]==['agent','prompt'])
        self.assertIn('--wait',prompt)
        self.assertEqual(prompt[prompt.index('--until')+1],'working')
        self.assertEqual(prompt[2],result['pane'])
        self.assertEqual(prompt[3],Path(result['contract']).read_text())
        self.assertIn('gpt-6.1-sol',start)
        self.assertIn('model_reasoning_effort="medium"',start)
        contract=Path(result['contract']).read_text()
        for text in ('w9:p1','w9:p0','docs/issues/9-ticket.md','docs/spec.md','GLOSSARY.md',
                     'git merge integration','watchdog aviso','aprovação','python3 -m unittest'):
            self.assertIn(text,contract)
        self.assertEqual(self.git('check-ignore',str(tree)),str(tree))
        self.assertEqual(self.git('check-ignore',result['contract']),result['contract'])

    def test_later_dependency_uses_same_tab_until_capacity(self):
        # L74, L173: ignoring dependency leva or capacity opens the wrong tab.
        a=json.loads(self.open('A','--capacidade','2').stdout)
        b=json.loads(self.open('B','--depende','A','--capacidade','2').stdout)
        c=json.loads(self.open('C','--depende','A','--capacidade','2').stdout)
        self.assertEqual(a['tab'],b['tab'])
        self.assertNotEqual(a['tab'],c['tab'])
        self.assertEqual(len(self.records()),3)

    def test_uncertain_start_keeps_record_and_does_not_duplicate(self):
        # L72 and L151: an uncertain startup must never silently open a second executor.
        self.env['KIT_FAIL_START']='1'
        self.open(ok=False)
        before=(self.root/'herdr.jsonl').read_text()
        self.open(ok=False)
        self.assertEqual((self.root/'herdr.jsonl').read_text(),before)
        self.assertEqual(self.records()[0]['state'],'failed')
        self.assertTrue(Path(self.records()[0]['worktree']).exists())

    def test_close_preserves_local_metadata_and_records_remote_comment(self):
        # L82, L176: a successful close must update state AND evidence in the copy.
        self.cli('fechar','--issue','9','--copia','docs/issues/9-ticket.md',
                 '--comentario','T8 concluído: commit abc, testes OK')
        copy=(self.repo/'docs/issues/9-ticket.md').read_text()
        self.assertIn('state: closed',copy)
        self.assertIn('parent: 1',copy)
        self.assertIn('T8 concluído: commit abc, testes OK',copy)
        calls=[json.loads(s) for s in (self.root/'gh.jsonl').read_text().splitlines()]
        self.assertEqual([c[1] for c in calls],['view','comment','close','view'])
        self.assertTrue(list((self.repo/'.watchdog/run').glob('*/*comentario*.md')))

    def test_failed_close_does_not_claim_closed_in_copy(self):
        # L176: failing remote close cannot mark local evidence closed.
        self.env['KIT_FAIL_CLOSE']='1'
        result = self.cli('fechar','--issue','9','--copia','docs/issues/9-ticket.md','--comentario','Evidence',ok=False)
        self.assertIn('close failed', result.stderr)
        self.assertIn('state: open',(self.repo/'docs/issues/9-ticket.md').read_text())

    def test_configuration_missing_fails_before_creating_resources(self):
        # L136: model/effort must come from Dispatch, never an invented default.
        (self.repo/'AGENTS.md').write_text('## Dispatch\nBranch de integração: `integration`\n')
        result = self.open(ok=False)
        self.assertIn('Modelo dos executores',result.stderr)
        self.assertFalse((self.root/'herdr.jsonl').exists())
        self.assertFalse((self.repo/'.worktrees/A').exists())

    def test_malformed_copy_is_rejected_before_remote_changes(self):
        # L176: invalid local copy must not close a real issue before failing.
        (self.repo/'docs/issues/9-ticket.md').write_text('number: 9\nNo YAML header\n')
        self.cli('fechar','--issue','9','--copia','docs/issues/9-ticket.md','--comentario','Evidence',ok=False)
        self.assertFalse((self.root/'gh.jsonl').exists())

    def test_concurrent_opens_keep_both_records(self):
        # L72-74, L151: separate CLI processes must not lose executor records.
        common = [str(ROOT/'watchdog'),'kit','abrir','--repo',str(self.repo),
                  '--grupo','group-1','--lider','w9:p0','--workspace','w9','--leva','Theme',
                  '--aceite','docs/issues/9-ticket.md','--spec','docs/spec.md']
        processes = [subprocess.Popen(common+['--ticket',ticket],env=self.env,
                                     stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
                     for ticket in ('A','B')]
        for process in processes:
            out, err = process.communicate(timeout=20)
            self.assertEqual(process.returncode,0,err)
        self.assertEqual({r['ticket'] for r in self.records()},{'A','B'})

    def test_draft_contract_is_not_reported_as_ready(self):
        # L77-80, L151: accepted text without a working turn is not delivery.
        self.env['KIT_FAIL_PROMPT']='1'
        result = self.open(ok=False)
        self.assertIn('agent_prompt_stalled',result.stderr)
        self.assertEqual(self.records()[0]['state'],'failed')
        self.assertEqual(self.records()[0]['operation'],'contract')

    def test_retry_partial_close_does_not_repeat_existing_comment(self):
        # L176 + user correction: retrying a partial close keeps one evidence comment.
        self.env['KIT_FAIL_CLOSE']='1'
        args=('fechar','--issue','9','--copia','docs/issues/9-ticket.md','--comentario','Evidence')
        self.cli(*args,ok=False)
        self.env.pop('KIT_FAIL_CLOSE')
        self.cli(*args)
        remote=json.loads((self.root/'issue.json').read_text())
        self.assertEqual(remote['state'],'CLOSED')
        self.assertEqual([c['body'] for c in remote['comments']],['Evidence'])
        calls=[json.loads(s) for s in (self.root/'gh.jsonl').read_text().splitlines()]
        self.assertEqual(sum(c[:2]==['issue','comment'] for c in calls),1)
        self.assertIn('Evidence',(self.repo/'docs/issues/9-ticket.md').read_text())

    def test_session_available_after_prompt_is_registered(self):
        # L92-93 + user correction: use confirmed session from the working pane.
        self.env['KIT_SESSION_ON_PROMPT']='1'
        result=json.loads(self.open().stdout)
        self.assertEqual(result['session'],'thread1')


if __name__ == '__main__':unittest.main()
