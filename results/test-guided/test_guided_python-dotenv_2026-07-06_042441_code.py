# cli.py
"""Command-line interface for python-dotenv."""

import os
import sys
import subprocess
import shlex
from contextlib import contextmanager
from typing import Dict, List, Optional, IO

import click

from .main import dotenv_values, set_key, unset_key
from .version import __version__


@contextmanager
def stream_file(path: str):
    """Open a file or yield stdin/stdout as appropriate."""
    if path == "-":
        yield sys.stdin
    else:
        with open(path, "r") as f:
            yield f


def enumerate_env(path: str) -> Dict[str, Optional[str]]:
    """Return the key-value pairs from a .env file."""
    return dotenv_values(dotenv_path=path)


@click.group()
@click.option(
    "-f",
    "--file",
    default=os.path.join(os.getcwd(), ".env"),
    type=click.Path(exists=False),
    help="Location of the .env file.",
)
@click.option(
    "-q",
    "--quote",
    default="always",
    type=click.Choice(["always", "never", "auto"]),
    help="Whether to quote or not the variable values.",
)
@click.option(
    "-e",
    "--export",
    default=True,
    type=bool,
    help="Whether to write the dot file as an executable bash script.",
)
@click.version_option(version=__version__)
@click.pass_context
def cli(ctx: click.Context, file: str, quote: str, export: bool) -> None:
    """A command-line interface for python-dotenv."""
    ctx.ensure_object(dict)
    ctx.obj["FILE"] = file
    ctx.obj["QUOTE"] = quote
    ctx.obj["EXPORT"] = export


@cli.command()
@click.pass_context
@click.option(
    "--format",
    "format_",
    default="simple",
    type=click.Choice(["simple", "json", "shell", "export"]),
    help="The format in which to display the list.",
)
def list_values(ctx: click.Context, format_: str) -> None:
    """Display all the stored key/value pairs."""
    file = ctx.obj["FILE"]
    values = enumerate_env(file)

    if format_ == "json":
        import json
        click.echo(json.dumps(values, indent=2))
    elif format_ == "shell":
        for k, v in values.items():
            click.echo(f"{k}={v}")
    elif format_ == "export":
        for k, v in values.items():
            click.echo(f"export {k}={v}")
    else:
        for k, v in values.items():
            click.echo(f"{k}={v}")


