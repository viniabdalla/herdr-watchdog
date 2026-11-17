"""Owned native boundaries only; no model sessions or production inboxes."""
import json
import os
from pathlib import Path
import shutil
import tempfile
import time
import unittest
import uuid
from unittest.mock import patch

from watchdog_app.mission import accept_event
from watchdog_app.mission_launch import command, open_run
from watchdog_app.mission_transport import Gossip, forward
from watchdog_app.herdr import Herdr
import test_mission_launch
import test_mission_transport


@unittest.skipUnless(os.environ.get('WATCHDOG_GOSSIP_TEST')=='1', 'set WATCHDOG_GOSSIP_TEST=1 for owned Gossip daemons')
class GossipNativeTests(unittest.TestCase):
    def test_real_assignment_blocker_followup_result_and_exact_main_bridge(self):
        fixture=test_mission_transport.TransportTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        run=fixture.run;store=fixture.store
        with tempfile.TemporaryDirectory(prefix='wd-test-gossip-') as folder:
            state=Path(folder)/'main.json';worker=Path(folder)/'worker.json'
            main_nick='wd-test-main-'+uuid.uuid4().hex[:6];worker_nick='wd-test-worker-'+uuid.uuid4().hex[:6]
            command(['agent-gossip','create','--name','wd-test-'+uuid.uuid4().hex[:6],
                     '--nickname',main_nick,'--lookup','mdns','--transport','udp',
                     '--owner-pid',str(os.getpid()),'--state-file',state])
            deadline=time.monotonic()+10
            while time.monotonic()<deadline:
                if state.exists() and json.loads(state.read_text()).get('ready'):break
                time.sleep(.05)
            main_state=json.loads(state.read_text());room=main_state['gossip']
            self.addCleanup(lambda:command(['agent-gossip','leave',room,'--nickname',main_nick]))
            command(['agent-gossip','join',room,'--nickname',worker_nick,'--owner-pid',str(os.getpid()),'--state-file',worker])
            self.addCleanup(lambda:command(['agent-gossip','leave',room,'--nickname',worker_nick]))
            gossip=Gossip({'gossip':room,'nickname':main_nick})
            deadline=time.monotonic()+10
            while not gossip.peers() and time.monotonic()<deadline:time.sleep(.1)
            peer=gossip.peers()[0]
            run['transport']={'gossip':room,'nickname':main_nick}
            run['participants']['worker'].update(nickname=worker_nick,pubkey=peer['pubkey'])
            task_id=gossip.call(peer['nickname'],'Explicit owned boundary contract',expected_key=peer['pubkey'])
            run['tasks']['task']['gossip_task']=task_id
            other=Gossip(run['transport'],worker_nick)
            events=other.poll(0)
            self.assertTrue(any(e.get('task_id')==task_id for e in events))
            blocked={'run_id':run['id'],'task_id':'task','status':'blocked','summary':'Need the fixture path'}
            other.invoke('a2a','status','--task-id',task_id,'--state','input-required','--text',json.dumps(blocked))
            self.assertEqual(gossip.call(peer['nickname'],'Fixture is tests/data; same scope',task_id=task_id,expected_key=peer['pubkey']),task_id)
            result={'run_id':run['id'],'task_id':'task','status':'result','summary':'Implemented controls',
                    'commits':['a'*40],'tests':['python -m unittest: passed']}
            other.invoke('a2a','artifact','--task-id',task_id,'--text',json.dumps(result))
            deadline=time.monotonic()+10
            while time.monotonic()<deadline:
                events=gossip.poll(0)
                if any(e.get('kind')=='artifact-update' for e in events):break
                time.sleep(.1)
            seen=0
            for event in events:
                seen+=bool(accept_event(run,event))
            self.assertEqual(seen,2,events)
            self.assertEqual(run['tasks']['task']['state'],'review')
            forward(store,run)
            forward(store,run)
            self.assertEqual(len(fixture.delivered),2)
            self.assertTrue(all(run['id'] in text for text in fixture.delivered))
            self.assertTrue(any('Need the fixture path' in text for text in fixture.delivered))


@unittest.skipUnless(os.environ.get('WATCHDOG_HERDR_TEST')=='1', 'set WATCHDOG_HERDR_TEST=1 for owned wd-test panes')
class HerdrNativeTests(unittest.TestCase):
    def test_real_single_tab_preserves_unrelated_terminal(self):
        fixture=test_mission_launch.LaunchTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        api=Herdr('wd-test')
        created=api.call('workspace','create','--cwd',str(fixture.repo),'--label','wd-test Mission Control','--no-focus')
        workspace=created['workspace']['workspace_id'];original=created['root_pane']
        self.addCleanup(lambda:api.call('workspace','close',workspace))
        # The launcher itself is real. Native terminal commands use /usr/bin/true,
        # never a model session. The bridge is mocked by the launch fixture.
        fixture.patches[2].stop()  # Real owned Gossip, no model participants.
        fixture.session.binding.pid=os.getpid()
        fixture.run['main']['pid']=os.getpid()
        fixture.session.binding.workspace=workspace
        fixture.run['main']['workspace']=workspace;fixture.run['herdr_session']='wd-test'
        fixture.store.save(fixture.run)
        run=test_mission_launch.launch.launch(fixture.store,fixture.run_id,fixture.brief,confirmed=True,api=api)
        room=run['transport']['gossip']
        self.addCleanup(lambda:command(['agent-gossip','leave',room,'--nickname',run['transport']['nickname']]))
        deadline=time.monotonic()+8
        exits=[fixture.store.root/run['id']/(role+'-exit.json') for role in ('worker','qa')]
        while not all(p.exists() for p in exits) and time.monotonic()<deadline:time.sleep(.1)
        for p in exits:self.assertEqual(json.loads(p.read_text())['code'],0)
        panes=api.call('pane','list','--workspace',workspace)['panes']
        self.assertEqual(len(panes),3)
        self.assertEqual(api.checked(original)['terminal_id'],original['terminal_id'])
        self.assertEqual(api.checked(original)['tab_id'],original['tab_id'])
        team=[p for p in panes if p['tab_id']==run['tab']]
        self.assertEqual(len(team),2)
        open_run(run,api)
        self.assertNotEqual(run['tab'],original['tab_id'])
