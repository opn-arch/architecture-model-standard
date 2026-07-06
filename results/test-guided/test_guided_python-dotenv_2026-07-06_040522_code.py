mermaid
graph TD
    cli --> main
    cli --> version
    ipython --> main
    main --> parser
    main --> variables
# __init__.py
from .main import (
    dotenv_values,
    find_dotenv,
    get_key,
    load_dotenv,
    set_key,
    unset_key,
)
from .version import __version__


def get_cli_string(path=None, action=None, key=None, value=None, quote=None):
    """Return a CLI string for the given parameters."""
    command = "dotenv"
    if path:
        command += f" -f {path}"
    if action:
        command += f" {action}"
        if key:
            command += f" {key}"
            if value:
                if quote:
                    command += f" {value} --quote {quote}"
                else:
                    command += f" {value}"
    return command


__all__ = [
    "__version__",
    "dotenv_values",
    "find_dotenv",
    "get_cli_string",
    "get_key",
    "load_dotenv",
    "set_key",
    "unset_key",
]
# zip_imports.py
"""
Handles graceful behavior when python-dotenv is used from within zip imports.

When code is running from a zip file (e.g., a .zip or .egg), filesystem
operations like finding .env files may not work as expected. This module
provides utilities to detect and handle such cases.
"""

import os
import zipfile


def is_zip_path(path):
    """Check if the given path is inside a zip file."""
    if not path:
        return True
    parts = os.path.normpath(path).split(os.sep)
    accumulated = ""
    for part in parts:
        accumulated = os.path.join(accumulated, part) if accumulated else part
        if zipfile.is_zipfile(accumulated):
            return True
        if accumulated.endswith(('.zip', '.egg')):
            return True
    return False


def find_dotenv_in_zip_context(usecwd=False, raise_error_if_not_found=False, filename='.env'):
    """
    Attempt to find a dotenv file, gracefully handling zip import contexts.

    Returns the path to the .env file if found, or an empty string if not found
    or if running from a zip import context where filesystem traversal isn't possible.
    """
    from dotenv.main import find_dotenv

    try:
        return find_dotenv(filename=filename, raise_error_if_not_found=raise_error_if_not_found, usecwd=usecwd)
    except (ValueError, OSError, TypeError):
        if raise_error_if_not_found:
            raise
        return ""


def load_dotenv_gracefully(dotenv_path=None, stream=None, verbose=False, interpolate=True,
                           override=False, encoding='utf-8'):
    """
    Load dotenv file, gracefully handling zip import scenarios.

    When running from within a zip file and no explicit path is given,
    this will return False without raising an error.
    """
    from dotenv.main import load_dotenv

    try:
        if dotenv_path is None and stream is None:
            try:
                dotenv_path = find_dotenv_in_zip_context()
            except Exception:
                return False

            if not dotenv_path:
                return False

        return load_dotenv(
            dotenv_path=dotenv_path,
            stream=stream,
            verbose=verbose,
            interpolate=interpolate,
            override=override,
            encoding=encoding,
        )
    except (FileNotFoundError, OSError, TypeError):
        return False
# __init__.py
from .main import (
    dotenv_values,
    find_dotenv,
    get_key,
    load_dotenv,
    set_key,
    unset_key,
)
from .version import __version__


def get_cli_string(path=None, action=None, key=None, value=None, quote=None):
    """Return a CLI string for the given parameters."""
    command = "dotenv"
    if path:
        command += f" -f {path}"
    if action:
        command += f" {action}"
        if key:
            command += f" {key}"
            if value:
                if quote:
                    command += f" {value} --quote {quote}"
                else:
                    command += f" {value}"
    return command


__all__ = [
    "__version__",
    "dotenv_values",
    "find_dotenv",
    "get_cli_string",
    "get_key",
    "load_dotenv",
    "set_key",
    "unset_key",
]

# cli.py
import os
import shlex
import subprocess
import sys
from typing import Dict, List

import click

from .main import dotenv_values, set_key, unset_key
from .version import __version__


def enumerate_env(path=None):
    """Return a dictionary of the values in the .env file."""
    return dotenv_values(dotenv_path=path)


def stream_file(path):
    """Stream the contents of a file."""
    with open(path, "r") as f:
        for line in f:
            yield line


@click.group()
@click.option("-f", "--file", default=os.path.join(os.getcwd(), ".env"),
              type=click.Path(exists=False),
              help="Location of the .env file.")
@click.option("-q", "--quote", default="always",
              type=click.Choice(["always", "never", "auto"]),
              help="Whether to quote values.")
@click.option("-e", "--export", default=True,
              type=bool,
              help="Whether to write export in front of the key.")
@click.version_option(version=__version__)
@click.pass_context
def cli(ctx, file, quote, export):
    """A CLI interface for python-dotenv."""
    ctx.ensure_object(dict)
    ctx.obj["FILE"] = file
    ctx.obj["QUOTE"] = quote
    ctx.obj["EXPORT"] = export


@cli.command()
@click.pass_context
def list_values(ctx):
    """Display all the stored key/value pairs."""
    file = ctx.obj["FILE"]
    values = dotenv_values(dotenv_path=file)
    for k, v in values.items():
        click.echo(f"{k}={v}")


@cli.command("set")
@click.argument("key")
@click.argument("value")
@click.pass_context
def set_value(ctx, key, value):
    """Store the given key/value pair."""
    file = ctx.obj["FILE"]
    quote = ctx.obj["QUOTE"]
    export = ctx.obj["EXPORT"]
    success, key, value = set_key(file, key, value, quote=quote, export=export)
    if success:
        click.echo(f"{key}={value}")
    else:
        exit(1)


@cli.command()
@click.argument("key")
@click.pass_context
def get(ctx, key):
    """Retrieve the value for the given key."""
    file = ctx.obj["FILE"]
    values = dotenv_values(dotenv_path=file)
    stored_value = values.get(key)
    if stored_value is not None:
        click.echo(f"{key}={stored_value}")
    else:
        exit(1)


@cli.command()
@click.argument("key")
@click.pass_context
def unset(ctx, key):
    """Remove the given key."""
    file = ctx.obj["FILE"]
    success, key = unset_key(file, key)
    if success:
        click.echo(f"Successfully removed {key}")
    else:
        exit(1)


@cli.command()
@click.argument("commandline", nargs=-1, type=click.UNPROCESSED)
@click.pass_context
def run(ctx, commandline):
    """Run a command with the environment from the .env file."""
    file = ctx.obj["FILE"]
    if not commandline:
        click.echo("No command given.")
        exit(1)
    run_command(commandline, file)


def run_command(command, env_file):
    """Run a command with the given .env file loaded into the environment."""
    values = dotenv_values(dotenv_path=env_file)
    env = os.environ.copy()
    env.update(values)

    if isinstance(command, (list, tuple)):
        ret = subprocess.call(command, env=env)
    else:
        ret = subprocess.call(shlex.split(command), env=env)

    sys.exit(ret)