@cli.command()
@click.pass_context
@click.argument("key")
@click.argument("value")
def set_value(ctx: click.Context, key: str, value: str) -> None:
    """Store the given key/value pair."""
    file = ctx.obj["FILE"]
    quote = ctx.obj["QUOTE"]
    export = ctx.obj["EXPORT"]
    success, key, value = set_key(file, key, value, quote=quote, export=export)
    if success:
        click.echo(f"{key}={value}")
    else:
        click.echo("Error: could not set value.", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
@click.argument("key")
def get(ctx: click.Context, key: str) -> None:
    """Retrieve the value for the given key."""
    file = ctx.obj["FILE"]
    values = enumerate_env(file)
    stored_value = values.get(key)
    if stored_value is not None:
        click.echo(f"{key}={stored_value}")
    else:
        click.echo("Error: key not found.", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
@click.argument("key")
def unset(ctx: click.Context, key: str) -> None:
    """Remove the given key."""
    file = ctx.obj["FILE"]
    success, key = unset_key(file, key)
    if success:
        click.echo(f"Successfully removed {key}")
    else:
        click.echo("Error: could not unset key.", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
@click.option(
    "--override/--no-override",
    default=True,
    help="Override existing environment variables.",
)
@click.argument("commandline", nargs=-1, type=click.UNPROCESSED)
def run(ctx: click.Context, override: bool, commandline: List[str]) -> None:
    """Run a command with the environment variables set."""
    file = ctx.obj["FILE"]
    if not commandline:
        click.echo("Error: no command given.", err=True)
        sys.exit(1)
    run_command(commandline, file, override=override)


def run_command(command: List[str], file: str, override: bool = True) -> None:
    """Run a command with the environment from the .env file."""
    values = enumerate_env(file)
    env = os.environ.copy()

    for key, value in values.items():
        if value is not None:
            if override or key not in env:
                env[key] = value

    try:
        ret = subprocess.run(command, env=env)
        sys.exit(ret.returncode)
    except FileNotFoundError:
        click.echo(f"Error: command '{command[0]}' not found.", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

# ipython.py
from IPython.core.magic import Magics, magics_class, line_magic

from .main import find_dotenv, load_dotenv


@magics_class
class IPythonDotEnv(Magics):

    @line_magic
    def dotenv(self, line):
        """Load a .env file and set environment variables.

        Usage: %dotenv [path]
        """
        path = line.strip()
        if not path:
            path = find_dotenv()
        load_dotenv(path)


def load_ipython_extension(ipython):
    """Register the %dotenv magic when the extension is loaded."""
    ipython.register_magics(IPythonDotEnv)

# variables.py
"""Module for parsing and resolving variable interpolation in dotenv values."""

import re
from abc import ABCMeta, abstractmethod
from typing import Iterator, Mapping, Optional, Pattern, Tuple


class Atom(metaclass=ABCMeta):
    """Protocol for atoms that can be resolved to string values."""

    @abstractmethod
    def resolve(self, env: Mapping[str, Optional[str]]) -> str:
        raise NotImplementedError


class Literal(Atom):
    """A literal string value that resolves to itself."""

    def __init__(self, value: str) -> None:
        self.value = value

    def resolve(self, env: Mapping[str, Optional[str]]) -> str:
        return self.value


class Variable(Atom):
    """A variable reference that resolves by looking up its name in the environment."""

    def __init__(self, name: str, default: Optional[str] = None) -> None:
        self.name = name
        self.default = default

    def resolve(self, env: Mapping[str, Optional[str]]) -> str:
        result = env.get(self.name)
        if result is not None:
            return result
        if self.default is not None:
            return self.default
        return ""


_variable_pattern: Pattern[str] = re.compile(
    r"""
    \$\{(?P<name>[^}:\-]+)(?::-(?P<default>[^}]*))?\}  # ${NAME} or ${NAME:-default}
    |
    \$(?P<simple_name>[A-Za-z_][A-Za-z0-9_]*)          # $NAME
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
        name = match.group("name")
        if name is not None:
            default = match.group("default")
            yield Variable(name=name, default=default)
        else:
            simple_name = match.group("simple_name")
            yield Variable(name=simple_name)
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
    DotEnv,
)
from .version import __version__

__all__ = [
    "dotenv_values",
    "find_dotenv",
    "get_key",
    "load_dotenv",
    "set_key",
    "unset_key",
    "DotEnv",
    "__version__",
]
# __init__.py
"""python-dotenv - Parse and load .env files."""

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


def is_zip_path(path):
    """Check if a given path is inside a zip file."""
    if not path:
        return False
    # Check if any parent component of the path is a zip file
    parts = os.path.normpath(path).split(os.sep)
    current = ""
    for part in parts:
        current = os.path.join(current, part) if current else part
        if zipfile.is_zipfile(current):
            return True
        # Also check with root separator for absolute paths
        if not current.startswith(os.sep) and os.path.isabs(path):
            current = os.sep + current
            if zipfile.is_zipfile(current):
                return True
    return False


def find_dotenv_in_zip_context(usecwd=False, filename='.env'):
    """
    Attempt to find a .env file when running from a zip import context.

    When the caller is inside a zip file, fall back to using the current
    working directory to locate the .env file.

    Returns the path to the .env file, or an empty string if not found.
    """
    if usecwd:
        path = os.path.join(os.getcwd(), filename)
        return path if os.path.isfile(path) else ''

    # Walk up from cwd looking for the .env file
    current_dir = os.getcwd()
    while True:
        check_path = os.path.join(current_dir, filename)
        if os.path.isfile(check_path):
            return check_path
        parent = os.path.dirname(current_dir)
        if parent == current_dir:
            break
        current_dir = parent

    return ''


def load_dotenv_gracefully(dotenv_path=None, **kwargs):
    """
    Load dotenv gracefully handling zip import scenarios.

    If dotenv_path is not provided and the caller is within a zip file,
    this function will attempt to find the .env file relative to the
    current working directory instead of the caller's file location.
    """
    from .main import load_dotenv, find_dotenv

    if dotenv_path is None:
        try:
            dotenv_path = find_dotenv()
        except (TypeError, ValueError, OSError):
            dotenv_path = find_dotenv_in_zip_context()

    if not dotenv_path:
        return False

    if not os.path.isfile(dotenv_path):
        return False

    return load_dotenv(dotenv_path, **kwargs)
# zip_imports.py
"""Handle zip imports gracefully for python-dotenv.

When code is running from within a zip file (e.g., a .pyz archive),
find_dotenv and load_dotenv should not raise errors if no .env file
can be found.
"""

import os
import zipfile


def is_zip_import(frame_filename: str) -> bool:
    """Check if the given filename indicates a zip import."""
    parts = os.path.normpath(frame_filename).split(os.sep)
    for i, part in enumerate(parts):
        partial_path = os.sep.join(parts[:i + 1])
        if zipfile.is_zipfile(partial_path):
            return True
        # Check common zip extensions
        if any(part.endswith(ext) for ext in ('.zip', '.pyz', '.egg')):
            if os.path.isfile(partial_path):
                return True
    return False


def find_dotenv_from_zip(usecwd: bool = False, filename: str = ".env") -> str:
    """Attempt to find a .env file when running from a zip import.

    Returns the path to the .env file if found, or an empty string if not.
    This function never raises an exception.
    """
    if usecwd:
        path = os.path.join(os.getcwd(), filename)
        if os.path.isfile(path):
            return path
        return ""

    # Try current working directory as fallback
    path = os.path.join(os.getcwd(), filename)
    if os.path.isfile(path):
        return path

    return ""
