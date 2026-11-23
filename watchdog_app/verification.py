"""Bounded read-only Mission Control run evidence assessment.

Run with python3 -B -m watchdog_app.verification --run UUID --state-dir PATH
--observations PATH. Output never changes a run, a task, a pane or a TODO.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from .project_instructions import read_regular, digest

LIMIT=2*1024*1024
STAGES=('preparing','running','verifying','waiting-for-approval')


def read_observations(path):
    raw=read_regular(path,LIMIT);records=[];issues=[]
    for number,line in enumerate(raw.splitlines(keepends=True),1):
        if not line.endswith(b'\n'):continue
        try:
            row=json.loads(line)
            if not isinstance(row,dict):raise ValueError('object required')
            records.append(row)
        except (ValueError,UnicodeError):issues.append('invalid observation line '+str(number))
    return dict(records=records,incomplete=bool(raw and not raw.endswith(b'\n')),issues=issues,digest=digest(raw))


def qa_valid(run,candidate):
    qa=run.get('qa') or {};contract=run.get('review_contract') or {}
    return bool(candidate and re.fullmatch('[0-9a-f]{40}',candidate) and
        run.get('qa_finished') is True and qa.get('status')=='qa' and qa.get('verdict')=='pass' and
        qa.get('candidate')==candidate==contract.get('candidate') and
        type(contract.get('version')) is int and contract['version']>=1 and
        contract.get('version')==run.get('result_version') and contract.get('verified_commits') is True and
        isinstance(contract.get('id'),str) and bool(contract['id']) and
        qa.get('review_id')==contract.get('id') and qa.get('tests') and
        run.get('tasks') and all(t.get('result') and t.get('state') in ('review','done') for t in run['tasks'].values()))


def assess(run_id,observations,run):
    if run.get('id')!=run_id:raise RuntimeError('Evidence ledger belongs to another run')
    candidate=run.get('candidate');qa=qa_valid(run,candidate);stages=[];issues=[];previous=-1;last_time=None
    for row in observations:
        if row.get('run_id',run_id)!=run_id:raise RuntimeError('Observation belongs to another run')
        when=row.get('observed_at')
        if not isinstance(when,(int,float)) or isinstance(when,bool):
            issues.append('observation lacks numeric timestamp');continue
        if last_time is not None and when<last_time:issues.append('observation time regressed')
        last_time=when
        status=row.get('status')
        if status in ('decision','waiting-for-approval'):
            # A blocked decision is not waiting for approval. Require the exact
            # candidate in that observation and the independently recorded QA gate.
            if not qa or row.get('candidate')!=candidate:continue
            status='waiting-for-approval'
        if status not in STAGES:continue
        index=STAGES.index(status)
        if index<previous:issues.append('stage order regressed: '+status)
        previous=index
        if status not in stages:stages.append(status)
    integration=run.get('integration') or {}
    integrated=bool(candidate and run.get('phase')=='done' and qa and
        integration.get('candidate')==candidate and integration.get('how') in ('already','fast-forward','merge') and
        re.fullmatch('[0-9a-f]{40}',str(integration.get('head',''))))
    missing=[s for s in STAGES if s not in stages]
    return dict(run_id=run_id,assessed_at=datetime.now(timezone.utc).isoformat(),
        evidence_kind='read-only ledger assessment',observed_stages=stages,missing_stages=missing,
        ordered=not issues,issues=issues,candidate=candidate,exact_candidate_qa=qa,
        integrated=integrated,pushed=bool(integrated and integration.get('pushed') is True),
        complete=not missing and not issues and qa and integrated,
        unperformed=['Actual agent rule-reading acknowledgement remains manual',
                     'No live model, native queue or kernel behavior is established by fixture tests'],
        failures=[str(run[k])[:1000] for k in ('reason','monitor_problem') if run.get(k)]+
                 ['observed '+str(row.get('status'))+' at '+str(row.get('observed_at'))
                  for row in observations if row.get('status') in ('stalled','blocked','unavailable')])


def observe(run_id,state_dir,observations):
    if not re.fullmatch('[0-9a-f-]{36}',run_id):raise RuntimeError('Invalid run ID')
    ledger=Path(state_dir)/(run_id+'.json');raw=read_regular(ledger,8*1024*1024)
    source=read_observations(observations);result=assess(run_id,source['records'],json.loads(raw))
    result.update(ledger=str(ledger),ledger_digest=digest(raw),observations=str(observations),
                  observations_digest=source['digest'],incomplete=source['incomplete'])
    result['issues']+=source['issues']
    if source['incomplete'] or source['issues']:result['complete']=False
    return result


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',required=True)
    p.add_argument('--state-dir',type=Path,required=True);p.add_argument('--observations',type=Path,required=True)
    a=p.parse_args(argv)
    print(json.dumps(observe(a.run,a.state_dir,a.observations),indent=2));return 0

if __name__=='__main__':raise SystemExit(main())
