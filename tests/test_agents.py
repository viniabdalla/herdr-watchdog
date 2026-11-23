"""Monitor identity and transcript boundaries, without live agents."""
from dataclasses import asdict
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest


class AgentTests(unittest.TestCase):
    def test_usage_module_is_local(self):
        from watchdog_app import agent_usage
        self.assertTrue(Path(agent_usage.__file__).resolve().is_relative_to(Path(__file__).resolve().parents[1]))

    def test_codex_incremental_partial_and_rotation(self):
        from watchdog_app.agent_usage import read_usage
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'log.jsonl'; cache = {}
            def event(context, total):
                return json.dumps({'payload': {'type':'token_count', 'info': {
                    'last_token_usage':{'total_tokens':context}, 'model_context_window':1000000,
                    'total_token_usage':{'total_tokens':total}}}})+'\n'
            path.write_text(event(12000,90000))
            self.assertEqual(read_usage(path,cache),(12000,1000000,90000))
            with path.open('a') as f:f.write(event(24000,110000).rstrip('\n'))
            self.assertEqual(read_usage(path,cache),(12000,1000000,90000))
            with path.open('a') as f:f.write('\n')
            self.assertEqual(read_usage(path,cache),(24000,1000000,110000))
            path.rename(path.with_suffix('.old'));path.write_text(event(500,700))
            self.assertEqual(read_usage(path,cache),(500,1000000,700))

    def test_claude_stream_updates_deduplicate_message_and_ignore_other_session(self):
        from watchdog_app.agent_usage import claude_usage
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'log.jsonl';cache={}
            def message(sid, output):
                return json.dumps({'type':'assistant','sessionId':sid,'message':{
                    'id':'message','model':'claude-1m','usage':{'input_tokens':12000,
                    'cache_read_input_tokens':3000,'output_tokens':output}}})+'\n'
            path.write_text(message('sid',10)+message('other',900)+message('sid',20))
            self.assertEqual(claude_usage(path,cache,'sid'),(15000,15020,'claude-1m'))
            self.assertEqual(claude_usage(path,cache,'sid'),(15000,15020,'claude-1m'))

    def test_meter_shows_missing_data_and_real_window(self):
        from watchdog_app.agent_usage import usage_meter
        self.assertIn('Sem dados',usage_meter(None))
        text=usage_meter({'context':250000,'window':1000000,'total':1600000})
        for part in ('250k','1M','25%','1,6M'):self.assertIn(part,text)

    def test_changed_session_never_reads_old_transcript(self):
        from watchdog_app.agents_ui import describe
        row={'binding':{'kind':'codex','session':'original','pane':'p','terminal':'t',
                        'workspace':'w','account':'/missing','history':'/missing'}}
        state,usage=describe(row,{'terminal_id':'t','agent':'codex',
            'agent_session':{'kind':'id','value':'replacement'},'agent_status':'idle'}, {})
        self.assertIn('Sessão alterada',state);self.assertIsNone(usage)

    def test_only_exact_leaders_runs_are_shown_and_no_duplicate_actors(self):
        from watchdog_app.agents_ui import agent_rows
        from test_actions import FakeBinding
        main=asdict(FakeBinding())
        worker=dict(main,session='worker',pane='worker-pane',terminal='worker-terminal')
        run={'id':'run','main':main,'phase':'active','tasks':{'t':{'state':'review','title':'Work'}},
             'participants':{'worker':{'native':worker,'model':'gpt','effort':'medium'}},
             'resources':{'worker':{'pane_id':'worker-pane','terminal_id':'worker-terminal'}}}
        unrelated=dict(run,main=dict(main,session='another'))
        rows=agent_rows(SimpleNamespace(binding=FakeBinding()),[run,run,unrelated])
        self.assertEqual(len(rows),2)
        self.assertEqual(rows[1]['binding']['session'],'worker')
        self.assertIn('revisão',rows[1]['delivery'].lower())
