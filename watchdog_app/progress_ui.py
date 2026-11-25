"""Live run progress and independent project TODO counts."""
import curses
from datetime import datetime
from pathlib import Path
import textwrap

from . import long_run
from .mission import RunStore, task_view, run_status, close, FINISHED
from .mission_scope import explain
from .mission_launch import open_run
from .tasks_ui import put, safe
from .todo import Snapshot
from .session_progress import Progress
from .actions import Session
from .clean_sessions_ui import Controller


def session_rows(view, width=80):
    labels={'ready':('Ready','ready'), 'working':('Working','working'),
            'done':('Done','done'), 'no_checklist':('No checklist','unavailable'),
            'catching_up':('Catching up','review'), 'unsupported':('Unsupported','unavailable'),
            'unavailable':('Unavailable','unavailable')}
    label,color=labels[view.state]
    result=[('SESSION · '+label,color,None)]
    if view.total is not None:
        size=max(4,min(28,width-20))
        filled=size*view.done//view.total
        result.append(('['+'#'*filled+'-'*(size-filled)+f'] {view.done}/{view.total} complete',color,None))
        if view.current:result.append(('Current: '+view.current,color,None))
    elif view.detail:
        result.append((view.detail,color,None))
    result.append(('',None,None))
    return result


def run_rows(repo, store):
    result=[]
    finished=0
    for run in (store or RunStore()).list(repo):
        status=run_status(run)
        if status['finished']:
            finished+=1
            if finished<=3:
                result.append(('RUN '+run['id'][:8]+' · '+status['label']+(' · '+status['detail'] if status['detail'] else ''),status['color'],run))
            continue
        result.append(('RUN '+run['id'][:8]+' · '+status['label'].upper()+' · '+status['detail'],status['color'],run))
        from .mission_single import is_single
        if is_single(run):
            actor = run.get('executor', {}).get('binding') or run.get('participants', {}).get('worker', {}).get('native', {})
            result.append(('Para um agente · Revisão do líder · ' + actor.get('pane', run.get('resources', {}).get('worker', {}).get('pane_id', 'painel indisponível')), None, run))
        if run.get('reason') and run['phase']=='blocked':result.append((run['reason'],'blocked',run))
        if run.get('monitor_problem'):result.append(('Monitor: '+explain(run['monitor_problem']),'blocked',run))
        current={t.get('attempt_id') for t in run['tasks'].values()}|{t.get('gossip_task') for t in run['tasks'].values()}|{run.get('qa_task')}
        for key,message in run.get('report_errors',{}).items():
            if key in current:result.append(('Report needs attention: '+message,'blocked',run))
        for wake in run.get('wakes',{}).values():
            if wake['delivery']!='queued':
                result.append(('Agent notification '+wake['delivery']+' · '+wake['role']+
                    ': inspect the exact conversation queue before retrying. '+wake.get('problem',''),'blocked',run))
        if run.get('transport',{}).get('kind')=='native':
            for delivery in run.get('deliveries',{}).values():
                if delivery['state']=='uncertain':
                    result.append(('Native delivery uncertain · '+delivery['role']+
                        ': inspect the exact thread queue before recovery. '+delivery.get('problem',''),'blocked',run))
        history=0
        for event in (run.get('events') or {}).values():
            if event.get('rejected') or event['delivery']=='history':history+=1;continue
            if event['delivery']!='sent':
                result.append(('Main notification '+event['delivery']+' · '+
                    event.get('notification_problem','Evidence is retained in the run ledger'),
                    'blocked' if event['delivery']=='uncertain' else 'working',run))
        if history:result.append((f'{history} late or superseded report(s) kept in history',None,run))
        for key in run['tasks']:
            task=task_view(run,key)
            result.append((task['label']+' · '+task['title'],task['color'],run))
            stamp=datetime.fromtimestamp(task['updated']).strftime('%m-%d %H:%M:%S')
            result.append((task['agent']+' · '+stamp+' · '+task['summary'],task['color'],run))
        for role,part in run.get('participants',{}).items():
            result.append((role+' · '+part.get('model','Model unavailable')+' · '+
                           part.get('effort','Effort unavailable'),None,run))
            if part.get('problem'):result.append((role+': '+part['problem'],'blocked',run))
        result.append((('Enter: abrir painel do executor · x: fechar execução' if run.get('resources', {}).get('worker') else 'x: fechar execução') if is_single(run) else
                       ('Enter: open execution tab · x: close run' if run.get('tab') else 'x: close run'),None,run))
        result.append(('',None,None))
    if finished>3:result.append((f'{finished-3} older finished run(s) hidden',None,None))
    if finished:result.append(('',None,None))
    if not any(run and not run_status(run)['finished'] for _,_,run in result):result.extend([('No active runs. Select tasks and choose Orchestrate.',None,None),('',None,None)])
    return result


def progress_bar(done, total, width):
    # Leave room for brackets, the percentage and the panel's right margin.
    size = max(1, min(28, width - 9))
    filled = size * done // total if total else 0
    return '[' + '█' * filled + '░' * (size - filled) + ']'


