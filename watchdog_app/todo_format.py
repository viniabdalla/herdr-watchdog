"""Versioned, deliberately small Markdown grammar; no YAML or model inference."""
import json
import re
import uuid


FIELDS = {'ID': 'id', 'Resumo': 'summary', 'Origem': 'origin',
          'Referência': 'reference', 'Execução': 'execution', 'Aceite': 'acceptance',
          'Motivo': 'reason'}
REQUIRED = ('id', 'summary', 'origin', 'execution', 'acceptance')
ORIGINS = ('pedido-humano', 'sugestao-agente', 'legado-nao-confirmado')
HISTORY_BEGIN = '<!-- watchdog-history:begin -->'
HISTORY_END = '<!-- watchdog-history:end -->'
MIGRATION_PREFIX = '<!-- watchdog-migration: '


def error(line, message):
    raise RuntimeError(f'TODO linha {line}: {message}')


def canonical_id(value):
    try:
        return isinstance(value, str) and str(uuid.UUID(value)) == value
    except (ValueError, AttributeError):
        return False


def version(lines):
    if not lines or lines[0].strip() != '---':
        return 0
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == '---'), None)
    entries = [(i, line.split(':', 1)[1].strip()) for i, line in enumerate(lines[1:end], 2)
               if re.match(r'^watchdog_todo\s*:', line)]
    if not entries:
        return 0
    if end is None or len(entries) != 1 or entries[0][1] != '1':
        error(entries[0][0], 'versão de formato watchdog_todo inválida ou não suportada')
    return 1


def fields(lines, start, end):
    values, current = {}, None
    for i in range(start + 1, end):
        line = lines[i].rstrip('\r\n')
        if not line.strip():
            if current:
                values[current] += '\n'
            continue
        match = re.fullmatch(r'  ([^ :][^:]*):(?: (.*))?', line)
        if match:
            name = FIELDS.get(match[1])
            if name is None:
                error(i + 1, 'campo desconhecido: ' + match[1])
            if name in values:
                error(i + 1, 'campo repetido: ' + match[1])
            values[name] = match[2] or ''
            current = name
        elif line.startswith('    ') and current in ('summary', 'execution', 'acceptance'):
            values[current] += ('\n' if values[current] else '') + line[4:]
        else:
            error(i + 1, 'recuo ou campo inválido')
    values = {key: value.strip() for key, value in values.items()}
    for key in REQUIRED:
        if not values.get(key):
            error(start + 1, 'campo obrigatório ausente: ' + next(k for k, v in FIELDS.items() if v == key))
    if not canonical_id(values['id']):
        error(start + 1, 'ID deve ser UUID canônico')
    if values['origin'] not in ORIGINS:
        error(start + 1, 'Origem inválida')
    return values


def render(title, values, *, done=False, newline='\n'):
    lines = [('- [x] ' if done else '- [ ] ') + title]
    for label, name in FIELDS.items():
        value = values.get(name, '')
        if not value:
            continue
        if name in ('summary', 'execution', 'acceptance'):
            parts = value.splitlines()
            lines.append('  ' + label + ':')
            lines.extend('    ' + part if part else '' for part in parts)
        else:
            if '\n' in value or '\r' in value:
                raise RuntimeError('TODO: campo deve ter uma linha: ' + label)
            lines.append('  ' + label + ': ' + value)
    return newline.join(lines) + newline


def migration_record(line, number):
    try:
        value = json.loads(line[len(MIGRATION_PREFIX):-4])
    except (ValueError, TypeError):
        error(number, 'metadados de migração inválidos')
    if (not isinstance(value, dict) or set(value) != {'version', 'kind', 'source_digest', 'ids'}
            or value['version'] != 1 or type(value['version']) is not int
            or value['kind'] not in ('legacy', 'identity')
            or not isinstance(value['source_digest'], str)
            or not re.fullmatch('[0-9a-f]{64}', value['source_digest'])
            or not isinstance(value['ids'], dict)
            or any(not canonical_id(new) for new in value['ids'].values())
            or len(set(value['ids'].values())) != len(value['ids'])
            or any(not (canonical_id(old) if value['kind'] == 'identity'
                        else re.fullmatch('[0-9a-f]{64}', old)) for old in value['ids'])):
        error(number, 'esquema dos metadados de migração inválido')
    if value['kind'] == 'identity' and any(old == new for old, new in value['ids'].items()):
        error(number, 'mudança de identidade deve ter ID diferente')
    return value
