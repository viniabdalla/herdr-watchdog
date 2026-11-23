"""Artifact paths attributed to successful tools in one verified conversation.

Paths are evidence of a tool operation, never authorship of current bytes. Shell
commands, prose and Git diffs alone are deliberately not attribution evidence.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from .transcripts import evidence_tail
from .project_instructions import read_regular


def safe_path(repo,name):
    if not isinstance(name,str) or not name or any(ord(c)<32 for c in name):return None
    path=Path(name)
    target=path if path.is_absolute() else repo/path
    if '..' in path.parts or not target.is_relative_to(repo):return None
    if any(p.is_symlink() for p in (target,*target.parents)):return None
    return target


def patch_paths(text):
    return [(m[2],m[1].lower()) for m in re.finditer(r'^\*\*\* (Add File|Update File|Delete File|Move to): (.+)$',text,re.M)]


def call_paths(name,args):
    if name.split('.')[-1]=='apply_patch':
        return patch_paths(args if isinstance(args,str) else '')
    if name.split('.')[-1]=='exec' and isinstance(args,str):
        # Accept only a literal JSON string passed to apply_patch. Never eval JS.
        match=re.fullmatch(r'\s*text\(await tools\.apply_patch\(("(?:[^"\\]|\\.)*")\)\);?\s*',args)
        return patch_paths(json.loads(match[1])) if match else []
    if isinstance(args,str):
        try:args=json.loads(args)
        except ValueError:return []
    if name in ('Write','Edit','MultiEdit') and isinstance(args,dict):
        return [(args.get('file_path'),'write' if name=='Write' else 'edit')]
    return []


def success(name,result):
    if isinstance(result,dict) and result.get('is_error'):return False
    value=result.get('content',result) if isinstance(result,dict) else result
    text=json.dumps(value) if not isinstance(value,str) else value
    if name.split('.')[-1]=='exec':
        return 'Script completed' in text and 'Script failed' not in text and not re.search(r'Error|isError.*true',text)
    if name.split('.')[-1]=='apply_patch':
        return 'Success. Updated the following files:' in text and not re.search(r'Failed|Error|isError.*true',text)
    return bool(re.search(r'success|created|updated|written|applied',text,re.I)) and not re.search(r'error|failed|not found|denied',text,re.I)


def discover(session,repo):
    repo=Path(repo).resolve();session.verify()
    if Path(session.repo).resolve()!=repo:raise RuntimeError('Artifact project differs from binding')
    binding=session.binding;identity=(binding.kind,binding.session,binding.account,binding.history)
    tail=evidence_tail(binding.history);calls={};found={}
    for row,ref in tail['records']:
        pairs=[]
        if binding.kind=='codex' and row.get('type')=='response_item':
            p=row.get('payload',{});kind=p.get('type')
            if kind in ('function_call','custom_tool_call'):
                calls[p.get('call_id')]=(p.get('name',''),p.get('arguments',p.get('input','')),ref)
            elif kind in ('function_call_output','custom_tool_call_output'):
                pairs=[(p.get('call_id'),p.get('output'))]
        elif binding.kind=='claude' and not row.get('isSidechain') and not row.get('agentId'):
            for p in row.get('message',{}).get('content',[]) if isinstance(row.get('message',{}).get('content'),list) else []:
                if p.get('type')=='tool_use':calls[p.get('id')]=(p.get('name',''),p.get('input',{}),ref)
                if p.get('type')=='tool_result':pairs.append((p.get('tool_use_id'),p))
        for key,result in pairs:
            call=calls.pop(key,None)
            if not call or not success(call[0],result):continue
            for name,operation in call_paths(call[0],call[1]):
                path=safe_path(repo,name)
                if path is None:continue
                relative=str(path.relative_to(repo))
                entry=found.setdefault(relative,dict(path=relative,operations=[],evidence=[]))
                entry['operations'].append(operation);entry['evidence'].extend([call[2],ref])
    entries=[]
    for entry in found.values():
        path=safe_path(repo,entry['path'])
        if path is None:continue
        try:
            raw=read_regular(path,limit=8*1024*1024,missing=True)
            entry.update(state='missing' if raw is None else 'present',digest=hashlib.sha256(raw).hexdigest() if raw is not None else None)
        except (OSError,RuntimeError):
            entry.update(state='unavailable',digest=None)
        entry.update(provenance='successful-tool-path; current-bytes-unproven',
            summary=', '.join(dict.fromkeys(entry['operations']))+' · '+entry['state'],agent=binding.kind)
        entries.append(entry)
    session.verify()
    b=session.binding
    if identity!=(b.kind,b.session,b.account,b.history):raise RuntimeError('Artifact source identity changed')
    return dict(artifacts=entries,history=str(binding.history),session=binding.session,
        source_digest=tail['digest'],incomplete=tail['incomplete'],issues=tail['issues'],
        scope='bounded transcript tool evidence; unsupported shell writes and Git-only changes remain unproven')


def linked_client(binding_file,repo,client):
    """Check the owned Files pane and its foreground Yazi before revealing."""
    from .actions import Session
    from .herdr import Herdr
    from .app import panel_process
    session=Session.for_panel(binding_file,repo);session.verify()
    state=json.loads(session.file.read_text())
    if not client or not client.isdecimal() or not 0<int(client)<2**64 or state.get('yazi_client_id')!=client:
        raise RuntimeError('Files client differs from linked binding')
    api=Herdr();pane=api.panel(state['panes']['files'],repo)
    running,_=panel_process(api,pane,'files',state)
    if not running:raise RuntimeError('Linked Files pane is not running its owned Yazi client')
    return client


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repo',type=Path,required=True)
    p.add_argument('--binding-file',type=Path,required=True);a=p.parse_args(argv)
    try:
        from .actions import Session
        print(json.dumps(discover(Session.for_panel(a.binding_file,a.repo),a.repo),indent=2));return 0
    except (RuntimeError,OSError,ValueError) as e:
        print('Watchdog: '+str(e),file=sys.stderr);return 1
