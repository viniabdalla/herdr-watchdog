"""Tasks' explicit cleanup form and background poller; no curses in workers."""
import copy
from dataclasses import asdict
from pathlib import Path
import threading
import time

from . import clean_sessions as backend
from .store import Store

FIELDS=(('remote','Push remote'),('branch','Destination branch (current branch only)'),
        ('owned_paths','Owned files to commit (comma separated; verify ownership)'),
        ('integrate','Approved branches to fast-forward (comma separated; blank = none)'),
        ('executable','Dedicated Codex executable'),('model','Model'),('effort','Reasoning effort'))


class Setup:
    def __init__(self,session):
        self.index=0
        self.policy=backend.defaults(session)

    @property
    def policy(self):
        return {k:([s.strip() for s in v.split(',') if s.strip()] if k in ('owned_paths','integrate') else v)
                for k,v in self.buffers.items()}

    @policy.setter
    def policy(self,value):
        self.buffers={k:(', '.join(v) if isinstance(v,list) else v) for k,v in value.items()}

    def handle(self,key):
        if key in ('tab','\t','down'):
            self.index=(self.index+1)%len(FIELDS)
        elif key in ('up','backtab'):
            self.index=(self.index-1)%len(FIELDS)
        else:
            field=FIELDS[self.index][0];value=self.buffers[field]
            if key in ('backspace','\x7f','\b'):value=value[:-1]
            elif key=='\x15':value=''
            elif isinstance(key,str) and len(key)==1 and key.isprintable() and len(value)<2048:value+=key
            self.buffers[field]=value

    def rows(self,session):
        rows=[('Clean sessions · authorization scope','In progress',None),
              ('Project: '+str(session.repo),None,None),('Current thread: '+session.binding.session,None,None),
              ('Account: '+session.binding.account,None,None),('',None,None)]
        for i,(field,label) in enumerate(FIELDS):
            value=self.buffers[field]
            rows.append((('> ' if i==self.index else '  ')+label+': '+(', '.join(value) if isinstance(value,list) else value),None,None))
        rows.extend([('',None,None),('Request the verified leader to reconcile TODO and save ai-memory handoff.',None,None),
            ('Authorize owned commits, only listed branch integration, push, fresh split/startup,',None,None),
            ('bounded receipt, explicit predecessor release and Watchdog/Orchestrate transfer.',None,None),
            ('Existing agents, panes, Artifacts, Files/Yazi and layout are preserved.',None,None),
            ('An active native run blocks transfer until finished. Legacy ledgers stay historical.',None,None),
            ('Tab/Up/Down: choose field · Ctrl+U: clear · Enter: review · Esc: cancel',None,None)])
        return rows


def confirmation_rows(session,policy):
    return [('Confirm Clean sessions','In progress',None),('Project: '+str(session.repo),None,None),
            ('Current thread: '+session.binding.session,None,None),('Account: '+session.binding.account,None,None),
            *[(label+': '+(', '.join(policy[k]) if isinstance(policy[k],list) else policy[k]),None,None) for k,label in FIELDS],
            ('Leader reconciles TODO honestly and saves bounded context through ai-memory.',None,None),
            ('Backend commits only owned files, fast-forwards listed branches, pushes and verifies checkpoint.',None,None),
            ('Create a fresh leader split; require its actual receipt and predecessor release.',None,None),
            ('Transfer Tasks/Progress/Orchestrate. Existing actors/panes remain. No TODO completion on dispatch.',None,None)]


class Controller:
    def __init__(self,repo,store=None):
        self.repo=Path(repo);self.store=store or Store();self.operation=None
        self.thread=None;self.result=None;self.next_poll=0

    def start(self,session,policy):
        self.operation=backend.request(session,copy.deepcopy(policy),confirmed=True,store=self.store)
        return self.operation

    def poll(self,binding):
        if self.thread is not None:
            if self.thread.is_alive():return
            self.thread=None
            if self.result is not None:self.operation=self.result;self.result=None
        if time.monotonic()<self.next_poll:return
        self.next_poll=time.monotonic()+2
        relevant=[op for op in backend.operations(self.store,self.repo)
                  if asdict(binding) in (op['source'],op.get('target'))]
        if relevant:self.operation=max(relevant,key=lambda op:op['created'])
        if not self.operation or self.operation['state'] in ('partial','blocked')+backend.SETTLED:return
        identity=self.operation['operation_id']
        def work():
            try:self.result=backend.advance(self.store,identity)
            except (RuntimeError,OSError,ValueError,KeyError,TypeError) as error:
                # Includes busy locks; preserve the durable state and show error.
                self.result=copy.deepcopy(self.operation)
                self.result['problem']=str(error)
        self.thread=threading.Thread(target=work,daemon=True);self.thread.start()

    @property
    def stuck(self):
        return self.operation if self.operation and self.operation['state'] in ('partial','blocked') else None

    def retry(self):
        self.operation=backend.retry(self.store,self.stuck['operation_id']);self.next_poll=0
        return self.operation

    def close(self):
        self.operation=backend.close(self.store,self.stuck['operation_id'])
        return self.operation

    def stuck_rows(self):
        op=self.stuck
        rows=[('Clean sessions stopped · '+op['state']+' at '+op['stage'],'Blocked',None),
              ('Operation '+op['operation_id'],None,None),('Problem: '+str(op.get('problem','unknown')),'Blocked',None)]
        if op.get('left_uncommitted'):rows.append(('Left uncommitted (not in the list): '+', '.join(op['left_uncommitted']),None,None))
        rows.append(('',None,None))
        if op['state']=='partial':rows.append(('y: retry from the step that stopped (nothing already done is repeated)',None,None))
        rows+=[('x: close it — the record stays as evidence; then press c to start a new Clean sessions',None,None),
               ('Esc: back',None,None)]
        return rows

    def rows(self):
        op=self.operation
        if not op or op['state']=='closed':return []
        if op['state']=='released':
            # Finished: one short line, then gone; the record stays in Watchdog state.
            if time.time()-op.get('updated',0)>600:return []
            return [('Clean sessions done · new leader '+str(op.get('target',{}).get('pane','')),'Done',None),('',None,None)]
        color='Blocked' if op['state'] in ('blocked','partial') else 'In progress'
        rows=[('Clean sessions · '+op['state']+' · '+op['stage']+' · '+op['operation_id'],color,None)]
        if op.get('problem'):rows.append((op['problem'],color,None))
        if op.get('checkpoint'):rows.append(('Verified checkpoint: '+op['checkpoint'],None,None))
        if op.get('left_uncommitted'):rows.append(('Left uncommitted (not in the list): '+', '.join(op['left_uncommitted']),None,None))
        if op['state'] in ('partial','blocked'):
            rows.append(('Press c to retry or close it.',color,None))
        return rows+[('',None,None)]
