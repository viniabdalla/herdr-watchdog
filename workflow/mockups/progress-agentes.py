"""Mockup do Progress com monitor de agentes. Teclas 1/2/3 trocam o momento; q sai."""
import curses

def bar(done, total, width):
    size = max(10, min(40, width - 12))
    filled = round(size * done / total) if total else 0
    return '[' + '█' * filled + '░' * (size - filled) + ']'

def meter(used, window):
    share = min(1, used / window)
    filled = round(10 * share)
    return f'{used}k/{window}k ' + '▰' * filled + '▱' * (10 - filled) + f' {round(100*share):>2}%'

SCENES = {
    '1': ('Durante a meta', 1, [
        ('Líder', 'wZ:pG', 'Working', 'working', (96, 200), 'esperando avisos (sem polling)'),
        ('A', 'wZ:pJ', 'Idle', 'done', (61, 272), 'concluída · commit eea4c91 · 689 testes'),
        ('B', 'wZ:pK', 'Working', 'working', (18, 272), 'checagem inicial 2/3 · rumo ok'),
        ('C', '—', 'Bloqueada', 'blocked', None, 'depende de você · fica para o aviso final'),
    ], None),
    '2': ('Pergunta imediata (D8)', 1, [
        ('Líder', 'wZ:pG', 'Idle', 'review', (104, 200), 'pergunta para você no pane do líder'),
        ('A', 'wZ:pJ', 'Idle', 'done', (61, 272), 'concluída · commit eea4c91 · 689 testes'),
        ('B', 'wZ:pK', 'Blocked', 'blocked', (44, 272), 'BLOQUEIO: integrar pelo interpretador? spec não decide'),
        ('C', '—', 'Bloqueada', 'blocked', None, 'depende de você'),
    ], ('? Pergunta de B aguarda você · veja o pane wZ:pG', 'review')),
    '3': ('Meta encerrada (D10)', 2, [
        ('Líder', 'wZ:pG', 'Idle', 'done', (131, 200), 'aviso final entregue'),
        ('A', 'wZ:pJ', 'Idle', 'done', (61, 272), 'concluída · commit eea4c91 · 689 testes'),
        ('B', 'wZ:pK', 'Idle', 'done', (88, 272), 'concluída · commit 7b1e0d2 · 702 testes'),
        ('C', '—', 'Bloqueada', 'blocked', None, 'depende de você: liberar token · próximo: rodar T14'),
    ], ('■ Meta encerrada · 2 de 3 · C depende de você', 'blocked')),
}

def put(s, y, x, text, attr=0):
    h, w = s.getmaxyx()
    if 0 <= y < h - 0 and x < w:
        try: s.addnstr(y, x, text, w - x - 1, attr)
        except curses.error: pass

def main(s):
    curses.curs_set(0); curses.start_color(); curses.use_default_colors()
    pal = {}
    for i, (n, c) in enumerate((('ready', 12), ('working', 11), ('blocked', 9), ('review', 13), ('done', 10), ('dim', 8)), 1):
        curses.init_pair(i, c, -1); pal[n] = curses.color_pair(i)
    key = '1'
    while True:
        title, done, agents, banner = SCENES[key]
        s.erase(); h, w = s.getmaxyx()
        put(s, 0, 0, 'WATCHDOG / PROGRESS', curses.A_BOLD)
        put(s, 1, 0, 'tropicdesk-kommoclone' + f'   [mockup: {title}]', pal['dim'])
        y = 3
        put(s, y, 0, 'Meta da seleção', pal['ready']); y += 1
        put(s, y, 0, f'{done} de 3 concluídas · {done/3:.0%} · faltam {3-done}', pal['done']); y += 1
        put(s, y, 0, bar(done, 3, w), pal['done']); y += 2
        put(s, y, 0, f'Projeto · {11+done} de 30 concluídas', pal['ready']); y += 1
        put(s, y, 0, bar(11 + done, 30, w) + f' {(11+done)/30:.0%}', pal['done']); y += 2
        if banner:
            put(s, y, 0, banner[0], pal[banner[1]] | curses.A_BOLD | curses.A_REVERSE); y += 2
        put(s, y, 0, 'AGENTES', curses.A_BOLD); y += 1
        for name, pane, state, color, use, note in agents:
            put(s, y, 0, f'{name:<6}{pane:<7}', 0)
            put(s, y, 13, f'{state:<10}', pal[color])
            put(s, y, 24, meter(*use) if use else '—', pal['dim'] if not use else 0)
            y += 1
            put(s, y, 6, note, pal['dim'] if color != 'blocked' else pal['blocked']); y += 1
        put(s, h - 1, 0, 'mockup · 1 durante · 2 pergunta · 3 encerrada · q sair', pal['dim'])
        s.refresh()
        k = s.getch()
        if k in (ord('q'), 27): return
        if chr(k) in SCENES if 0 <= k < 256 else False: key = chr(k)

curses.wrapper(main)
