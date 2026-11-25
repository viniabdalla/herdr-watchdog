"""Spec religar-pela-skill L32-37,40: Tasks PTY with isolated proof and Herdr.

Only the concurrently developed relink core is replaced. Tasks, its transport,
queue worker, binding persistence and group storage are real production code.
"""
from dataclasses import asdict, replace
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import test_leader_link as legacy
from test_artifacts_yazi import Terminal
from watchdog_app import long_run, pane_delivery
from watchdog_app.store import atomic

SCRIPT = r'''
import sys,json,uuid
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,sys.argv[3])
from test_leader_link import Binding
from watchdog_app import bindings,curate
from watchdog_app.store import Store,atomic
repo=Path(sys.argv[1]);origin=Path(sys.argv[2]);opfile=repo/'op.json'
def candidates():return [Binding(**b) for b in json.loads((repo/'live.json').read_text())],[]
def verify(b,**kw):
 if b not in candidates()[0]:raise RuntimeError('identity changed')
 return {'agent_status':'idle'}
def processes():return [dict(pid=b.pid,started=b.started,kind=b.kind,account=b.account,pane=b.pane) for b in candidates()[0]]
runtime=SimpleNamespace(Binding=Binding,verify=verify,processes=processes,
 process_info=lambda pid:next(p for p in processes() if p['pid']==pid))
bindings.engine=lambda:runtime
bindings.discover=lambda repo:candidates()
bindings.project_for=lambda b:repo
curate.latest_reply=lambda b:None
from watchdog_app import relink_delivery
# Inspect foreground and native identity via the actual fake binary. Its process
# table is represented by the controlled runtime above.
def begin(session,candidate):
 ref=uuid.uuid4().hex
 atomic(opfile,dict(ref=ref,state='pending',pane=candidate.pane,notice='aguardando prova B',
    binding_file=str(session.file),candidate=__import__('dataclasses').asdict(candidate)))
 return ref
def read(ref):
 op=json.loads(opfile.read_text())
 delivery=relink_delivery.record_path(ref)
 if op['state']=='pending' and delivery.exists() and json.loads(delivery.read_text())['state']=='sent' and (repo/'approve').exists():
  old=Binding(**json.loads(origin.read_text())['binding'])
  new=Binding(**json.loads((repo/'effective.json').read_text()))
  actors=[__import__('dataclasses').asdict(new) if b.pane==new.pane else __import__('dataclasses').asdict(b) for b in candidates()[0]]
  atomic(repo/'live.json',actors)
  from watchdog_app.herdr import Herdr
  target=Store(origin.parent).transfer(origin,old,new,repo,ref,api=Herdr())
  op.update(state='confirmed',successor=str(target),notice='B comprovada');atomic(opfile,op)
 return op
def cancel(ref):
 op=json.loads(opfile.read_text());op.update(state='cancelled',notice='cancelada');atomic(opfile,op)
def pending_for(file):
 return json.loads(opfile.read_text())['ref'] if opfile.exists() else None
sys.modules['watchdog_app.relink']=SimpleNamespace(begin=begin,read=read,cancel=cancel,pending_for=pending_for,guard=lambda file:None)
from watchdog_app.tasks_ui import run
run(repo,origin)
'''


