"""Native provider planning adapted from LU; proposals belong only to Watchdog."""
import json
import os
import selectors
import time
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory


def codex_plan(job, env, prompt, question_status, *, timeout=1200):
    # The interactive binary has no plan-mode startup flag. Its app-server
    # accepts the same collaboration preset as /plan and emits a typed plan.
    proc = subprocess.Popen([job['executable'], 'app-server'], cwd=job['cwd'], env=env,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)

    def write(message):
        proc.stdin.write(json.dumps(message) + '\n')
        proc.stdin.flush()

    deferred = []
    buffer = bytearray()
    deadline = time.monotonic() + timeout
    selector = selectors.DefaultSelector()
    selector.register(proc.stdout, selectors.EVENT_READ)

    def receive():
        while b'\n' not in buffer:
            if len(buffer) > 1048576: raise RuntimeError('Planning response exceeds size limit')
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not selector.select(remaining):
                raise RuntimeError('Codex planning timed out')
            chunk = os.read(proc.stdout.fileno(), 65536)
            if not chunk: raise RuntimeError('Codex closed before returning a plan')
            buffer.extend(chunk)
        line, _, rest = buffer.partition(b'\n')
        buffer[:] = rest
        if len(line) > 1048576: raise RuntimeError('Planning response exceeds size limit')
        return json.loads(line)

    def request(number, method, params):
        write({'id': number, 'method': method, 'params': params})
        while True:
            response = receive()
            if response.get('id') == number and 'method' not in response:
                if 'error' in response:
                    raise ValueError(response['error']['message'])
                return response['result']
            if response.get('method') in ('item/completed', 'turn/completed', 'item/tool/requestUserInput'):
                if len(deferred) >= 128: raise RuntimeError('Too many planning events before acknowledgement')
                deferred.append(response)

    try:
        request(1, 'initialize', {'clientInfo': {'name': 'herdr_watchdog', 'version': '1'},
                                  'capabilities': {'experimentalApi': True}})
        write({'method': 'initialized'})
        thread = request(2, 'thread/start', {'model': job['model'], 'cwd': job['cwd'],
                         'sandbox': 'read-only', 'approvalPolicy': 'never'})['thread']['id']
        mode = {'mode': 'plan', 'settings': {'model': job['model'],
                'reasoning_effort': job['effort'], 'developer_instructions': None}}
        turn = request(3, 'turn/start', {'threadId': thread, 'collaborationMode': mode,
                       'input': [{'type': 'text', 'text': prompt}]})['turn']['id']
        plan = ''
        last_message = ''
        while True:
            event = deferred.pop(0) if deferred else receive()
            method = event.get('method')
            data = event.get('params', {})
            if 'id' in event and method:
                if method == 'item/tool/requestUserInput' and data.get('turnId') == turn:
                    question = '\n'.join(q['question'] for q in data['questions'])
                    question_status(question)
                    raise RuntimeError('Planning needs a leader decision: ' + question)
                else:
                    write({'id': event['id'], 'error': {'code': -32601, 'message': 'Unsupported request'}})
            elif method == 'item/completed' and data.get('turnId') == turn:
                item = data['item']
                if item['type'] == 'plan':
                    plan = item['text']
                elif item['type'] == 'agentMessage':
                    last_message = item['text']
                    print(last_message, flush=True)
            elif method == 'turn/completed' and data['turn']['id'] == turn:
                if data['turn']['status'] != 'completed':
                    raise RuntimeError((data['turn'].get('error') or {}).get('message') or data['turn']['status'])
                if not plan.strip():
                    raise RuntimeError('Codex finished without returning a proposed plan'
                                       + (' · ' + last_message if last_message else ''))
                return plan.strip()
    finally:
        selector.close()
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        proc.stdin.close()
        proc.stdout.close()


def run(kind, job, env, question_status):
    prompt = (f"Prepare an implementation plan for this task in {job['cwd']}:\n{job['task']}\n\n"
              f"Parent agent's brief:\n{job['brief']}\n\n"
              "Return the complete proposed plan in the requested language. "
              "Leave all implementation for a separate execution dispatch.")
    if kind == 'codex':
        return codex_plan(job, env, prompt, question_status)
    # Claude writes its native plan to a named Markdown file. A private
    # directory gives this dispatch exclusive ownership of the result.
    with TemporaryDirectory(dir=job['cwd'], prefix='.watchdog-plan-') as directory:
        argv = [job['executable'], '--print', '--permission-mode', 'plan', '--model', job['model'],
                '--effort', job['effort'], '--tools', 'Read,Glob,Grep,Write,Edit',
                '--settings', json.dumps({'plansDirectory': Path(directory).name}),
                '--output-format', 'json', '--', prompt]
        proc = subprocess.run(argv, cwd=job['cwd'], env=env, stdout=subprocess.PIPE, text=True, timeout=1200)
        result = json.loads(proc.stdout) if proc.stdout.strip() else {}
        if proc.returncode or result.get('is_error'):
            raise RuntimeError(result.get('result') or f'Claude exited with status {proc.returncode}')
        files = [p for p in Path(directory).glob('*.md') if not p.is_symlink() and p.is_file()]
        if len(files) == 1:
            plan = files[0].read_text().strip()
            if plan:
                return plan
        message = result.get('result', '').strip()
        raise RuntimeError('Claude finished without writing a proposed plan' + (' · ' + message if message else ''))


