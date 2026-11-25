"""Isolated Herdr/Codex boundaries: delayed paste, submission, queue receipts."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
SID = '11111111-1111-4111-8111-111111111111'

SCRIPT = '''#!/usr/bin/env python3
import json,os,sys,time,textwrap
from pathlib import Path
root=Path(os.environ['FIXTURE_ROOT']);args=sys.argv[1:];p=root/'state.json'
s=json.loads(p.read_text())
def save():p.write_text(json.dumps(s))
def info():
 return dict(pane_id='w11:p8',terminal_id=s.get('terminal','term1'),agent=s.get('agent','codex'),agent_status=s['status'],
             agent_session=dict(kind='id',agent=s.get('agent','codex'),source='herdr:codex',value=s['session']))
if 'paste' in s and time.monotonic()>=s['materialized_at']:
 s['draft']+=s.pop('paste');save()
if s.get('consume_at',float('inf'))<=time.monotonic():
 s['submitted'].append(s['draft']);s['draft']='';s.pop('consume_at');save()
with (root/'commands').open('a') as f:f.write(json.dumps(args)+'\\n')
if args[:2]==['agent','get']:result=dict(agent=info())
elif args[:2]==['agent','read']:
 draft=s['draft']
 if s.get('wrap'):draft='\\n'.join(textwrap.wrap(draft,width=50))
 draft=draft.replace('\\n','\\n  ')
 if s.get('collapsed') and draft:draft='[Pasted text #1]'
 text=('\\x1b[0m\\x1b[48;2;51;30;30m› '+draft if draft else
       '\\x1b[0m\\x1b[48;2;51;30;30m› \\x1b[2mAsk Codex to do anything')
 print(text+'\\x1b[0m\\n\\n  GPT-6 Context 10% used');sys.exit(0)
elif args[:2]==['pane','send-text']:
 s['paste']=args[3];s['materialized_at']=time.monotonic()+s.get('paste_delay',.12);save()
 (root/'paste-started').touch();result={}
elif args[:2]==['pane','send-keys']:
 key=args[3].lower();s.setdefault('keys',[]).append(key)
 if s.get('alter_on_enter'):s['draft']='edição humana';s['stall']=True
 if s.get('change_identity'):s['session']='22222222-2222-4222-8222-222222222222'
 if s['draft'] and not s.get('stall') and 'paste' not in s:
  if not s.get('needs_tab') or key=='tab':
   s['consume_at']=time.monotonic()+s.get('consume_delay',.12)
 save();result={}
elif args[:2]==['agent','prompt']:
 # The unconfirmed native operation still has the same timing gap.
 s['paste']=args[3];s['materialized_at']=time.monotonic()+.12;save();result=dict(agent=info())
else:raise SystemExit('Unsupported fixture command: '+repr(args))
print(json.dumps(dict(result=result)))
'''


# PTY tests need only an idle agent plus a confirmed native prompt. The full
# stateful transport above is used for the paste-window/uncertainty regressions.
IDLE_SCRIPT = '''#!/usr/bin/env python3
import json,os,sys
from pathlib import Path
args=sys.argv[1:]
root=Path(os.environ.get('HERDR_LOG',__file__)).parent
if root.name=='bin':root=root.parent
if (root/'live.json').exists():
 actors=json.loads((root/'live.json').read_text());binding=next((b for b in actors if len(args)>2 and b['pane']==args[2]),actors[0])
else:binding=json.loads((root/'binding.json').read_text())['binding']
Path(os.environ.get('HERDR_LOG',str(root/'commands.jsonl'))).touch(exist_ok=True)
def agent():
 return dict(pane_id=binding['pane'],terminal_id=binding['terminal'],agent=binding['kind'],
  agent_status='idle',agent_session=dict(kind='id',value=binding['session']))
draft=root/'composer.json'
if args[:2]==['agent','read']:
 text=json.loads(draft.read_text()) if draft.exists() else ''
 rendered=text if text else '\\x1b[2mAsk Codex to do anything'
 print('\\x1b[0m\\x1b[48;2;51;30;30m› '+rendered+'\\x1b[0m\\n\\n  Context');sys.exit(0)
if args[:2] in (['pane','send-text'],['pane','send-keys']):
 log=Path(os.environ.get('HERDR_LOG',str(root/'commands.jsonl')))
 with log.open('a') as f:f.write(json.dumps(args)+'\\n')
 draft.write_text(json.dumps(args[3] if args[1]=='send-text' else ''))
 result={}
else:result=dict(agent=agent(),pane=agent())
print(json.dumps(dict(result=result)))
'''



class SubmissionFixture(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        fake=self.root/'herdr';fake.write_text(SCRIPT);fake.chmod(0o755)
        runtime=self.root/'lu/left_undone';runtime.mkdir(parents=True)
        (runtime/'__init__.py').write_text('')
        (runtime/'runtime.py').write_text("def candidates(): raise RuntimeError('Native queue forbidden in this fixture')\ndef queue(*a): raise RuntimeError('Native queue forbidden in this fixture')\n")
        self.env=dict(os.environ, HERDR_BIN_PATH=str(fake), FIXTURE_ROOT=str(self.root),
                      XDG_STATE_HOME=str(self.root/'xdg'), PYTHONPATH=str(ROOT),
                      HERDR_SOCKET_PATH=str(self.root/'herdr.sock'),
                      WATCHDOG_LEFT_UNDONE_ROOT=str(self.root/'lu'))
        self.state=dict(draft='',submitted=[],queued=[],status='idle',session=SID)
        self.save()

    def save(self):
        (self.root/'state.json').write_text(json.dumps(self.state))

    def actual(self):
        return json.loads((self.root/'state.json').read_text())

    def commands(self):
        p=self.root/'commands'
        return [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []

    def start(self, argv):
        p=subprocess.Popen(argv,env=self.env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        def cleanup():
            if p.poll() is None:p.kill()
            p.communicate()
        self.addCleanup(cleanup)
        return p

    def finish(self, p, success=True):
        out,err=p.communicate(timeout=15)
        if success:self.assertEqual(p.returncode,0,out+err)
        else:self.assertNotEqual(p.returncode,0,out+err)
        return err

    def send(self, text, success=True):
        p=self.start([sys.executable,'-c',
            'from watchdog_app.pane_delivery import send; import sys; send("w11:p8",sys.argv[1],timeout=1.5,background=False)',text])
        return self.finish(p,success)

    def notice(self, *args):
        return [sys.executable,str(ROOT/'watchdog'),'aviso','--lider','w11:p8',
                '--pane','w11:pE','--ticket','T6',*args]

    def wait_for(self, name):
        deadline=time.monotonic()+5
        while not (self.root/name).exists() and time.monotonic()<deadline:time.sleep(.01)
        self.assertTrue((self.root/name).exists(),name)
