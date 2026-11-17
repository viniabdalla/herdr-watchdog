"""Live run progress and independent project TODO counts."""
import curses
from datetime import datetime
from pathlib import Path
import textwrap

from .mission import RunStore, task_view
from .mission_launch import open_run
from .tasks_ui import put, safe
from .todo import Snapshot
from .session_progress import Progress


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


def rows(repo, store=None, *, progress=None, width=80):
    result=session_rows((progress or Progress(repo)).poll(), width)
    for run in (store or RunStore()).list(repo):
        result.append(('RUN '+run['id'][:8]+' · '+{'requested':'Preparing the brief','launching':'Opening the team','active':'Team is running','blocked':'Needs help','done':'Done'}.get(run['phase'],'Unavailable'),None,run))
        if run.get('reason'):result.append((run['reason'],'blocked',run))
        if run.get('monitor_problem'):result.append(('Monitoring unavailable: '+run['monitor_problem'],'blocked',run))
        for message in run.get('report_errors',{}).values():
            result.append(('Report needs attention: '+message,'blocked',run))
        for wake in run.get('wakes',{}).values():
            if wake['delivery']!='queued':
                result.append(('Agent notification '+wake['delivery']+' · '+wake['role']+
                    ': inspect the exact conversation queue before retrying. '+wake.get('problem',''),'blocked',run))
        if run.get('transport',{}).get('kind')=='native':
            for delivery in run.get('deliveries',{}).values():
                if delivery['state']=='uncertain':
                    result.append(('Native delivery uncertain · '+delivery['role']+
                        ': inspect the exact thread queue before recovery. '+delivery.get('problem',''),'blocked',run))
            for event in run['events'].values():
                if event['delivery']!='sent':
                    result.append(('Main notification '+event['delivery']+' · '+
                        event.get('notification_problem','Evidence is retained in the run ledger'),
                        'blocked' if event['delivery']=='uncertain' else 'working',run))
        for key in run['tasks']:
            task=task_view(run,key)
            result.append((task['label']+' · '+task['title'],task['color'],run))
            stamp=datetime.fromtimestamp(task['updated']).strftime('%m-%d %H:%M:%S')
            result.append((task['agent']+' · '+stamp,task['color'],run))
            result.append((task['summary'],task['color'],run))
        for role,part in run.get('participants',{}).items():
            result.append((role+' · '+part.get('model','Model unavailable')+' · '+
                           part.get('effort','Effort unavailable'),None,run))
            if part.get('problem'):result.append((role+': '+part['problem'],'blocked',run))
        result.append(('Enter: open execution tab' if run.get('tab') else 'Waiting for execution tab',None,run))
        result.append(('',None,None))
    if not any(run for _,_,run in result):result.extend([('No active runs. Select tasks and choose Orchestrate.',None,None),('',None,None)])
    try:
        snapshot=Snapshot.read(repo)
        done=sum(t.done for t in snapshot.tasks)
        result.extend([('PROJECT · TODO.md',None,None),(f'{done}/{len(snapshot.tasks)} tasks complete',None,None),
            ('Dispatch and run approval do not change project TODO.',None,None)])
    except (OSError,RuntimeError,UnicodeError) as error:
        result.append(('PROJECT · '+str(error),'blocked',None))
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
    selected=offset=0;notice=''
    progress=Progress(repo,binding_file)
    while True:
        screen.erase();h,w=screen.getmaxyx()
        put(screen,0,'WATCHDOG / PROGRESS',curses.A_BOLD);put(screen,1,Path(repo).name)
        try:source=rows(repo,progress=progress,width=w)
        except (OSError,ValueError,KeyError,TypeError) as error:source=[('Cannot read runs: '+str(error),'blocked',None)]
        rendered=[]
        for text,color,run in source:
            rendered.extend((part,color,run) for part in textwrap.wrap(safe(text),max(4,w-2)) or [''])
        selected=min(selected,max(0,len(rendered)-1));page=max(1,h-5)
        offset=min(offset,selected)
        if selected>=offset+page:offset=selected-page+1
        for i,(text,color,_) in enumerate(rendered[offset:offset+page],offset):
            put(screen,i-offset+3,text,palette.get(color,0)|(curses.A_REVERSE if i==selected else 0))
        put(screen,h-1,notice or 'j/k: scroll · Enter/click: execution tab · q: exit',curses.A_DIM)
        screen.refresh();key=screen.getch();notice=''
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
        if key in (10,13,curses.KEY_ENTER) and rendered:
            run=rendered[min(selected,len(rendered)-1)][2]
            if run:
                try:open_run(run)
                except (RuntimeError,OSError,ValueError,KeyError) as error:notice=str(error)


def run(repo, binding_file=None):
    curses.wrapper(panel,Path(repo).resolve(),binding_file)
