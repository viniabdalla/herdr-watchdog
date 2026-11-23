from dataclasses import asdict
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from test_actions import FakeBinding


class PanelBinding(FakeBinding):
    @property
    def key(self):return 'binding'


class PaneTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.repo=Path(self.temp.name);self.file=self.repo/'state/binding.json'
        self.file.parent.mkdir();self.binding=PanelBinding()
        self.state={'repo':str(self.repo),'binding':asdict(self.binding),'panes':{},
                    'binding_file':str(self.file),'yazi_client_id':'123','operation':'ready'}
        self.session=SimpleNamespace(binding=self.binding,file=self.file,repo=self.repo,verify=lambda:None)
        self.calls=[];self.live={self.binding.pane:{'pane_id':self.binding.pane,'terminal_id':self.binding.terminal,
            'workspace_id':'project','tab_id':'tab'}}
        self.foreground={}
        from watchdog_app.herdr import Herdr
        self.api=Herdr();self.api.call=self.call
        self.api.request=self.request
        self.write()

    def write(self):self.file.write_text(json.dumps(self.state))

    def call(self,*args):
        self.calls.append(args)
        if args[:2]==('pane','list'):return {'panes':list(self.live.values())}
        if args[:2]==('pane','get'):return {'pane':self.live[args[2]]}
        if args[:2]==('pane','split'):
            pane={'pane_id':'agents-pane','terminal_id':'agents-terminal','workspace_id':'project','tab_id':'tab'}
            self.live[pane['pane_id']]=pane;return {'pane':pane}
        if args[:2]==('pane','process-info'):
            return {'process_info':{'shell_pid':1,'foreground_processes':self.foreground.get(args[3],[])}}
        if args[:2]==('pane','run'):
            import shlex
            self.foreground[args[2]]=[{'pid':2,'name':'python3','argv':shlex.split(args[3])}]
        return {}

    def request(self, method, params):
        self.calls.append((method, params))
        if method != "pane.focus":raise AssertionError(method)
        return {}

    def open(self):
        from watchdog_app.panes import open_pane
        with patch('watchdog_app.panes.Session.for_panel',return_value=self.session):
            return open_pane(self.file,self.repo,'agents',api=self.api)

    def test_reopen_reuses_the_running_pane(self):
        self.open();self.open()
        self.assertEqual(sum(c[:2]==('pane','split') for c in self.calls),1)
        self.assertEqual(sum(c[:2]==('pane','run') for c in self.calls),1)
        self.assertIn(('pane.focus',{'pane_id':'agents-pane'}),self.calls)
        state=json.loads(self.file.read_text())
        self.assertEqual(state['panes']['agents']['launch_state'],'running')

    def test_repurposed_terminal_is_not_touched(self):
        self.open();self.calls.clear()
        self.live['agents-pane']=dict(self.live['agents-pane'],terminal_id='other')
        with self.assertRaisesRegex(RuntimeError,'terminal|substituído'):self.open()
        self.assertFalse(any(c[1] in ('run','split','focus') for c in self.calls))

    def test_busy_panel_is_not_overwritten(self):
        self.open();self.calls.clear()
        self.foreground['agents-pane']=[{'pid':3,'name':'sleep','argv':['sleep','100']}]
        with self.assertRaisesRegex(RuntimeError,'another command'):self.open()
        self.assertFalse(any(c[:2]==('pane','run') for c in self.calls))

    def test_another_watchdog_binding_is_not_reused(self):
        self.open();self.calls.clear()
        argv = self.foreground['agents-pane'][0]['argv']
        argv[argv.index('--binding-file')+1] = str(self.repo/'other-binding.json')
        with self.assertRaisesRegex(RuntimeError,'another command'):
            self.open()
        self.assertFalse(any(c[:2]==('pane','run') or c[0]=='pane.focus' for c in self.calls))

    def test_closed_panel_can_be_recreated(self):
        self.open();del self.live['agents-pane'];self.calls.clear()
        self.open()
        self.assertEqual(sum(c[:2]==('pane','split') for c in self.calls),1)

    def test_cli_pane_routes_without_rearranging_layout(self):
        from watchdog_app.app import main
        with patch('watchdog_app.panes.open_pane',return_value={'pane_id':'agents-pane'}) as opened:
            self.assertEqual(main(['pane','agents','--repo',str(self.repo),'--binding-file',str(self.file)]),0)
        self.assertEqual(opened.call_args.args[:3],(self.file,self.repo,'agents'))
