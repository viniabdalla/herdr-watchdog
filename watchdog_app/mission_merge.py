"""Integrate an approved run into the project branch, so nobody reviews worker branches.

Approval = QA passed for the exact candidate. Watchdog then merges that candidate
into the branch the project checkout is on (fast-forward when possible), and pushes
it to the branch's upstream. A conflict aborts cleanly and says what to do next.
"""
import os
import subprocess
from pathlib import Path


def git(repo, *args, check=True):
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    result = subprocess.run(['git', '-C', str(repo), *args], capture_output=True, text=True, timeout=60, env=env)
    if check and result.returncode:
        raise RuntimeError((result.stderr or result.stdout).strip() or 'git ' + args[0] + ' failed')
    return result


def out(repo, *args):
    return git(repo, *args).stdout.strip()


def integrate(run, candidate, *, push=True):
    repo = Path(run['repo'])
    branch = git(repo, 'symbolic-ref', '--quiet', '--short', 'HEAD', check=False).stdout.strip()
    if not branch:
        raise RuntimeError('The project checkout is not on a branch; switch to the main branch before approving')
    if git(repo, 'cat-file', '-e', candidate + '^{commit}', check=False).returncode:
        raise RuntimeError('Approved candidate ' + candidate[:8] + ' is not in this repository')
    before = out(repo, 'rev-parse', 'HEAD')
    titles = '\n'.join('- ' + t['title'] for t in run['tasks'].values())
    if git(repo, 'merge-base', '--is-ancestor', candidate, 'HEAD', check=False).returncode == 0:
        how = 'already'
    elif git(repo, 'merge-base', '--is-ancestor', 'HEAD', candidate, check=False).returncode == 0:
        merged = git(repo, 'merge', '--ff-only', candidate, check=False)
        if merged.returncode:
            raise RuntimeError('Could not bring the approved work into ' + branch + ': ' +
                               (merged.stderr or merged.stdout).strip()[-400:])
        how = 'fast-forward'
    else:
        message = 'Merge Watchdog run ' + run['id'][:8] + ' (QA passed ' + candidate[:8] + ')\n\n' + titles
        merged = git(repo, 'merge', '--no-ff', '-m', message, candidate, check=False)
        if merged.returncode:
            conflicts = out(repo, 'diff', '--name-only', '--diff-filter=U').split()
            if git(repo, 'rev-parse', '-q', '--verify', 'MERGE_HEAD', check=False).returncode == 0:
                git(repo, 'merge', '--abort')
            if conflicts:
                raise RuntimeError('Approved work conflicts with ' + branch + ' in: ' + ', '.join(conflicts) +
                                   '. Nothing was merged. Send the worker a followup to rebase onto ' + branch +
                                   ' (' + before[:8] + '), then review and approve the new candidate.')
            raise RuntimeError('Could not merge the approved work into ' + branch + ': ' +
                               (merged.stderr or merged.stdout).strip()[-400:])
        how = 'merge'
    head = out(repo, 'rev-parse', 'HEAD')
    result = {'branch': branch, 'candidate': candidate, 'before': before, 'head': head, 'how': how, 'pushed': False}
    upstream = git(repo, 'rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{u}', check=False).stdout.strip()
    if push and upstream and '/' in upstream:
        remote, target = upstream.split('/', 1)
        sent = git(repo, 'push', remote, 'HEAD:refs/heads/' + target, check=False)
        result.update(remote=remote, target=target, pushed=sent.returncode == 0)
        if sent.returncode:
            result['push_error'] = (sent.stderr or sent.stdout).strip()[-400:]
    elif push:
        result['push_error'] = 'branch has no upstream; merged locally only'
    return result


def summary(result):
    where = result['branch'] + ' (' + result['head'][:8] + ')'
    text = {'already': 'Already in ', 'fast-forward': 'Merged into ', 'merge': 'Merged into '}[result['how']] + where
    if result.get('pushed'):
        text += ' and pushed to ' + result['remote'] + '/' + result['target']
    elif result.get('push_error'):
        text += '; not pushed: ' + result['push_error']
    return text
