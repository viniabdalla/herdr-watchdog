"""Native identity bootstrap: host verifies, participant publishes, leader only reads."""
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from watchdog_app import mission_transport as transport
from watchdog_app.mission import RunStore
from test_actions import FakeBinding
from dataclasses import asdict


class IdentityTests(unittest.TestCase):
    def test_register_reads_graph_as_leader_and_never_publishes_as_worker(self):
        with tempfile.TemporaryDirectory() as folder:
            store=RunStore(folder); identity='d5ac58a0-ea68-426b-b639-99d5433b71c9';(store.root/identity).mkdir()
            native=FakeBinding(); native.pane='worker-pane';native.terminal='worker-terminal'
            run={'id':identity,'repo':folder,'transport':{'gossip':'room','nickname':'leader','pubkey':'leader-key'},
                 'resources':{'worker':{'pane_id':native.pane,'terminal_id':native.terminal}},
                 'participants':{'worker':{'nickname':'worker','account':native.account,'worktree':folder}}}
            (store.root/identity/'worker-gossip.json').write_text(json.dumps({'nickname':'worker','gossip':'room','pubkey':'worker-key'}))
            with patch.object(transport.bindings,'discover',return_value=([native],[])), patch.object(transport.bindings,'verify'), patch.object(transport,'publish_identity') as publish, patch.object(transport,'verify_graph'):
                transport.register(run,store,[{'nickname':'worker','pubkey':'worker-key'}])
            publish.assert_not_called()
            self.assertTrue(run['participants']['worker']['available'])

    def test_graph_verification_uses_leader_peer(self):
        run={'transport':{'gossip':'room','nickname':'leader','pubkey':'leader-key'},
             'main':{'session':'main'},'graph':{'instance':'d5ac58a0-ea68-426b-b639-99d5433b71c9','hash':'hash','name':'team'},
             'participants':{'worker':{'nickname':'worker','pubkey':'worker-key','native':{'session':'worker'}}}}
        graph=run['graph'];doc={}
        for role,key,native,nick in [('leader','leader-key',run['main'],'leader'),('worker','worker-key',{'session':'worker'},'worker')]:
            doc[key]={**graph,'graph':'team','node':role,'nickname':nick,'native':native,**({'leader':True} if role=='leader' else {})}
        with patch.object(transport,'command',return_value=json.dumps({'document':doc,'absent':[]})) as command:
            transport.verify_graph(run,'worker')
        argv=command.call_args.args[0]
        self.assertEqual(argv[argv.index('--nickname')+1],'leader')

    def test_bootstrap_binds_child_frontend_before_join_and_retains_context_proof(self):
        from watchdog_app import mission_identity as identity
        with tempfile.TemporaryDirectory() as folder:
            store=RunStore(folder);(store.root/'d5ac58a0-ea68-426b-b639-99d5433b71c9').mkdir()
            native=FakeBinding();native.pane='p';native.terminal='t'
            run={'id':'d5ac58a0-ea68-426b-b639-99d5433b71c9','repo':folder,'resources':{'worker':{'pane_id':'p','terminal_id':'t'}},
                 'transport':{'gossip':'room'},'participants':{'worker':{'account':native.account,'worktree':folder,'nickname':'worker'}}}
            store.save(run)
            context={'session_id':native.session,'owner_pid':native.pid,'owner_start':int(native.started),
                     'generation':'generation','boot_id':'boot','context_file':folder+'/context','state_file':folder+'/state'}
            calls=[]
            def command(argv,**kwargs):
                calls.append(argv)
                if argv[1:3]==['context','bind']:return json.dumps(context)
                self.assertEqual(argv[1],'join')
                self.assertEqual(argv[argv.index('--owner-pid')+1],str(native.pid))
                self.assertEqual(argv[argv.index('--session-context')+1],context['context_file'])
                Path(context['state_file']).write_text(json.dumps({'ready':True,'gossip':'room','nickname':'worker','pubkey':'key',
                    'session_context':{k:context[k] for k in ('session_id','owner_pid','owner_start','generation','boot_id')}}))
                return ''
            with patch.object(identity,'owned_worktree'),patch.object(identity.bindings,'discover',return_value=([native],[])),patch.object(identity.bindings,'verify'),patch.object(identity,'command',side_effect=command):
                proof=identity.bootstrap(store,'d5ac58a0-ea68-426b-b639-99d5433b71c9','worker',SimpleNamespace(pid=native.pid,poll=lambda:None))
            self.assertEqual(proof['native'],asdict(native))
            self.assertEqual(calls[0][1:3],['context','bind'])
            self.assertEqual(json.loads((store.root/'d5ac58a0-ea68-426b-b639-99d5433b71c9'/'worker-identity.json').read_text())['context'],context)

    def test_enroll_rejects_another_task_before_publication(self):
        from watchdog_app import mission_identity as identity
        with tempfile.TemporaryDirectory() as folder:
            store=RunStore(folder);(store.root/'d5ac58a0-ea68-426b-b639-99d5433b71c9').mkdir()
            native=asdict(FakeBinding())
            store.save({'id':'d5ac58a0-ea68-426b-b639-99d5433b71c9','participants':{'worker':{}},'resources':{}})
            (store.root/'d5ac58a0-ea68-426b-b639-99d5433b71c9'/'worker-identity.json').write_text(json.dumps({'native':native,'context':{}}))
            with patch.object(identity,'command',return_value=json.dumps({'session_id':'another','owner_pid':native['pid']})),patch.object(transport,'publish_identity') as publish:
                with self.assertRaisesRegex(RuntimeError,'verified native participant'):
                    identity.enroll(store,'d5ac58a0-ea68-426b-b639-99d5433b71c9','worker')
            publish.assert_not_called()

    def test_recovery_requires_confirmation_and_refuses_dispatched_work(self):
        from watchdog_app.mission_identity import recover_role
        with tempfile.TemporaryDirectory() as folder:
            store=RunStore(folder)
            run={'id':'d5ac58a0-ea68-426b-b639-99d5433b71c9','phase':'active','tasks':{'task':{'delivery':'sent'}}}
            store.save(run)
            with patch('watchdog_app.mission_launch.main_session'),patch('watchdog_app.mission_launch.source_current'),patch('os.kill') as kill:
                with self.assertRaisesRegex(RuntimeError,'confirmation'):recover_role(store,run['id'],'worker')
                with self.assertRaisesRegex(RuntimeError,'dispatched'):recover_role(store,run['id'],'worker',confirmed=True)
                kill.assert_not_called()

    def test_recovery_refuses_dirty_worktree_without_changing_it(self):
        from watchdog_app.mission_identity import recover_role
        import test_mission_launch
        fixture=test_mission_launch.LaunchTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        run=fixture.start();path=Path(run['participants']['worker']['worktree'])
        dirty=path/'new.py';dirty.write_text('keep this')
        with patch('os.kill') as kill:
            with self.assertRaisesRegex(RuntimeError,'clean original'):
                recover_role(fixture.store,run['id'],'worker',confirmed=True,api=fixture.api)
            kill.assert_not_called()
        self.assertEqual(dirty.read_text(),'keep this')
        self.assertFalse(fixture.store.load(run['id'])['participants']['worker'].get('identity_recovery'))
