from dataclasses import asdict
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from watchdog_app import artifacts

class ArtifactTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.repo=Path(self.tmp.name)
        self.log=self.repo/'history.jsonl';self.log.touch()
        self.session=SimpleNamespace(repo=self.repo,binding=SimpleNamespace(kind='codex',session='real',history=str(self.log),account='/account'),verify=lambda:None)
    def rows(self,*rows):self.log.write_text(''.join(json.dumps(r)+'\n' for r in rows))
    def patch(self,text,ok=True):
        return [dict(type='response_item',payload=dict(type='custom_tool_call',name='apply_patch',call_id='c',input=text)),dict(type='response_item',payload=dict(type='custom_tool_call_output',call_id='c',output='Success. Updated the following files:\n' if ok else 'Failed to apply patch'))]
    def test_successful_patch_attribution_uses_result_and_actual_state(self):
        (self.repo/'a.txt').write_text('hello\n')
        self.rows(*self.patch('*** Begin Patch\n*** Add File: a.txt\n+hello\n*** End Patch'))
        result=artifacts.discover(self.session,self.repo)
        entry=result['artifacts'][0]
        self.assertEqual(entry['path'],'a.txt');self.assertEqual(entry['state'],'present')
        self.assertEqual(entry['provenance'],'successful-tool-path; current-bytes-unproven')
        self.assertIn('byte:',entry['evidence'][0]);self.assertTrue(entry['digest'])
        self.assertFalse((self.repo/'other').exists())
    def test_failed_partial_outside_and_symlink_not_attributed(self):
        (self.repo/'a').write_text('a');(self.repo/'link').symlink_to('/etc/passwd')
        for patch,ok in [('*** Add File: a',False),('*** Add File: ../out',True),('*** Add File: link',True)]:
            self.rows(*self.patch(patch,ok));self.assertEqual(artifacts.discover(self.session,self.repo)['artifacts'],[])
        self.rows(self.patch('*** Add File: a')[0])
        with self.log.open('a') as f:f.write('{"type":')
        result=artifacts.discover(self.session,self.repo)
        self.assertEqual(result['artifacts'],[]);self.assertTrue(result['incomplete'])
    def test_rename_and_delete_are_retained_without_reveal_target(self):
        (self.repo/'new').write_text('renamed')
        self.rows(*self.patch('*** Update File: old\n*** Move to: new\n@@\n-x\n+y\n*** Delete File: gone'))
        result=artifacts.discover(self.session,self.repo)
        entries={x['path']:x for x in result['artifacts']}
        self.assertEqual(entries['old']['state'],'missing');self.assertEqual(entries['new']['state'],'present')
        self.assertEqual(entries['gone']['state'],'missing')
    def test_exact_identity_and_scope_verified_before_and_after(self):
        self.session.verify=lambda:(_ for _ in ()).throw(RuntimeError('replaced'))
        with self.assertRaises(RuntimeError):artifacts.discover(self.session,self.repo)
    def test_git_only_changes_never_gain_ai_provenance(self):
        (self.repo/'human').write_text('human edit');self.rows({})
        self.assertEqual(artifacts.discover(self.session,self.repo)['artifacts'],[])

    def test_exact_host_patch_wrapper_is_attributed_but_arbitrary_javascript_is_not(self):
        (self.repo/'a').write_text('hello')
        code='text(await tools.apply_patch('+json.dumps('*** Add File: a')+'));'
        def write(code):
            self.rows(dict(type='response_item',payload=dict(type='custom_tool_call',name='exec',call_id='e',input=code)),
                dict(type='response_item',payload=dict(type='custom_tool_call_output',call_id='e',output=[dict(type='input_text',text='Script completed\nOutput:\n{}')])))
        write(code);self.assertEqual(len(artifacts.discover(self.session,self.repo)['artifacts']),1)
        write(code+'text("fabricated success");');self.assertEqual(artifacts.discover(self.session,self.repo)['artifacts'],[])

    def test_linked_client_checks_exact_owned_files_process(self):
        from unittest.mock import patch
        state=self.repo/'binding.json';state.write_text(json.dumps(dict(yazi_client_id='123',panes=dict(files=dict(pane_id='files')))))
        session=SimpleNamespace(file=state,verify=lambda:None)
        api=SimpleNamespace(panel=lambda pane,repo:pane)
        with patch('watchdog_app.actions.Session.for_panel',return_value=session),patch('watchdog_app.herdr.Herdr',return_value=api),patch('watchdog_app.app.panel_process',return_value=(True,[])) as process:
            self.assertEqual(artifacts.linked_client(state,self.repo,'123'),'123')
            self.assertEqual(process.call_args.args[2],'files')
            for client in ('0','124',None):
                with self.assertRaises(RuntimeError):artifacts.linked_client(state,self.repo,client)
            process.return_value=(False,[])
            with self.assertRaises(RuntimeError):artifacts.linked_client(state,self.repo,'123')