class TasksRelinkPtyTests(unittest.TestCase):
    live = legacy.LeaderLinkTests.live
    wait = legacy.LeaderLinkTests.wait
    def open(self, actor=None):
        t=Terminal([sys.executable,'-B','-c',SCRIPT,str(self.repo),str(self.file),str(Path(__file__).parent)],self.env)
        self.addCleanup(t.close);self.wait(t,'WATCHDOG / TASKS');return t
    def setUp(self):
        legacy.LeaderLinkTests.setUp(self)
        self.old=replace(self.old,account=str(self.repo/'account'),session='AAAAAAAA-old',pid=111)
        self.store.save(self.old,self.store.load(self.old,self.repo));self.file=self.store.root/(self.old.key+'.json')
        self.chosen=replace(self.old,pane='project:p9',terminal='chosen-terminal',session='stale-A',pid=222)
        self.new=replace(self.chosen,session='BBBBBBBB-current')
        self.live(self.old,self.chosen)
        atomic(self.repo/'effective.json',asdict(self.new))
        skill=Path(self.chosen.account)/'skills/religar/SKILL.md';skill.parent.mkdir(parents=True);skill.write_text('fixture')
        self.env['FIXTURE_ROOT']=str(self.repo)
        subprocess.run(['git','init','-q',str(self.repo)],check=True)
        (self.repo/'source with spaces').mkdir()
        # Extend fake native CLI with list, foreground processes and project cwd.
        fake=self.repo/'herdr';text=fake.read_text()
        text=text.replace("else:result=dict(agent=agent(),pane=agent())", """elif args[:2]==['agent','list']:
 result=dict(agents=[dict(pane_id=b['pane'],terminal_id=b['terminal'],workspace_id=b['workspace'],agent=b['kind'],agent_status='idle',agent_session=dict(kind='id',value=b['session'])) for b in actors])
elif args[:2]==['pane','process-info']:
 b=next(b for b in actors if b['pane']==args[-1]);result=dict(process_info=dict(foreground_processes=[dict(pid=b['pid'])]))
else:result=dict(agent=agent(),pane=dict(agent(),cwd=str(root/'source with spaces')))""")
        fake.write_text(text)
    def calls(self):
        path=self.repo/'commands.jsonl'
        return [json.loads(l) for l in path.read_text().splitlines()] if path.exists() else []
    def test_waiting_queue_worker_stays_with_A_while_one_enter_recovers_B_and_reopens(self):
        # L32,33,37: different pane; 14/15 group and historical A requests survive.
        group={'members':['title:T'+str(n) for n in range(15)],'base':'base-sha',
               'modes':{'title:T0':'here'},'goal':{'kind':'codex','account':self.old.account,'session':self.old.session},
               'integration_branch':'integration'}
        (self.repo/'TODO.md').write_text('## Done\n'+''.join('- [x] T'+str(n)+'\n' for n in range(14))+'## Next\n- [ ] T14\n')
        with patch.dict(os.environ,self.env):
            atomic(long_run.path_for(self.repo),group)
            group_path=long_run.path_for(self.repo)
            pending=pane_delivery.pending_path(self.chosen.pane)
            old=dict(version=1,delivery_id='old',pane=self.chosen.pane,session=None,
                 identity=[self.chosen.pane,self.chosen.terminal,'codex',self.chosen.session],
                 text='pedido antigo de A',phase='waiting',enter='Enter',last_progress_at=time.time())
            atomic(pending,old)
        before=group_path.read_bytes()
        def progress_count():
            from watchdog_app.progress_ui import rows
            from watchdog_app.session_progress import View
            with patch.dict(os.environ,self.env):
                values=rows(self.repo,store=SimpleNamespace(list=lambda repo:[]),
                    progress=SimpleNamespace(poll=lambda:View('unavailable')),
                    agents=SimpleNamespace(poll=lambda:[]))
            return next(text for text,_,_ in values if text.startswith('14 de 15'))
        count_before=progress_count()
        atomic(self.repo/'composer.json','rascunho humano')
        worker=subprocess.Popen([sys.executable,'-m','watchdog_app.pane_delivery','watch',str(pending)],env=self.env,
                                stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        self.addCleanup(lambda: worker.poll() is None and worker.terminate())
        t=self.open();os.write(t.master,b'L');self.wait(t,'project:p9');os.write(t.master,b'j\r')
        self.wait(t,'Aguardando rascunho livre')
        self.assertEqual(json.loads((self.repo/'composer.json').read_text()),'rascunho humano')
        self.assertFalse(any(c[:2]==['pane','send-text'] for c in self.calls()))
        atomic(self.repo/'composer.json','');self.wait(t,'prova B')
        # Native continues announcing A until the fake core is explicitly allowed to prove B.
        self.assertEqual(json.loads((self.repo/'live.json').read_text())[1]['session'],'stale-A')
        self.assertNotIn('Líder ligado'.encode(),t.output)
        t.close()
        t=self.open();self.wait(t,'prova B')
        (self.repo/'approve').touch();self.wait(t,'Líder ligado');self.wait(t,'BBBBBBBB')
        self.assertEqual(group_path.read_bytes(),before)
        self.assertEqual(progress_count(),count_before)
        sends=[c for c in self.calls() if c[:2]==['pane','send-text']]
        ref=json.loads((self.repo/'op.json').read_text())['ref']
        self.assertEqual(sends,[['pane','send-text',self.chosen.pane,'$religar '+ref]])
        held=self.store.root/'relink-deliveries'/(ref+'.held')
        self.assertEqual([json.loads(p.read_text()) for p in held.glob('*.json')],[old])
        worker.wait(timeout=4)
        t.close();t=self.open();self.wait(t,'BBBBBBBB')
        self.assertEqual(len([c for c in self.calls() if c[:2]==['pane','send-text']]),1)
