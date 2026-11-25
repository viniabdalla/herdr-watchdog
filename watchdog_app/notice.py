"""Executor ready/blocker notices using the same pane lease as Tasks."""
import argparse
import sys

from .herdr import Herdr
from .pane_delivery import DeliveryPending, send


def nonempty(value):
    if not value.strip():
        raise argparse.ArgumentTypeError('Informe um valor não vazio')
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(description='Avisar o líder com trava até o Enter')
    parser.add_argument('--lider', required=True, type=nonempty)
    parser.add_argument('--pane', required=True, type=nonempty, help='Pane próprio do executor')
    parser.add_argument('--ticket', required=True, type=nonempty)
    parser.add_argument('--session', help='Sessão Herdr, quando explícita no painel')
    events = parser.add_subparsers(dest='event', required=True)
    ready = events.add_parser('pronto')
    ready.add_argument('--commit', required=True, type=nonempty)
    ready.add_argument('--testes', required=True, type=nonempty)
    ready.add_argument('--resumo', required=True, type=nonempty)
    blocker = events.add_parser('BLOQUEIO')
    blocker.add_argument('--duvida', required=True, type=nonempty)
    args = parser.parse_args(argv)
    prefix = f'[{args.ticket} · painel {args.pane}] '
    if args.event == 'pronto':
        text = prefix + f'{args.ticket} pronto: commit {args.commit}, testes {args.testes}. {args.resumo}'
    else:
        text = prefix + 'BLOQUEIO: ' + args.duvida
    try:
        send(args.lider, text, api=Herdr(args.session))
    except DeliveryPending as error:
        print(str(error)+'; não reenvie o aviso.', file=sys.stderr)
        return 2
    except (RuntimeError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0
