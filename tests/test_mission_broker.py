import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from watchdog_app.mission_broker import authorize,context_lease,Broker


class BrokerTests(unittest.TestCase):
    def setUp(self):
        self.native={'pid':100,'started':'200','session':'worker'}

    def test_only_actual_frontend_descendants_pass(self):
        with patch('watchdog_app.mission_broker.process',side_effect=lambda p:{301:(300,'3'),300:(100,'2'),100:(1,'200')}[p]):
            authorize(301,os.getuid(),self.native,'worker')
        with patch('watchdog_app.mission_broker.process',side_effect=lambda p:{301:(300,'3'),300:(1,'2')}[p]):
            with self.assertRaisesRegex(RuntimeError,'not a descendant'):
                authorize(301,os.getuid(),self.native,'worker')

    def test_wrong_thread_user_recycled_pid_and_shared_server_are_denied(self):
        for uid,session in [(os.getuid()+1,'worker'),(os.getuid(),'qa')]:
            with self.assertRaisesRegex(RuntimeError,'user or thread'):
                authorize(301,uid,self.native,session)
        with patch('watchdog_app.mission_broker.process',return_value=(1,'999')):
            with self.assertRaisesRegex(RuntimeError,'recycled'):
                authorize(100,os.getuid(),self.native,'worker')
        with patch('watchdog_app.mission_broker.process',return_value=(1,'999')):
            with self.assertRaisesRegex(RuntimeError,'not a descendant'):
                authorize(888,os.getuid(),self.native,'worker')

    def test_exited_child_and_wrong_role_are_denied_before_any_command(self):
        from types import SimpleNamespace
        broker=Broker.__new__(Broker);broker.identity='run';broker.role='worker'
        broker.child=SimpleNamespace(poll=lambda:0)
        good={'run':'run','role':'worker','session':'worker','method':'enroll','data':{}}
        with patch('watchdog_app.mission_broker.command') as command:
            with self.assertRaisesRegex(RuntimeError,'exited'):broker.execute(1,os.getuid(),good)
            with self.assertRaisesRegex(RuntimeError,'role differs'):broker.execute(1,os.getuid(),dict(good,role='qa'))
            command.assert_not_called()

    def test_changed_generation_is_denied_before_gossip_operation(self):
        broker=Broker.__new__(Broker)
        context={'session_id':'worker','owner_pid':100,'owner_start':200,'generation':'fixed',
                 'context_file':'/private/context.json','state_file':'/private/state.json'}
        broker.proof={'native':self.native,'context':context}
        with patch('watchdog_app.mission_broker.command',return_value=json.dumps(dict(context,generation='changed'))),patch('watchdog_app.mission_transport.Gossip.invoke') as gossip:
            with self.assertRaisesRegex(RuntimeError,'generation changed'):
                broker.execute_locked({'method':'enroll','data':{}})
            gossip.assert_not_called()

    @unittest.skipUnless(shutil.which('rustc'),'Rust toolchain only required for native lock interoperability check')
    def test_context_lease_interoperates_with_rust_bind_lock(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);path=root/'context.lock';path.touch(mode=0o600)
            source=root/'lock.rs';binary=root/'lock'
            source.write_text('use std::fs::OpenOptions; fn main(){let f=OpenOptions::new().read(true).write(true).open(std::env::args().nth(1).unwrap()).unwrap(); match f.try_lock(){Ok(())=>println!("locked"),Err(_)=>println!("blocked")}}')
            subprocess.run(['rustc',str(source),'-o',str(binary)],check=True,capture_output=True,timeout=30)
            probe=lambda:subprocess.check_output([str(binary),str(path)],text=True,timeout=2).strip()
            self.assertEqual(probe(),'locked')
            proof={'context':{'context_file':str(root/'context.json')}}
            with context_lease(proof):self.assertEqual(probe(),'blocked')
            self.assertEqual(probe(),'locked')

    def test_client_identity_is_rechecked_before_the_gossip_operation(self):
        from types import SimpleNamespace
        native={**self.native,'account':'account','pane':'pane','terminal':'terminal'}
        context={'session_id':'worker','owner_pid':100,'owner_start':200,'generation':'fixed',
                 'context_file':'/private/context.json','state_file':'/private/state.json'}
        run={'participants':{'worker':{'account':'account','nickname':'worker'}},
             'resources':{'worker':{'pane_id':'pane','terminal_id':'terminal'}},
             'transport':{'gossip':'room','nickname':'leader'}}
        broker=Broker.__new__(Broker);broker.identity='run';broker.role='worker'
        broker.proof={'native':native,'context':context,'pubkey':'key'}
        broker.store=SimpleNamespace(load=lambda _:run)
        state={'pubkey':'key','nickname':'worker','gossip':'room'}
        message={'session':'worker','method':'poll','data':{'after':0}}
        with patch('watchdog_app.mission_broker.command',return_value=json.dumps(context)),patch.object(Path,'read_text',return_value=json.dumps(state)),patch('watchdog_app.mission_broker.authorize',return_value='changed'),patch('watchdog_app.mission_transport.Gossip.poll',return_value=[]) as poll:
            with self.assertRaisesRegex(RuntimeError,'caller exited or its PID was recycled'):
                broker.execute_locked(message,caller=(999,os.getuid(),'original'))
            poll.assert_not_called()
        with patch('watchdog_app.mission_broker.command',return_value=json.dumps(context)),patch.object(Path,'read_text',return_value=json.dumps(state)),patch('watchdog_app.mission_broker.authorize',return_value='original'),patch('watchdog_app.mission_transport.Gossip.poll',return_value=[]) as poll:
            self.assertEqual(broker.execute_locked(message,caller=(999,os.getuid(),'original')),[])
            poll.assert_called_once_with(0)