def notify(store, ledger):
    from .mission_native import forward
    try:
        forward(store, ledger)
    except (RuntimeError, OSError, ValueError):
        pass  # Durable pending reports are forwarded by the monitor when the leader returns.


def participant(store, identity):
    """Owned launcher wrapper collects the typed proposal; workers have no result callback."""
    import os
    import time
    import uuid
    from .mission_launch import owned_worktree, source_current, git
    from .mission_fresh import provider_command
    with store.lock(identity):
        ledger = store.load(identity); source_current(ledger)
        if ledger.get('purpose') != 'plan': raise RuntimeError('Not a planning run')
        part = ledger['participants']['worker']
        attempt = part['startup_attempt']
        record = ledger['deliveries'][attempt]
        if record['state'] != 'sending': raise RuntimeError('Planner already started; do not retry blindly')
        path = owned_worktree(ledger, 'worker')
        if git(path, 'status', '--porcelain') or git(path, 'rev-parse', 'HEAD') != part['base_sha']:
            raise RuntimeError('Planner requires its clean approved base')
        from .mission_broker import process
        from .mission_native import boot_id
        record.update(method='plan', state='running', wrapper_pid=os.getpid(),
                      wrapper_started=process(os.getpid())[1], wrapper_boot=boot_id())
        for task in ledger['tasks'].values(): task.update(state='working', delivery='sent', agent='worker', updated=time.time())
        part.update(available=True, last_seen=time.time()); ledger['observed']=time.time()
        store.save(ledger)
    job = {'cwd':str(path), 'task':'\n'.join(t['title'] for t in ledger['tasks'].values()),
           'brief':json.dumps(record['payload'], ensure_ascii=False), **{k:part[k] for k in ('model','effort','executable')}}
    _, env = provider_command(part, '', store, ledger)
    proposal = ''
    problem = ''
    try:
        proposal = run(part.get('kind', 'codex'), job, env, lambda q:None)
        if not isinstance(proposal, str) or not proposal.strip() or len(proposal.encode()) > 65536:
            raise RuntimeError('Planner must return a non-empty bounded proposal')
        if git(path, 'status', '--porcelain') or git(path, 'rev-parse', 'HEAD') != part['base_sha']:
            raise RuntimeError('Planner changed source or commits; changes retained, proposal not accepted')
    except Exception as error:
        problem = str(error)
    with store.lock(identity):
        ledger = store.load(identity); source_current(ledger)
        if ledger['participants']['worker'].get('startup_attempt') != attempt:
            raise RuntimeError('Planner attempt was replaced; result not applied')
        now=time.time(); event_id=str(uuid.uuid4())
        summary = problem or 'Plano pronto; implementação continua pendente'
        report = {'run_id':identity, 'attempt_id':attempt, 'event_id':event_id,
                  'status':'blocked' if problem else 'planned', 'summary':summary}
        if not problem:
            report['plan']=proposal
            output = store.root / identity / ('plan-' + attempt + '.md')
            output.write_text(proposal + '\n')
            report['plan_file'] = str(output)
            print(proposal, flush=True)
        for task in ledger['tasks'].values():
            task.pop('plan', None)
            if not problem: task['plan']=proposal
            task.update(state='blocked' if problem else 'review', summary=summary, agent='main', updated=now)
        ledger['deliveries'][attempt]['state']='blocked' if problem else 'planned'
        ledger['events'][event_id]={'report':report,'role':'worker','delivery':'pending','received':now}
        store.save(ledger); notify(store, ledger)
    return 1 if problem else 0


def reconcile(ledger):
    """A dead planning wrapper is a blocker, never a completed or restarted task."""
    import uuid
    from .mission_broker import process
    from .mission_native import boot_id
    part = ledger.get('participants', {}).get('worker', {})
    attempt = part.get('startup_attempt')
    record = ledger.get('deliveries', {}).get(attempt, {})
    state = record.get('state')
    if state not in ('sending', 'running'): return
    if state == 'sending' and time.time() - record.get('created', 0) < 60: return
    if state == 'running':
        try:
            if (record.get('wrapper_boot') == boot_id() and
                    process(record['wrapper_pid'])[1] == record.get('wrapper_started')):
                return
        except (OSError, RuntimeError, KeyError): pass
    summary = 'Planejador interrompido; evidências preservadas. Inspecione antes de abrir outra tentativa.'
    record.update(state='blocked', problem=summary)
    part['available'] = False
    for task in ledger['tasks'].values():
        task.update(state='blocked', summary=summary, agent='main', updated=time.time())
    event_id = str(uuid.uuid4())
    ledger['events'][event_id] = {'role':'worker', 'received':time.time(), 'delivery':'pending',
        'report':{'run_id':ledger['id'], 'attempt_id':attempt, 'event_id':event_id,
                  'status':'blocked', 'summary':summary}}
