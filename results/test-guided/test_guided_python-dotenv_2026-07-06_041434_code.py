# cli.py
"""Command-line interface for python-dotenv."""

import os
import sys
import subprocess
import shlex
from typing import Dict, List, Optional

import click

from .main import dotenv_values, set_key, unset_key
from .version import __version__


def enumerate_env() -> str:
    """Return the path to the .env file by searching up the directory tree."""
    path = os.getcwd()
    while True:
        check_path = os.path.join(path, '.env')
        if os.path.isfile(check_path):
            return check_path
        parent = os.path.dirname(path)
        if parent == path:
            break
        path = parent
    return os.path.join(os.getcwd(), '.env')


def stream_file(path: str) -> str:
    """Read and return the content of a file."""
    with open(path, 'r') as f:
        return f.read()


@click.group()
@click.option('-f', '--file', default=None,
              type=click.Path(exists=False),
              help='Location of the .env file.')
@click.option('-q', '--quote', default='always',
              type=click.Choice(['always', 'never', 'auto']),
              help='Whether to quote values.')
@click.option('-e', '--export', default=True,
              type=bool,
              help='Whether to write export in front of the key.')
@click.version_option(version=__version__)
@click.pass_context
def cli(ctx: click.Context, file: Optional[str], quote: str, export: bool) -> None:
    """A CLI interface for python-dotenv."""
    ctx.ensure_object(dict)
    ctx.obj['FILE'] = file or enumerate_env()
    ctx.obj['QUOTE'] = quote
    ctx.obj['EXPORT'] = export


@cli.command()
@click.option('--format', 'list_format', default='simple',
              type=click.Choice(['simple', 'json', 'shell', 'export']),
              help='Output format.')
@click.pass_context
def list_values(ctx: click.Context, list_format: str) -> None:
    """Display all the stored key/value pairs."""
    file = ctx.obj['FILE']
    if not os.path.isfile(file):
        click.echo("Error: Path '{}' does not exist.".format(file), err=True)
        ctx.exit(1)
        return

    values = dotenv_values(file)

    if list_format == 'json':
        import json
        click.echo(json.dumps(values, indent=2))
    elif list_format == 'shell':
        for k, v in values.items():
            click.echo("{}={}".format(k, shlex.quote(v or '')))
    elif list_format == 'export':
        for k, v in values.items():
            click.echo("export {}={}".format(k, shlex.quote(v or '')))
    else:
        for k, v in values.items():
            click.echo("{}={}".format(k, v))


@cli.command('set')
@click.argument('key')
@click.argument('value')
@click.pass_context
def set_value(ctx: click.Context, key: str, value: str) -> None:
    """Store the given key/value pair."""
    file = ctx.obj['FILE']
    quote = ctx.obj['QUOTE']
    export = ctx.obj['EXPORT']

    success, key, value = set_key(file, key, value, quote=quote, export=export)
    if success:
        click.echo("{}={}".format(key, value))
    else:
        click.echo("Error: could not set value.", err=True)
        ctx.exit(1)


@cli.command()
@click.argument('key')
@click.pass_context
def get(ctx: click.Context, key: str) -> None:
    """Retrieve the value for the given key."""
    file = ctx.obj['FILE']

    if not os.path.isfile(file):
        click.echo("Error: Path '{}' does not exist.".format(file), err=True)
        ctx.exit(1)
        return

    values = dotenv_values(file)
    stored_value = values.get(key)

    if stored_value is not None:
        click.echo(stored_value)
    else:
        click.echo("Error: key '{}' not found.".format(key), err=True)
        ctx.exit(1)


@cli.command()
@click.argument('key')
@click.pass_context
def unset(ctx: click.Context, key: str) -> None:
    """Remove the given key."""
    file = ctx.obj['FILE']
    quote = ctx.obj['QUOTE']

    success, key = unset_key(file, key, quote=quote)
    if success:
        click.echo("Successfully removed {}".format(key))
    else:
        click.echo("Error: could not unset key.", err=True)
        ctx.exit(1)


