"""Regressions found by the independent review; real provider/process boundaries."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_mission_provider as provider_tests
import test_mission_bundle as bundle_tests
from watchdog_app import mission_launch, mission_native, mission_fresh, mission_plan, mission


def appserver(root, *, hangs=False):
    path = root/'fake-codex'
    path.write_text('#!'+sys.executable+'\n'+('import time\ntime.sleep(10)\n' if hangs else '''import json, sys
for line in sys.stdin:
 m=json.loads(line)
 with open('requests.jsonl','a') as f: f.write(line)
 if 'id' not in m: continue
 method=m['method']
 result={} if method=='initialize' else {'thread':{'id':'thread'}} if method=='thread/start' else {'turn':{'id':'turn'}}
 print(json.dumps({'id':m['id'],'result':result}),flush=True)
 if method=='turn/start':
  print(json.dumps({'method':'item/completed','params':{'turnId':'turn','item':{'type':'plan','text':'A real subprocess proposal'}}}),flush=True)
  print(json.dumps({'method':'turn/completed','params':{'turn':{'id':'turn','status':'completed'}}}),flush=True)
'''))
    path.chmod(0o700)
    return str(path)


class RecoveryTests(unittest.TestCase):
    setUp = provider_tests.ProviderTests.setUp
    fresh = provider_tests.ProviderTests.fresh

    def launched(self, *, plan=False):
        self.fresh()
        if plan:
            self.run['purpose']='plan'; self.brief['purpose']='plan'; self.store.save(self.run)
        return mission_launch.launch(self.store, self.run_id, self.brief, confirmed=True, api=self.api)

    def test_codex_plan_starts_real_provider_process(self):
        job={'executable':appserver(self.root), 'cwd':str(self.repo), 'model':'test', 'effort':'high'}
        self.assertEqual(mission_plan.codex_plan(job, os.environ.copy(), 'Plan only', lambda q:None), 'A real subprocess proposal')

    def test_codex_plan_deadline_covers_a_provider_that_never_replies(self):
        job={'executable':appserver(self.root, hangs=True), 'cwd':str(self.repo), 'model':'test', 'effort':'high'}
        with self.assertRaisesRegex(RuntimeError, 'timed out'):
            mission_plan.codex_plan(job, os.environ.copy(), 'Plan only', lambda q:None, timeout=.1)

    def test_rejected_retry_preserves_previous_assignment_and_review(self):
        run=self.launched(); task_id=next(iter(run['tasks']))
        run['tasks'][task_id].update(delivery='sent', state='blocked')
        run['leader_review']={'verdict':'fail', 'summary':'Retain this review'}; self.store.save(run)
        before=self.store.path(self.run_id).read_bytes()
        (self.repo/'a.py').write_text('dirty main')
        with self.assertRaisesRegex(RuntimeError, 'clean'):
            mission_fresh.retry(self.store, self.run_id, task_id, 'Fix it', api=self.api)
        self.assertEqual(self.store.path(self.run_id).read_bytes(), before)

    def test_followup_retains_live_monitor_identity(self):
        from watchdog_app.mission_broker import process
        run=self.launched(); task_id=next(iter(run['tasks']))
        run['tasks'][task_id].update(delivery='sent', state='blocked')
        child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'])
        self.addCleanup(lambda: (child.terminate(),child.wait()))
        run['monitor_pid']=child.pid; run['monitor_started']=process(child.pid)[1]; self.store.save(run)
        with patch.object(mission_launch,'start_monitor',side_effect=AssertionError('Duplicate monitor')):
            new=mission_fresh.retry(self.store,self.run_id,task_id,'Continue',api=self.api)
        self.assertEqual(new['monitor_pid'], child.pid)
        self.assertEqual(new['monitor_started'], run['monitor_started'])

    def test_dead_planner_wrapper_becomes_blocked_without_relaunch(self):
        run=self.launched(plan=True); part=run['participants']['worker']
        record=run['deliveries'][part['startup_attempt']]
        record.update(method='plan',state='running',wrapper_pid=999999999,wrapper_started='1',wrapper_boot=mission_native.boot_id())
        for task in run['tasks'].values(): task.update(delivery='sent',state='working')
        self.store.save(run)
        with patch.object(mission_native,'forward'):
            updated=mission_native.tick(self.store,self.run_id)
        self.assertTrue(all(t['state']=='blocked' for t in updated['tasks'].values()))
        self.assertTrue(updated['events'])
        self.assertEqual(len(updated['deliveries']),1)

    def test_large_proposal_notification_points_to_stored_artifact(self):
        from types import SimpleNamespace
        from test_actions import FakeBinding
        import uuid
        run=self.launched(plan=True)
        report={'status':'planned','summary':'Plan ready','plan':'"'*65536,'plan_file':'/owned/plan.md'}
        run['events']['event']={'report':report,'delivery':'pending','role':'worker'}
        messages=[]
        runtime=SimpleNamespace(queue=lambda binding,message: messages.append(message) or str(uuid.uuid4()))
        session=SimpleNamespace(binding=FakeBinding(),runtime=runtime)
        with patch('watchdog_app.mission_transport.main_session',return_value=session):
            mission_native.forward(self.store,run)
        self.assertEqual(run['events']['event']['delivery'],'sent')
        self.assertEqual(len(messages),1)
        self.assertLess(len(messages[0].encode()),65536)
        self.assertIn('/owned/plan.md', messages[0])
        self.assertEqual(run['events']['event']['report']['plan'], report['plan'])


class PlanScopeTests(unittest.TestCase):
    setUp = bundle_tests.GroupRequestTests.setUp
    tasks = bundle_tests.GroupRequestTests.tasks

    def test_joint_plan_does_not_authorize_extra_tasks_in_separate_execution(self):
        snapshot, ids=self.tasks()
        store=mission.RunStore()
        plan=mission.request_batch(self.session,snapshot,ids,confirmed=True,purpose='plan')[0]
        plan['phase']='active'
        for task in plan['tasks'].values(): task.update(state='review',plan='Implement First AND Second')
        store.save(plan); self.delivered.clear()
        runs=mission.request_batch(self.session,snapshot,ids,confirmed=True,grouping='separate')
        self.assertTrue(all(not r.get('approved_plans') for r in runs))
        self.assertNotIn('Approved proposal',self.delivered[0][2])
