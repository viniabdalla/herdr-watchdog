"""Four presets, applied by moving owned terminals rather than replacing trees."""

PRESETS = {
    1: ('Right column', 'conversation     | tasks\n                 | progress\n                 | artifacts\n                 | files'),
    2: ('Column + bottom strip', 'conversation     | tasks\n                 | progress\n-----------------+---------\nartifacts | files'),
    3: ('Separate Watchdog tab', 'TAB 1: conversation\n\nTAB 2:\ntasks     | progress\n----------+---------\nartifacts | files'),
    4: ('Slim column + tab', 'TAB 1:\nconversation | tasks\n             | progress\n\nTAB 2:\nartifacts | files'),
}


def arrange(api, conversation, panes, preset, save=lambda: None):
    if preset not in PRESETS:
        raise RuntimeError('Choose layout 1, 2, 3 or 4')
    if not {'tasks', 'progress', 'artifacts', 'files'} <= panes.keys():
        raise RuntimeError('Watchdog panel set is incomplete')
    ids = [conversation['pane_id']] + [p['pane_id'] for p in panes.values()]
    if len(set(ids)) != len(ids):
        raise RuntimeError('Pane ownership is ambiguous')
    # Preflight every terminal before the first mutation.
    live = api.checked(conversation)
    for pane in panes.values():
        api.checked(pane)
    workspace = live['workspace_id']
    current = api.call('pane', 'list', '--workspace', workspace)['panes']
    unknown = [p for p in current if p['tab_id'] == live['tab_id'] and p['pane_id'] not in ids]
    if unknown:
        result = api.call('pane', 'move', live['pane_id'], '--new-tab', '--workspace',
                          workspace, '--label', 'Watchdog conversation', '--no-focus')['move_result']
        conversation.update(result['pane'])
        live = result['pane']
        save()
    target = live['tab_id']

    def move(name, tab=None, dest=None, direction='right', ratio=.5, new_label=None):
        ref = panes[name]
        api.checked(ref)
        args = ['pane', 'move', ref['pane_id']]
        if new_label:
            args += ['--new-tab', '--workspace', workspace, '--label', new_label]
        else:
            args += ['--tab', tab, '--target-pane', dest, '--split', direction,
                     '--ratio', str(ratio)]
        result = api.call(*args, '--no-focus')['move_result']
        if not result['changed']:
            raise RuntimeError('Herdr did not move the panel; layout stopped without retrying')
        ref.update(result['pane'])
        save()
        return ref['pane_id']

    # Same-tab moves are no-ops in Herdr 0.9.1. Stage the known panels in a
    # temporary owned tab, then rebuild around the unchanged conversation.
    first = next(iter(panes))
    anchor = move(first, new_label='Watchdog staging')
    staging = panes[first]['tab_id']
    for name in panes:
        if name != first:
            move(name, staging, anchor, 'down')

    if preset == 1:
        tasks = move('tasks', target, live['pane_id'], ratio=.64)
        progress = move('progress', target, tasks, 'down', .25)
        artifacts = move('artifacts', target, progress, 'down', 1 / 3)
        move('files', target, artifacts, 'down')
        focus = target
    elif preset == 2:
        files = move('files', target, live['pane_id'], 'down', .68)
        artifacts = move('artifacts', target, files, ratio=.32)
        api.call('pane', 'swap', '--source-pane', files, '--target-pane', artifacts)
        tasks = move('tasks', target, live['pane_id'], ratio=.64)
        move('progress', target, tasks, 'down')
        focus = target
    elif preset == 3:
        tasks = move('tasks', new_label='Watchdog panels')
        dashboard = panes['tasks']['tab_id']
        progress = move('progress', dashboard, tasks)
        move('artifacts', dashboard, tasks, 'down')
        move('files', dashboard, progress, 'down')
        focus = dashboard
    else:
        tasks = move('tasks', target, live['pane_id'], ratio=.7)
        move('progress', target, tasks, 'down')
        artifacts = move('artifacts', new_label='Watchdog files')
        focus = target
        move('files', panes['artifacts']['tab_id'], artifacts, ratio=.4)
    if 'agents' in panes:
        tasks = panes['tasks']
        move('agents', tasks['tab_id'], panes['progress']['pane_id'], 'down')
    if 'left_undone' in panes:
        files = panes['files']
        move('left_undone', files['tab_id'], files['pane_id'], ratio=.62)
    for pane in panes.values():
        api.checked(pane)
    api.call('tab', 'focus', focus)
    return focus
