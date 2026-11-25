"""Issue #16 L24-37,64-68; spec #1 L58-60,137,172-175 (boundary B)."""
import json
import os
import subprocess
import sys
from unittest.mock import patch
from pane_submission_fixture import SubmissionFixture
from watchdog_app import pane_delivery as d
from watchdog_app.store import atomic


class StalledQueueTests(SubmissionFixture):
    def setup_queue(self, age=121):
        self.env_patch = patch.dict(os.environ, self.env)
        self.env_patch.start(); self.addCleanup(self.env_patch.stop)
        self.pending = d.pending_path('w11:p8')
        self.front = dict(version=1, delivery_id='front', pane='w11:p8', session=None,
                          identity=['w11:p8','term1','codex',self.state['session']],
                          text='Aviso antigo T6', phase='uncertain', uncertain_phase='pasting',
                          enter='Enter', last_progress_at=1000-age)
        atomic(self.pending, self.front)
        self.queued=[]
        for i,text in enumerate(['T13 pronto','$code-review','outro pedido','$code-review']):
            path=self.pending.with_name(self.pending.name.replace('.pending.json',f'.queued.0000000000000000000.{i}.json'))
            atomic(path,dict(self.front, delivery_id=str(i),text=text,phase='waiting'))
            self.queued.append(path)

    def tick(self, now=1000):
        with patch.object(d.time,'time',return_value=now):
            with d.pane_lock('w11:p8') as pending:
                return d.check_stalled(pending)

    def test_uncertain_front_archived_intact_and_single_notice_survives_restart(self):
        self.setup_queue()
        self.tick()
        archive=next(path for path in self.pending.parent.glob('*.stalled.*') if path.is_dir())
        self.assertEqual(json.loads((archive/'front.json').read_text()), self.front)
        notice=json.loads(self.pending.read_text())
        self.assertIn('Fila travada no seu pane w11:p8:',notice['text'])
        self.assertIn('Aviso antigo T6',notice['text'])
        self.assertIn('T13 pronto',notice['text'])
        self.assertIn('121 s',notice['text'])
        # Restart/concurrent observers cannot replace/escalate the saved notice.
        self.tick(1500)
        self.assertEqual(json.loads(self.pending.read_text()),notice)
        self.assertEqual(d.queue_notice('w11:p8'),'')
        p=self.start([sys.executable,'-m','watchdog_app.pane_delivery','resume',str(self.pending)])
        self.finish(p)
        self.assertEqual(self.actual()['submitted'],[notice['text']])
        # Tasks is a different process, reading the confirmed shared state.
        p=self.start([sys.executable,'-c',
                     'from watchdog_app.pane_delivery import queue_notice; print(queue_notice("w11:p8"))'])
        out,err=p.communicate(timeout=5)
        self.assertEqual(p.returncode,0,err)
        self.assertEqual(out.strip(),'Fila travada · perguntei ao líder')
        self.tick(1800)
        self.assertFalse(self.pending.exists())
        self.assertEqual(len(self.actual()['submitted']),1)
        # No copy is released before the explicit decision, even without pending.
        with self.assertRaises(d.DeliveryPending):
            d.send('w11:p8','mais um',timeout=.1,background=False)
        self.assertEqual(len(self.actual()['submitted']),1)
        d.resolve_queue('w11:p8', ['0','1','2','3'], 'Paste antigo encerrado; T6 integrado; pedidos atuais conferidos')
        self.assertEqual(d.queue_notice('w11:p8'),'')
        for path in sorted(self.pending.parent.glob('*.queued.*.json')):
            self.finish(self.start([sys.executable,'-m','watchdog_app.pane_delivery','resume',str(path)]))
        self.assertEqual(self.actual()['submitted'][1:],['T13 pronto','outro pedido','$code-review','mais um'])

    def test_progress_inside_deadline_preserves_front(self):
        self.setup_queue(age=119)
        self.tick()
        self.assertEqual(json.loads(self.pending.read_text()),self.front)
        self.front['last_progress_at']=999
        atomic(self.pending,self.front)
        self.tick(1119)
        self.assertEqual(json.loads(self.pending.read_text()),self.front)

    def test_lone_uncertain_delivery_and_human_draft_are_preserved(self):
        self.setup_queue()
        for path in self.queued:path.unlink()
        self.state['draft']='rascunho humano';self.save()
        self.tick()
        with self.assertRaises(d.DeliveryPending):
            d.advance(d.Herdr(),json.loads(self.pending.read_text()),self.pending,deadline=d.time.monotonic()+.15)
        self.assertEqual(self.actual()['draft'],'rascunho humano')
        self.assertEqual(self.actual()['submitted'],[])
        self.assertEqual(d.queue_notice('w11:p8'),'')
        self.tick(5000)
        self.assertEqual(len([path for path in self.pending.parent.glob('*.stalled.*') if path.is_dir()]),1)

    def test_legacy_snapshot_new_arrival_and_distinct_callbacks(self):
        # Issue #16 L58-62: legacy originals immutable; decision is snapshot scoped.
        self.setup_queue()
        self.front.pop('delivery_id');self.front.pop('last_progress_at')
        self.pending.write_text(json.dumps(self.front,separators=(',',':')))
        original_front=self.pending.read_bytes()
        for path in self.queued:
            job=json.loads(path.read_text());job.pop('delivery_id');job.pop('last_progress_at')
            atomic(path,job)
        originals={str(p):p.read_bytes() for p in self.queued}
        self.tick()  # establish observation without touching the legacy record
        self.assertEqual(self.pending.read_bytes(),original_front)
        self.tick(1121)
        archive=next(path for path in self.pending.parent.glob('*.stalled.*') if path.is_dir())
        self.assertEqual((archive/'front.json').read_bytes(),original_front)
        snapshot=d.queue_snapshot('w11:p8')
        self.assertEqual(snapshot,d.queue_snapshot('w11:p8'))
        self.finish(self.start([sys.executable,'-m','watchdog_app.pane_delivery','resume',str(self.pending)]))
        new=self.pending.with_name(self.pending.name.replace('.pending.json','.queued.z-new.json'))
        callback=dict(path=str(self.root/'callback.json'),expected=0,value=1)
        atomic(self.root/'callback.json',0)
        atomic(new,dict(self.front,text='$code-review',phase='waiting',on_confirm=callback))
        self.assertTrue(all(d.Path(path).read_bytes()==raw for path,raw in originals.items()))
        d.resolve_queue('w11:p8',[entry['id'] for entry in snapshot[1:]],'Fila antiga conferida e encerrada')
        for path in sorted(self.pending.parent.glob('*.queued.*.json')):
            self.finish(self.start([sys.executable,'-m','watchdog_app.pane_delivery','resume',str(path)]))
        self.assertEqual(self.actual()['submitted'][1:],['T13 pronto','outro pedido','$code-review','$code-review'])
        self.assertEqual(json.loads((self.root/'callback.json').read_text()),1)

    def test_notice_uncertain_requires_explicit_confirmation_and_resolution_restart(self):
        # Issue #16 L59-62: no recursive notice or blind resend after uncertainty.
        self.setup_queue();self.tick()
        notice=json.loads(self.pending.read_text())
        d.suspend(notice,self.pending,'consumo não observável')
        self.tick(9000)
        self.assertEqual(json.loads(self.pending.read_text())['phase'],'uncertain')
        self.assertEqual(d.queue_notice('w11:p8'),'')
        with patch.object(d,'Herdr',return_value=d.Herdr()):
            d.reconcile(self.pending,'consumed','Líder confirmou que leu o aviso; compositor vazio')
        self.assertEqual(self.actual()['submitted'],[])  # no unverified key/paste
        self.assertEqual(d.queue_notice('w11:p8'),'Fila travada · perguntei ao líder')
        def interrupted(pending,path,state):
            # Crash halfway through removal, after the durable decision.
            d.Path(state['paths'][0]).unlink()
            raise RuntimeError('crash simulado')
        with patch.object(d,'finish_resolution',side_effect=interrupted):
            with self.assertRaisesRegex(RuntimeError,'crash simulado'):
                d.resolve_queue('w11:p8',['0','1','2','3'],'T6 integrado, fila conferida')
        # Production worker resumes the persisted decision, including a missing file.
        self.assertEqual(d.watch(self.queued[-1]),0)
        self.assertEqual(self.actual()['submitted'],['T13 pronto','outro pedido','$code-review'])

    def test_autonomous_worker_lone_uncertain_to_tasks_pty_and_decision(self):
        # Issue #16 L24-37,64-68; spec #1 L153,172: production worker + Tasks PTY.
        self.autonomous('uncertain')

    def test_autonomous_worker_human_draft_without_other_clicks(self):
        # Same contract: waiting is timed, human draft and pending notice survive.
        self.autonomous('draft')

    def autonomous(self, scenario):
        import signal
        import time
        from dataclasses import asdict
        from test_actions import FakeBinding
        from test_artifacts_yazi import Terminal
        from test_tasks_ui import BOUND_SCRIPT, ROOT
        clock=self.root/'clock'
        def set_clock(value):
            temporary=self.root/'clock.tmp';temporary.write_text(str(value));temporary.replace(clock)
        set_clock(1000)
        site=self.root/'site';site.mkdir()
        (site/'sitecustomize.py').write_text(
            "import time,os\nfrom pathlib import Path\n"
            "clock=Path(os.environ['TEST_CLOCK'])\n"
            "time.time=lambda:float(clock.read_text())\n")
        env=dict(self.env,TEST_CLOCK=str(clock),PYTHONPATH=str(site)+os.pathsep+self.env['PYTHONPATH'])
        agent='claude' if scenario=='draft' else 'codex'
        self.state.update(draft='rascunho humano' if scenario=='draft' else '',agent=agent,
                          paste_delay=.12 if scenario=='draft' else 60)
        self.save()
        script='''from watchdog_app import pane_delivery as d
from pathlib import Path
import os
original=d.background_waiter
def background(record):
 pid=original(record);Path(os.environ['FIXTURE_ROOT'],'worker.pid').write_text(str(pid));return pid
d.background_waiter=background
try:d.send('w11:p8','Aviso antigo T6',timeout=.3)
except d.DeliveryPending:pass
'''
        proc=subprocess.Popen([sys.executable,'-c',script],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        out,err=proc.communicate(timeout=5);self.assertEqual(proc.returncode,0,out+err)
        pid=int((self.root/'worker.pid').read_text())
        def cleanup():
            try:os.kill(pid,signal.SIGTERM)
            except ProcessLookupError:pass
        self.addCleanup(cleanup)
        pending=next((self.root/'xdg/herdr-watchdog/pane-locks').glob('*.pending.json'))
        def wait_for(predicate):
            until=time.monotonic()+8
            while time.monotonic()<until:
                try:
                    if predicate():return
                except FileNotFoundError:
                    pass
                time.sleep(.03)
            self.fail('worker não avançou: '+str(list(pending.parent.iterdir())))
        if scenario=='uncertain':
            set_clock(1003)
            wait_for(lambda:json.loads(pending.read_text())['phase']=='uncertain')
            current=self.actual();current.pop('paste',None);current['paste_delay']=.12
            (self.root/'state.json').write_text(json.dumps(current))
        # Restart and concurrent workers share the lease and the same notice intent.
        os.kill(pid,signal.SIGTERM)
        restarted=[]
        for _ in range(2):
            worker=subprocess.Popen([sys.executable,'-m','watchdog_app.pane_delivery','watch',str(pending)],env=env,
                                    stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            restarted.append(worker)
            def clean_worker(worker=worker):
                if worker.poll() is None:worker.terminate()
                worker.wait(timeout=5)
            self.addCleanup(clean_worker)
        # No second send or click wakes the stalled front.
        set_clock(1125)
        statepath=pending.with_name(pending.name.replace('.pending.json','.stalled.json'))
        wait_for(statepath.exists)
        (self.root/'TODO.md').write_text('## Next\n- [ ] tarefa isolada\n')
        binding=self.root/'binding.json'
        binding.write_text(json.dumps(dict(repo=str(self.root),binding=asdict(FakeBinding(pane='w11:p8',kind=agent)))))
        tracked_script=BOUND_SCRIPT.replace('from watchdog_app.tasks_ui import run', """from watchdog_app import tasks_ui
original_put=tasks_ui.put
def tracked_put(screen,row,text,*args):
 if row==3:
  tmp=repo/'banner.tmp';tmp.write_text(json.dumps(text));tmp.replace(repo/'banner.json')
 return original_put(screen,row,text,*args)
tasks_ui.put=tracked_put
from watchdog_app.tasks_ui import run""")
        terminal=Terminal([sys.executable,'-c',tracked_script,str(self.root),str(binding),str(ROOT/'tests')],
                          dict(env,TERM='xterm-256color',WATCHDOG_STATE_DIR=str(self.root/'store')))
        self.addCleanup(terminal.close)
        if scenario=='draft':
            self.assertTrue(terminal.wait_for('WATCHDOG / TASKS'))
            self.assertEqual(json.loads((self.root/'banner.json').read_text()),'')
            self.assertEqual(self.actual()['draft'],'rascunho humano')
            self.assertEqual(self.actual()['submitted'],[])
            set_clock(2000)  # notice must not recursively escalate
            current=self.actual();current['draft']=''
            (self.root/'state.json').write_text(json.dumps(current))
        wait_for(lambda:json.loads(statepath.read_text())['status']=='confirmed')
        self.assertEqual(len(self.actual()['submitted']),1)
        self.assertTrue(terminal.wait_for('Fila travada · perguntei ao líder'),terminal.output.decode(errors='replace'))
        # Later requests are saved, not delivered or discarded by the old snapshot.
        for text in ['B','C','B']:
            p=subprocess.Popen([sys.executable,'-c',
                'from watchdog_app import pane_delivery as d; import sys\ntry:d.send("w11:p8",sys.argv[1],timeout=.1,background=False)\nexcept d.DeliveryPending:pass',text],env=env)
            self.assertEqual(p.wait(timeout=5),0)
        self.assertEqual(len(self.actual()['submitted']),1)
        # Preserve B/C, retire the old front; newer B takes its proper place after C.
        p=subprocess.Popen([sys.executable,'-m','watchdog_app.pane_delivery','resolve-queue',
                            '--pane','w11:p8','--evidence','T6 integrado; paste encerrado; pedidos novos preservados'],env=env)
        self.assertEqual(p.wait(timeout=5),0)
        wait_for(lambda:len(self.actual()['submitted'])==3)
        self.assertEqual(self.actual()['submitted'][1:],['C','B'])
        self.assertFalse(statepath.exists())
        wait_for(lambda:json.loads((self.root/'banner.json').read_text())=='')
        for worker in restarted:self.assertEqual(worker.wait(timeout=5),0)
        self.assertEqual(len([p for p in pending.parent.glob('*.stalled.*') if p.is_dir()]),1)

    def test_observed_progress_resets_deadline_in_production_handshake(self):
        # Issue #16 L58: an actual paste transition resets the inactivity deadline.
        self.setup_queue(age=0)
        self.front.update(phase='waiting',last_progress_at=1000)
        atomic(self.pending,self.front)
        now=[1000]
        class ClockedHerdr(d.Herdr):
            def call(self,*args):
                result=super().call(*args)
                if args[:2]==('pane','send-text'):now[0]=1100
                return result
        with patch.object(d.time,'time',side_effect=lambda:now[0]), \
             patch.object(d.time,'sleep',side_effect=d.DeliveryPending('pausa do teste')):
            with self.assertRaises(d.DeliveryPending):
                d.advance(ClockedHerdr(),self.front,self.pending)
        progressed=json.loads(self.pending.read_text())
        self.assertEqual(progressed['phase'],'pasting')
        self.assertEqual(progressed['last_progress_at'],1100)
        self.tick(1220)
        self.assertEqual(json.loads(self.pending.read_text()),progressed)
        self.tick(1221)
        self.assertTrue(json.loads(self.pending.read_text())['stall_notice'])
