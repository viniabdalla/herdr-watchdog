"""Read explicitly selected JSON plans into bounded, non-authorizing contracts."""
import argparse
import json
from pathlib import Path
import sys
from .project_instructions import project, read_regular, digest
from .todo import Snapshot, single_line
from .todo_format import canonical_id

LIMIT=256*1024
FORMAT='watchdog-plan-v1'


def scoped_path(repo,name):
    if not isinstance(name,str) or not name or '\\' in name or any(ord(c)<32 for c in name):
        raise RuntimeError('Invalid scoped path')
    path=Path(name)
    if path.is_absolute() or '..' in path.parts or name in ('.',''):
        raise RuntimeError('Path escapes project scope')
    target=repo/path
    if any(p.is_symlink() for p in (target,*target.parents)):
        raise RuntimeError('Symlink path refused')
    if not target.resolve().is_relative_to(repo):raise RuntimeError('Path escapes project')
    return target


def strings(values,label):
    if not isinstance(values,list) or not 0<len(values)<=100:
        raise RuntimeError('Missing or excessive '+label)
    return [single_line(v,label) for v in values]


def preview(repo, source, *, format):
    repo=project(repo)
    if format!=FORMAT:raise RuntimeError('Declare watchdog-plan-v1 format')
    path=scoped_path(repo,source);raw=read_regular(path,LIMIT)
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:raise RuntimeError('Duplicate JSON field')
            result[key]=value
        return result
    plan=json.loads(raw,object_pairs_hook=pairs)
    if not isinstance(plan,dict) or set(plan)!= {'format','tasks'} or plan['format']!=FORMAT:
        raise RuntimeError('Invalid declared plan schema')
    snap=Snapshot.read(repo)
    if snap.format_version!=1:raise RuntimeError('Version-1 TODO required')
    known={t.id:t for t in snap.tasks if canonical_id(t.id) and not t.done}
    tasks=plan['tasks']
    if not isinstance(tasks,list) or not 0<len(tasks)<=100:raise RuntimeError('Plan task limit is 100')
    contracts=[];seen=set()
    for item in tasks:
        if not isinstance(item,dict) or set(item)!= {'id','allowed_files','acceptance','tests','dependencies'}:
            raise RuntimeError('Task contract requires explicit scope, acceptance, tests and dependencies')
        key=item['id']
        if not isinstance(key,str) or key not in known or key in seen:raise RuntimeError('Unknown, closed or duplicate task ID')
        seen.add(key)
        files=strings(item['allowed_files'],'allowed files')
        for file in files:scoped_path(repo,file)
        deps=item['dependencies']
        if not isinstance(deps,list) or len(deps)>100 or len(set(deps))!=len(deps) or any(d not in known for d in deps):
            raise RuntimeError('Unknown or duplicate dependency')
        contracts.append(dict(id=key,title=known[key].title,summary=known[key].summary,allowed_files=files,
            acceptance=strings(item['acceptance'],'acceptance'),tests=strings(item['tests'],'tests'),dependencies=deps))
    # A plan must include its open dependencies so no hidden, unvalidated edge exists.
    graph={t['id']:t['dependencies'] for t in contracts};visiting=set();visited=set()
    def visit(key):
        if key in visiting:raise RuntimeError('Dependency cycle')
        if key in visited:return
        if key not in graph:raise RuntimeError('Open dependency missing from explicit plan')
        visiting.add(key)
        for dep in graph[key]:visit(dep)
        visiting.remove(key);visited.add(key)
    for key in graph:visit(key)
    snap.assert_current()
    if digest(read_regular(path,LIMIT))!=digest(raw):raise RuntimeError('Plan changed while reading')
    result = dict(version=1,project=str(repo),source=source,source_digest=digest(raw),todo_digest=snap.digest,
                contracts=contracts,authorized=False,preview='\n'.join(t['id']+' · '+t['title']+'\n  Files: '+', '.join(t['allowed_files'])+'\n  Acceptance: '+ '; '.join(t['acceptance'])+'\n  Tests (data only): '+ '; '.join(t['tests'])+'\n  Dependencies: '+', '.join(t['dependencies']) for t in contracts))

    if len(json.dumps(result,ensure_ascii=False).encode())>1024*1024:
        raise RuntimeError('Plan output exceeds 1 MiB limit; reduce scope or summary size')
    return result


def assert_current(repo,result):
    if str(project(repo))!=result['project']:raise RuntimeError('Project changed')
    current=preview(repo,result['source'],format=FORMAT)
    if result!=current:raise RuntimeError('Stale or modified plan preview')


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repo',type=Path,required=True)
    p.add_argument('--source',required=True);p.add_argument('--format',required=True)
    p.add_argument('--expected-digest')
    p.add_argument('--human',action='store_true')
    a=p.parse_args(argv)
    try:
        result=preview(a.repo,a.source,format=a.format)
        if a.expected_digest and result['source_digest']!=a.expected_digest:raise RuntimeError('Stale plan source')
        print(result['preview'] if a.human else json.dumps(result,ensure_ascii=False,indent=2));return 0
    except (RuntimeError,OSError,ValueError,TypeError) as e:
        print('Watchdog: '+str(e),file=sys.stderr);return 1
