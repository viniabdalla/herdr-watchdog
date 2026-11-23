"""Transcript usage readers and meter ported from Left Undone's agents.py.

Kept locally so Watchdog does not import Left Undone's monitor or database.
"""
import json

CLAUDE_WINDOW = 200_000
CLAUDE_LARGE_WINDOW = 1_000_000


def decimal(text):
    return text.replace('.', ',')


def tr(text):
    return {'Context': 'Contexto', 'No data': 'Sem dados',
            '{0} / {1} context used': '{0} / {1} de contexto usado',
            '{0} total': '{0} no total'}.get(text, text)


def read_usage(path, cache):
    """Consume complete transcript records once, including across log rotation."""
    stat = path.stat()
    identity = (stat.st_dev, stat.st_ino)
    previous, offset, context, window, total = cache.get(path, (None, 0, None, None, None))
    if identity != previous or stat.st_size < offset:
        offset, context, window, total = 0, None, None, None
    with path.open('rb') as stream:
        stream.seek(offset)
        for line in stream:
            if not line.endswith(b'\n'):
                break
            offset += len(line)
            if b'"token_count"' not in line:
                continue
            payload = json.loads(line).get('payload', {})
            if payload.get('type') != 'token_count':
                continue
            info = payload.get('info') or {}
            context = (info.get('last_token_usage') or {}).get('total_tokens', context)
            window = info.get('model_context_window', window)
            total = (info.get('total_token_usage') or {}).get('total_tokens', total)
    cache[path] = identity, offset, context, window, total
    return context, window, total


def abbreviate(number):
    """950 -> 950, 12400 -> 12.4k, 254160 -> 254k, 23114025 -> 23.1M."""
    for size, unit in ((1_000_000, 'M'), (1_000, 'k')):
        if number >= size:
            value = number / size
            text = f'{value:.1f}'.rstrip('0').rstrip('.') if value < 100 else str(round(value))
            return decimal(text) + unit
    return str(number)


def claude_window(context, model, override=None):
    if override:
        return override
    if (context or 0) > CLAUDE_WINDOW or '1m' in (model or '').lower():
        return CLAUDE_LARGE_WINDOW
    return CLAUDE_WINDOW


def claude_usage(path, cache, session):
    """(current context, cumulative total, model) of a Claude session."""
    stat = path.stat()
    identity = (stat.st_dev, stat.st_ino)
    previous, offset, messages, total, context, model = cache.get(path, (None, 0, {}, 0, None, None))
    if previous != identity or stat.st_size < offset:
        offset, messages, total, context, model = 0, {}, 0, None, None
    with path.open('rb') as stream:
        stream.seek(offset)
        for line in stream:
            if not line.endswith(b'\n'):
                break
            offset += len(line)
            if b'"usage"' not in line:
                continue
            row = json.loads(line)
            if row.get('type') != 'assistant' or row.get('sessionId') != session or row.get('isSidechain'):
                continue
            message = row.get('message', {})
            mid, usage = message.get('id'), message.get('usage') or {}
            if not mid or 'input_tokens' not in usage or 'output_tokens' not in usage:
                continue
            count = sum(usage.get(k,0) or 0 for k in ('input_tokens','output_tokens',
                        'cache_creation_input_tokens','cache_read_input_tokens'))
            total += count - messages.get(mid,0)
            messages[mid] = count
            context = count - (usage.get('output_tokens',0) or 0)
            model = message.get('model') or model
    cache[path] = identity, offset, messages, total, context, model
    return (context, total, model) if messages else (None, None, None)


def usage_meter(usage):
    """'254k / 1M context used · ▰▰▰▱▱▱▱▱▱▱ 25% · 23.1M total'."""
    if not usage:
        return tr('Context')+' · '+tr('No data')
    parts = []
    context, window = usage.get('context'), usage.get('window')
    if context is not None and window:
        share = min(1, context/window)
        percent = 100*share
        label = '<1' if 0 < percent < 1 else str(round(percent))
        filled = min(10, round(10*share))
        parts.append(tr('{0} / {1} context used').format(abbreviate(context), abbreviate(window)))
        parts.append('▰'*filled+'▱'*(10-filled)+' '+label+'%')
    if usage.get('total') is not None:
        parts.append(tr('{0} total').format(abbreviate(usage['total'])))
    return ' · '.join(parts) or tr('Context')+' · '+tr('No data')