@cli.command(context_settings={'ignore_unknown_options': True, 'allow_extra_args': True})
@click.option('--override/--no-override', default=True,
              help='Whether to override existing environment variables.')
@click.argument('commandline', nargs=-1, type=click.UNPROCESSED)
@click.pass_context
def run(ctx: click.Context, override: bool, commandline: List[str]) -> None:
    """Run a command with the environment variables from the .env file."""
    file = ctx.obj['FILE']

    if not commandline:
        click.echo("Error: no command given.", err=True)
        ctx.exit(1)
        return

    if not os.path.isfile(file):
        click.echo("Error: Path '{}' does not exist.".format(file), err=True)
        ctx.exit(1)
        return

    ret = run_command(commandline, file, override=override)
    ctx.exit(ret)


def run_command(command: List[str], file: str, override: bool = True) -> int:
    """Run a command with the environment variables loaded from a .env file."""
    values = dotenv_values(file)

    env = os.environ.copy()
    for key, value in values.items():
        if value is not None:
            if override or key not in env:
                env[key] = value

    try:
        ret = subprocess.call(
            command,
            env=env,
        )
        return ret
    except FileNotFoundError:
        click.echo("Error: command '{}' not found.".format(command[0]), err=True)
        return 1
    except KeyboardInterrupt:
        return 1


if __name__ == '__main__':
    cli()

# ipython.py
from IPython.core.magic import Magics, magics_class, line_magic

from .main import find_dotenv, load_dotenv


@magics_class
class IPythonDotEnv(Magics):

    @line_magic
    def dotenv(self, line):
        """Load a .env file and set environment variables.

        Usage:
            %dotenv
            %dotenv path/to/.env
        """
        if line:
            dotenv_path = line.strip()
        else:
            dotenv_path = find_dotenv()
        load_dotenv(dotenv_path)


def load_ipython_extension(ipython):
    ipython.register_magics(IPythonDotEnv)

# variables.py
"""Module for parsing and resolving variables in dotenv values."""

import re
from abc import ABCMeta, abstractmethod
from typing import Iterator, Mapping, Optional, Pattern, Tuple


class Atom(metaclass=ABCMeta):
    """Protocol for atoms that can be resolved to string values."""

    @abstractmethod
    def resolve(self, env: Mapping[str, Optional[str]]) -> str:
        raise NotImplementedError


class Literal(Atom):
    """A literal string value."""

    def __init__(self, value: str) -> None:
        self.value = value

    def resolve(self, env: Mapping[str, Optional[str]]) -> str:
        return self.value


class Variable(Atom):
    """A variable reference that resolves from the environment."""

    def __init__(self, name: str, default: Optional[str] = None) -> None:
        self.name = name
        self.default = default

    def resolve(self, env: Mapping[str, Optional[str]]) -> str:
        result = env.get(self.name)
        if result is None:
            return self.default if self.default is not None else ""
        return result


_variable_pattern: Pattern[str] = re.compile(
    r"""
    \$\{(?P<name>[^}:\-]+)(?:\:\-(?P<default>[^}]*))?\}  # ${NAME} or ${NAME:-default}
    |
    \$(?P<simple_name>[A-Za-z_][A-Za-z0-9_]*)            # $NAME
    """,
    re.VERBOSE,
)


def parse_variables(value: str) -> Iterator[Atom]:
    """Parse a string value into a sequence of Literal and Variable atoms."""
    cursor = 0
    for match in _variable_pattern.finditer(value):
        start, end = match.span()
        if start > cursor:
            yield Literal(value[cursor:start])
        name = match.group("name") or match.group("simple_name")
        default = match.group("default")
        yield Variable(name=name, default=default)
        cursor = end
    if cursor < len(value):
        yield Literal(value[cursor:])

# version.py
yaml
- id: version
  name: version
  status: ACTIVE
  files:
  - src/dotenv/version.py
  kind: library
  variables:
  - __version__
# __init__.py
from .main import (
    dotenv_values,
    find_dotenv,
    get_key,
    load_dotenv,
    set_key,
    unset_key,
)
# __init__.py
"""Python-dotenv - Read key-value pairs from a .env file and set them as environment variables."""