def rows(repo, store=None, *, progress=None, width=80):
    result, history_rows = [], []
    try:
        snapshot = Snapshot.read(repo)
        done = sum(task.done for task in snapshot.tasks)
        total = len(snapshot.tasks)
        count_label = 'concluída' if total == 1 else 'concluídas'
        title = f'Projeto · {done} de {total} {count_label}' if total else 'Projeto · nenhuma tarefa'
        percentage = f' {done / total:.0%}' if total else ''
        project = [(title, 'ready', None), (progress_bar(done, total, width) + percentage, 'done', None)]
        group = long_run.load(repo)
        if group:
            tasks = long_run.members(snapshot, group)
            total = len(group)
            done = sum(1 for task in tasks if task and task.done)
            remaining = total - done
            label = 'falta' if remaining == 1 else 'faltam'
            heading = [('Long run', 'ready', None),
                       (f'{done} de {total} concluídas · {done / total:.0%} · {label} {remaining}', 'done', None),
                       (progress_bar(done, total, width), 'done', None)]
            missing = tasks.count(None)
            if missing:
                heading.append((f'{missing} sem correspondência única no TODO.md', 'blocked', None))
            result.extend(heading + [('', None, None)])
        result.extend(project + [('', None, None)])
        if not group:
            result.extend([('Long run · selecione tarefas em Tasks e use Acompanhar no Progress (g).', None, None),
                           ('', None, None)])
        if snapshot.format_version == 1:
            from .project_history import observe
            history = observe(snapshot)
            history_rows.append(('PROJECT HISTORY · observed transitions (TODO is authoritative)',None,None))
            for event in history['events'][-12:]:
                history_rows.append((event['observed_at']+' · '+event['id'][:8]+' · '+
                               event['from']+' → '+event['to']+' · '+event['evidence'],None,None))
    except (OSError, RuntimeError, ValueError) as error:
        result.append(('PROJECT · '+str(error),'blocked',None))
    result.extend(session_rows((progress or Progress(repo)).poll(), width))
    try:
        result.extend(run_rows(repo, store))
    except (RuntimeError, OSError, ValueError, KeyError, TypeError) as error:
        result.append(('Cannot read runs: ' + str(error), 'blocked', None))
    result.extend(history_rows)
    return result


def panel(screen, repo, binding_file=None):
    try:curses.curs_set(0)
    except curses.error:pass
    screen.keypad(True);screen.timeout(1000);curses.mousemask(curses.ALL_MOUSE_EVENTS)
    palette={}
    try:
        if curses.has_colors():
            curses.start_color()
            try:curses.use_default_colors();bg=-1
            except curses.error:bg=curses.COLOR_BLACK
            for i,(name,color) in enumerate((('ready',12),('working',11),('blocked',9),('review',13),('done',10),('unavailable',7)),1):
                curses.init_pair(i,color if curses.COLORS>=16 else color%8,bg);palette[name]=curses.color_pair(i)
    except curses.error:pass
    selected=offset=0;notice='';armed=None
    progress=Progress(repo,binding_file)
    clean=Controller(repo)
    while True:
        screen.erase();h,w=screen.getmaxyx()
        put(screen,0,'WATCHDOG / PROGRESS',curses.A_BOLD);put(screen,1,Path(repo).name)
        try:
            if binding_file:
                session=Session.for_panel(binding_file,Path(repo))
                if session.file!=Path(binding_file):
                    binding_file=session.file;progress=Progress(repo,binding_file)
                clean.poll(session.binding)
            cleanup_rows = [(text, 'blocked' if color == 'Blocked' else 'working', None)
                            for text, color, _ in clean.rows()]
        except (RuntimeError, OSError, ValueError, KeyError, TypeError) as error:
            cleanup_rows = [('Session · ' + str(error), 'blocked', None)]
        source = rows(repo, progress=progress, width=w) + cleanup_rows
        rendered=[]
        for text,color,run in source:
            rendered.extend((part,color,run) for part in textwrap.wrap(safe(text),max(4,w-2)) or [''])
        selected=min(selected,max(0,len(rendered)-1));page=max(1,h-5)
        offset=min(offset,selected)
        if selected>=offset+page:offset=selected-page+1
        for i,(text,color,_) in enumerate(rendered[offset:offset+page],offset):
            put(screen,i-offset+3,text,palette.get(color,0)|(curses.A_REVERSE if i==selected else 0))
        put(screen,h-1,notice or 'j/k: scroll · Enter/click: execution tab · x: close run · q: exit',curses.A_DIM)
        screen.refresh();key=screen.getch()
        if key!=-1 and key!=ord('x'):notice=''
        if key in (ord('q'),27):return
        if key in (ord('j'),curses.KEY_DOWN):selected+=1
        elif key in (ord('k'),curses.KEY_UP):selected=max(0,selected-1)
        elif key==curses.KEY_NPAGE:selected+=page
        elif key==curses.KEY_PPAGE:selected=max(0,selected-page)
        elif key==curses.KEY_MOUSE:
            try:
                _,_,y,_,mask=curses.getmouse()
                if 3<=y<h-2:
                    selected=min(len(rendered)-1,max(0,offset+y-3))
                    if mask&(curses.BUTTON1_CLICKED|curses.BUTTON1_DOUBLE_CLICKED):key=10
            except curses.error:pass
        if key==ord('x') and rendered:
            run=rendered[min(selected,len(rendered)-1)][2]
            if not run or run['phase'] in FINISHED:notice='Select an unfinished run to close'
            elif armed==run['id']:
                try:close(RunStore(),run['id'],'closed by the user in Progress');notice='Run '+run['id'][:8]+' closed; evidence kept'
                except (RuntimeError,OSError,ValueError,KeyError) as error:notice=str(error)
                armed=None
            else:
                armed=run['id'];notice='Press x again to close run '+run['id'][:8]+' (agents are not stopped; evidence is kept)'
            continue
        if key!=-1:armed=None
        if key in (10,13,curses.KEY_ENTER) and rendered:
            run=rendered[min(selected,len(rendered)-1)][2]
            if run:
                try:open_run(run)
                except (RuntimeError,OSError,ValueError,KeyError) as error:notice=str(error)


def run(repo, binding_file=None):
    curses.wrapper(panel,Path(repo).resolve(),binding_file)