from .main import (
    dotenv_values,
    find_dotenv,
    get_key,
    load_dotenv,
    set_key,
    unset_key,
)
from .version import __version__

# zip_imports.py
"""Handle graceful behavior when dotenv is imported from within zip files."""

import os
import zipfile

from .main import find_dotenv, load_dotenv


def _is_zip_path(path):
    """Check if the given path is inside a zip file."""
    if path is None:
        return False
    parts = os.path.normpath(path).split(os.sep)
    for i in range(len(parts)):
        partial = os.sep.join(parts[:i + 1])
        if zipfile.is_zipfile(partial):
            return True
        if partial.endswith(('.zip', '.egg')):
            return True
    return False


def _find_dotenv_safe(filename='.env', raise_error_if_not_found=False, usecwd=False):
    """Safely find dotenv file, handling zip import scenarios gracefully."""
    try:
        return find_dotenv(filename=filename,
                           raise_error_if_not_found=raise_error_if_not_found,
                           usecwd=usecwd)
    except (ValueError, OSError, TypeError):
        return ''


def load_dotenv_gracefully(dotenv_path=None, **kwargs):
    """
    Load dotenv file, gracefully handling cases where code is running
    from within a zip archive and no .env file is present.

    Returns True if a .env file was found and loaded, False otherwise.
    """
    if dotenv_path is None:
        try:
            import inspect
            frame = inspect.currentframe()
            caller_file = None
            if frame and frame.f_back:
                caller_file = frame.f_back.f_globals.get('__file__')

            if caller_file and _is_zip_path(caller_file):
                dotenv_path = _find_dotenv_safe(usecwd=True)
            else:
                dotenv_path = _find_dotenv_safe()
        except (AttributeError, TypeError, ValueError):
            dotenv_path = ''

    if not dotenv_path or not os.path.isfile(dotenv_path):
        return False

    return load_dotenv(dotenv_path=dotenv_path, **kwargs)
# zip_imports.py
"""Support for handling imports from zip files gracefully."""

import os
import zipfile
from typing import Optional


def is_zip_path(path: str) -> bool:
    """Check if a given path is inside a zip file."""
    parts = os.path.normpath(path).split(os.sep)
    accumulated = ""
    for part in parts:
        accumulated = os.path.join(accumulated, part) if accumulated else part
        if zipfile.is_zipfile(accumulated):
            return True
        # Check for common zip extensions in the path
        if any(accumulated.endswith(ext) for ext in ('.zip', '.egg', '.whl')):
            return True
    return False


def find_dotenv_in_zip_context(usecwd: bool = False, filename: str = '.env') -> Optional[str]:
    """Attempt to find a .env file, gracefully handling zip import contexts.

    When code is running from within a zip file, the normal file-based
    directory traversal may not work. In that case, fall back to using
    the current working directory.

    Returns the path to the .env file if found, or an empty string if not.
    """
    if usecwd:
        path = os.path.join(os.getcwd(), filename)
        return path if os.path.isfile(path) else ''

    # Try to walk up from cwd
    path = os.getcwd()
    while True:
        check_path = os.path.join(path, filename)
        if os.path.isfile(check_path):
            return check_path
        parent = os.path.dirname(path)
        if parent == path:
            break
        path = parent

    return ''


def handle_zip_import(caller_path: str, filename: str = '.env') -> str:
    """Handle the case where the caller is inside a zip archive.

    If the caller's __file__ is inside a zip, we cannot traverse
    directories relative to it. Instead, we fall back to the current
    working directory.

    Args:
        caller_path: The __file__ of the calling module.
        filename: The name of the dotenv file to find.

    Returns:
        Path to the .env file, or empty string if not found.
    """
    if is_zip_path(caller_path):
        # Fall back to current working directory when inside a zip
        return find_dotenv_in_zip_context(usecwd=True, filename=filename)
    return find_dotenv_in_zip_context(usecwd=False, filename=filename)
