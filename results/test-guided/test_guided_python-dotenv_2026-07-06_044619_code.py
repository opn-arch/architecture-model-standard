# cli.py
"""cli.py - Command line interface for dotenv management."""

import os
import sys
from subprocess import Popen, PIPE

import click

from .main import dotenv_values, get_key, set_key, unset_key


def enumerate_env(path):
    """Enumerate environment variables from a .env file."""
    if not os.path.exists(path):
        raise IOError("Error opening env file")
    values = dotenv_values(path)
    return values


@click.group()
@click.option('-f', '--file', default='.env', type=click.Path(exists=False),
              help='Location of the .env file.')
@click.option('-q', '--quote', default='always',
              type=click.Choice(['always', 'never', 'auto']),
              help='Whether to quote values.')
@click.option('-e', '--export', default=True, type=bool,
              help='Whether to write export statements.')
@click.pass_context
def cli(ctx, file, quote, export):
    """A CLI interface for dotenv files."""
    ctx.ensure_object(dict)
    ctx.obj['FILE'] = file
    ctx.obj['QUOTE'] = quote
    ctx.obj['EXPORT'] = export


def stream_file(path):
    """Stream contents of a file."""
    if not os.path.exists(path):
        raise IOError("Error opening env file")
    with open(path, 'r') as f:
        for line in f:
            yield line


@cli.command()
@click.pass_context
def list_values(ctx):
    """List all values in the .env file."""
    file = ctx.obj['FILE']
    if not os.path.isfile(file):
        raise click.UsageError("Error opening env file")
    try:
        values = enumerate_env(file)
        for key, value in values.items():
            click.echo(f"{key}={value}")
    except IOError as e:
        raise click.UsageError(str(e))


@cli.command()
@click.argument('key')
@click.argument('value')
@click.pass_context
def set_value(ctx, key, value):
    """Set a value in the .env file."""
    file = ctx.obj['FILE']
    quote = ctx.obj['QUOTE']
    export = ctx.obj['EXPORT']
    if not os.path.isfile(file):
        raise click.UsageError("Error opening env file")
    success, key, value = set_key(file, key, value, quote_mode=quote, export=export)
    if success:
        click.echo(f"{key}={value}")
    else:
        sys.exit(1)


@cli.command()
@click.argument('key')
@click.pass_context
def get(ctx, key):
    """Get a value from the .env file."""
    file = ctx.obj['FILE']
    if not os.path.isfile(file):
        raise click.UsageError("Error opening env file")
    stored_value = get_key(file, key)
    if stored_value is not None:
        click.echo(f"{key}={stored_value}")
    else:
        sys.exit(1)


@cli.command()
@click.argument('key')
@click.pass_context
def unset(ctx, key):
    """Unset a value in the .env file."""
    file = ctx.obj['FILE']
    if not os.path.isfile(file):
        raise click.UsageError("Error opening env file")
    success, key = unset_key(file, key)
    if success:
        click.echo(f"Successfully removed {key}")
    else:
        sys.exit(1)


@cli.command()
@click.argument('commandline', nargs=-1, required=True)
@click.pass_context
def run(ctx, commandline):
    """Run a command with the .env file loaded."""
    file = ctx.obj['FILE']
    if not os.path.isfile(file):
        raise click.UsageError("Error opening env file")
    try:
        values = enumerate_env(file)
    except IOError as e:
        raise click.UsageError(str(e))

    env = os.environ.copy()
    env.update(values)

    ret = run_command(commandline, env)
    sys.exit(ret)


def run_command(command, env=None):
    """Run a command in a subprocess with the given environment."""
    if env is None:
        env = os.environ.copy()

    try:
        proc = Popen(command, env=env, stdout=PIPE, stderr=PIPE, shell=False)
        stdout, stderr = proc.communicate()
        if stdout:
            click.echo(stdout.decode('utf-8'), nl=False)
        if stderr:
            click.echo(stderr.decode('utf-8'), nl=False, err=True)
        return proc.returncode
    except FileNotFoundError:
        click.echo(f"Command not found: {command[0]}", err=True)
        return 1
    except Exception as e:
        click.echo(f"Error running command: {e}", err=True)
        return 1

# ipython.py
"""IPython extension for dotenv magic commands."""

from IPython.core.magic import Magics, magics_class, line_magic

from .main import dotenv_values, set_key, get_key, unset_key, find_dotenv


@magics_class
class IPythonDotEnv(Magics):
    """IPython magic commands for working with .env files."""

    @line_magic
    def dotenv(self, line=""):
        """Load .env file and set environment variables.

        Usage:
            %dotenv
            %dotenv /path/to/.env
            %dotenv -o /path/to/.env  (override existing vars)
            %dotenv -v /path/to/.env  (verbose mode)
        """
        import os
        import sys

        args = line.strip().split()

        override = False
        verbose = False
        dotenv_path = None

        i = 0
        while i < len(args):
            if args[i] == "-o" or args[i] == "--override":
                override = True
            elif args[i] == "-v" or args[i] == "--verbose":
                verbose = True
            else:
                dotenv_path = args[i]
            i += 1

        if dotenv_path is None:
            try:
                dotenv_path = find_dotenv(raise_error_if_not_found=True)
            except IOError:
                print("Could not find .env file")
                return

        dotenv_path = os.path.expanduser(dotenv_path)

        if not os.path.isfile(dotenv_path):
            print(f"Error: file '{dotenv_path}' not found")
            return

        dotenv_dict = dotenv_values(dotenv_path)

        if verbose:
            print(f"Loading .env file: {dotenv_path}")

        for key, value in dotenv_dict.items():
            if key is None:
                continue

            if override or key not in os.environ:
                if value is not None:
                    os.environ[key] = value
                    if verbose:
                        print(f"  Set {key}={value}")
            else:
                if verbose:
                    print(f"  Skipping {key} (already set)")


def load_ipython_extension(ipython):
    """Register the dotenv magic when the extension is loaded.

    Usage in IPython/Jupyter:
        %load_ext dotenv
        %dotenv
    """
    ipython.register_magics(IPythonDotEnv)

# main.py
"""main.py - DotEnv module for parsing, loading, and managing .env files."""

import os
import re
import sys
import warnings
from collections import OrderedDict
from pathlib import Path
from typing import Dict, Iterator, Optional, Tuple, Union, IO


def with_warn_for_invalid_lines(mappings: Iterator[Tuple[Optional[str], Optional[str]]]) -> Iterator[Tuple[str, str]]:
    """Filter out invalid lines and warn about them."""
    for line_num, (key, value) in enumerate(mappings, start=1):
        if key is None:
            if value is not None and value.strip():
                warnings.warn(
                    f"Python-dotenv could not parse statement starting at line {line_num}",
                    UserWarning
                )
        else:
            yield key, value


def _parse_line(line: str) -> Tuple[Optional[str], Optional[str]]:
    """Parse a single line from a .env file."""
    line = line.strip()
    
    if not line or line.startswith('#'):
        return None, None
    
    if 'export ' in line and line.startswith('export '):
        line = line[len('export '):]
    
    if '=' not in line:
        return None, line
    
    key, _, value = line.partition('=')
    key = key.strip()
    value = value.strip()
    
    if not key:
        return None, line
    
    if value and value[0] in ('"', "'"):
        quote_char = value[0]
        if len(value) >= 2 and value[-1] == quote_char:
            value = value[1:-1]
        else:
            value = value[1:]
    
    if value and value[0] == '"':
        value = value.replace('\\n', '\n').replace('\\t', '\t')
    
    value = value.split('#')[0].strip() if not (value.startswith('"') or value.startswith("'")) else value
    
    return key, value


class DotEnv:
    """Manages .env file parsing and environment variable setting."""
    
    def __init__(
        self,
        dotenv_path: Optional[Union[str, Path]] = None,
        stream: Optional[IO[str]] = None,
        verbose: bool = False,
        encoding: Optional[str] = 'utf-8',
        interpolate: bool = True,
        override: bool = True
    ):
        self.dotenv_path = dotenv_path
        self.stream = stream
        self.verbose = verbose
        self.encoding = encoding
        self.interpolate = interpolate
        self.override = override
        self._dict: Optional[Dict[str, str]] = None

    def _get_stream(self) -> Iterator[str]:
        """Get a stream of lines from the dotenv file or stream."""
        if self.stream is not None:
            yield from self.stream
        elif self.dotenv_path is not None:
            path = Path(self.dotenv_path)
            if path.is_file():
                with open(path, encoding=self.encoding) as f:
                    yield from f
            else:
                if self.verbose:
                    warnings.warn(f"File doesn't exist {self.dotenv_path}", UserWarning)

    def parse(self) -> Iterator[Tuple[str, str]]:
        """Parse the .env file and yield key-value pairs."""
        raw_mappings = (_parse_line(line) for line in self._get_stream())
        if self.verbose:
            yield from with_warn_for_invalid_lines(raw_mappings)
        else:
            for key, value in raw_mappings:
                if key is not None:
                    yield key, value

    def dict(self) -> Dict[str, str]:
        """Return a dictionary of parsed key-value pairs."""
        if self._dict is not None:
            return self._dict
        
        raw_values = OrderedDict(self.parse())
        
        if self.interpolate:
            self._dict = resolve_variables(raw_values)
        else:
            self._dict = raw_values
        
        return self._dict

    def set_as_environment_variables(self) -> bool:
        """Set the parsed values as environment variables."""
        for key, value in self.dict().items():
            if key and value is not None:
                if self.override or key not in os.environ:
                    os.environ[key] = value
        return True

    def get(self, key: str) -> Optional[str]:
        """Get a specific value by key."""
        data = self.dict()
        if key in data:
            return data[key]
        if self.verbose:
            warnings.warn(f"Key {key} not found in {self.dotenv_path}", UserWarning)
        return None


def resolve_variables(
    values: Dict[str, str],
    override: bool = False
) -> Dict[str, str]:
    """Resolve variable interpolation in values."""
    new_values: Dict[str, str] = OrderedDict()
    
    variable_pattern = re.compile(
        r"""
        \$\{([^}]+)\}  |  # ${VAR} style
        \$([A-Za-z_][A-Za-z_0-9]*)  # $VAR style
        """,
        re.VERBOSE
    )
    
    for key, value in values.items():
        if value is None:
            new_values[key] = ""
            continue
        
        def _replace_var(match):
            var_name = match.group(1) or match.group(2)
            if var_name in new_values:
                return new_values[var_name]
            if var_name in os.environ and not override:
                return os.environ[var_name]
            return match.group(0)
        
        new_values[key] = variable_pattern.sub(_replace_var, value)
    
    return new_values


def get_key(
    dotenv_path: Union[str, Path],
    key_to_get: str,
    encoding: Optional[str] = 'utf-8'
) -> Optional[str]:
    """Get the value of a specific key from a .env file."""
    dotenv = DotEnv(dotenv_path=dotenv_path, encoding=encoding, interpolate=True)
    return dotenv.get(key_to_get)


def rewrite(path: Union[str, Path], encoding: str = 'utf-8') -> Iterator[Tuple[str, str]]:
    """Context-manager-like generator for rewriting a .env file in-place."""
    path = Path(path)
    
    if not path.is_file():
        path.touch()
    
    with open(path, encoding=encoding) as f:
        lines = f.readlines()
    
    new_lines = []
    
    class _Writer:
        def __init__(self):
            self.lines = []
        
        def write(self, line):
            self.lines.append(line)
    
    writer = _Writer()
    
    for line in lines:
        yield line, writer
        if writer.lines:
            new_lines.append(writer.lines[-1])
            writer.lines = []
        else:
            new_lines.append(line)
    
    with open(path, 'w', encoding=encoding) as f:
        f.writelines(new_lines)


def set_key(
    dotenv_path: Union[str, Path],
    key_to_set: str,
    value_to_set: str,
    quote_mode: str = 'always',
    export: bool = False,
    encoding: Optional[str] = 'utf-8'
) -> Tuple[Optional[bool], str, str]:
    """Set a key-value pair in a .env file."""
    dotenv_path = Path(dotenv_path)
    
    if not dotenv_path.is_file():
        dotenv_path.parent.mkdir(parents=True, exist_ok=True)
        dotenv_path.touch()
    
    if quote_mode == 'always':
        value_out = f'"{value_to_set}"'
    elif quote_mode == 'auto':
        if ' ' in value_to_set or '#' in value_to_set or "'" in value_to_set:
            value_out = f'"{value_to_set}"'
        else:
            value_out = value_to_set
    else:
        value_out = value_to_set
    
    export_str = "export " if export else ""
    line_out = f"{export_str}{key_to_set}={value_out}\n"
    
    key_found = False
    new_lines = []
    
    with open(dotenv_path, encoding=encoding) as f:
        lines = f.readlines()
    
    for line in lines:
        parsed_key, _ = _parse_line(line)
        stripped = line.strip()
        if stripped.startswith('export '):
            stripped = stripped[len('export '):]
        check_key = stripped.split('=')[0].strip() if '=' in stripped else None
        
        if check_key == key_to_set or parsed_key == key_to_set:
            new_lines.append(line_out)
            key_found = True
        else:
            new_lines.append(line)
    
    if not key_found:
        if new_lines and not new_lines[-1].endswith('\n'):
            new_lines.append('\n')
        new_lines.append(line_out)
    
    with open(dotenv_path, 'w', encoding=encoding) as f:
        f.writelines(new_lines)
    
    return True, key_to_set, value_to_set


def unset_key(
    dotenv_path: Union[str, Path],
    key_to_unset: str,
    quote_mode: str = 'always',
    encoding: Optional[str] = 'utf-8'
) -> Tuple[Optional[bool], str]:
    """Remove a key from a .env file."""
    dotenv_path = Path(dotenv_path)
    
    if not dotenv_path.is_file():
        warnings.warn(f"Can't delete from {dotenv_path} - it doesn't exist.", UserWarning)
        return None, key_to_unset
    
    new_lines = []
    key_found = False
    
    with open(dotenv_path, encoding=encoding) as f:
        lines = f.readlines()
    
    for line in lines:
        parsed_key, _ = _parse_line(line)
        stripped = line.strip()
        if stripped.startswith('export '):
            stripped = stripped[len('export '):]
        check_key = stripped.split('=')[0].strip() if '=' in stripped else None
        
        if check_key == key_to_unset or parsed_key == key_to_unset:
            key_found = True
        else:
            new_lines.append(line)
    
    with open(dotenv_path, 'w', encoding=encoding) as f:
        f.writelines(new_lines)
    
    if key_found:
        return True, key_to_unset
    return None, key_to_unset


def find_dotenv(
    filename: str = '.env',
    raise_error_if_not_found: bool = False,
    usecwd: bool = False
) -> str:
    """Search for a .env file by walking up directories."""
    if usecwd:
        start = os.getcwd()
    else:
        frame = sys._getframe()
        caller_dir = os.path.dirname(os.path.abspath(
            frame.f_back.f_code.co_filename if frame.f_back else __file__
        ))
        start = caller_dir
    
    current = start
    while True:
        check_path = os.path.join(current, filename)
        if os.path.isfile(check_path):
            return check_path
        
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    
    if raise_error_if_not_found:
        raise IOError(f"File {filename} not found starting from {start}")
    
    return ''


def load_dotenv(
    dotenv_path: Optional[Union[str, Path]] = None,
    stream: Optional[IO[str]] = None,
    verbose: bool = False,
    interpolate: bool = True,
    override: bool = False,
    encoding: Optional[str] = 'utf-8'
) -> bool:
    """Load a .env file and set environment variables."""
    if dotenv_path is None and stream is None:
        dotenv_path = find_dotenv()
    
    dotenv = DotEnv(
        dotenv_path=dotenv_path,
        stream=stream,
        verbose=verbose,
        encoding=encoding,
        interpolate=interpolate,
        override=override
    )
    return dotenv.set_as_environment_variables()


def dotenv_values(
    dotenv_path: Optional[Union[str, Path]] = None,
    stream: Optional[IO[str]] = None,
    verbose: bool = False,
    interpolate: bool = True,
    encoding: Optional[str] = 'utf-8'
) -> Dict[str, str]:
    """Parse a .env file and return a dictionary of key-value pairs."""
    if dotenv_path is None and stream is None:
        dotenv_path = find_dotenv()
    
    dotenv = DotEnv(
        dotenv_path=dotenv_path,
        stream=stream,
        verbose=verbose,
        encoding=encoding,
        interpolate=interpolate,
        override=True
    )
    return dotenv.dict()

# parser.py
"""parser.py - Parser for .env files."""

import codecs
import re
from typing import IO, Iterator, NamedTuple, Optional, Pattern, Tuple


class Original(NamedTuple):
    string: str
    line: int


class Binding(NamedTuple):
    key: str
    value: str
    original: Original
    error: bool


class Position:
    def __init__(self, chars: str, line: int = 1):
        self.chars = chars
        self.line = line
        self.index = 0

    def start(self) -> int:
        return self.index

    def set(self, index: int) -> None:
        self.index = index

    def advance(self, count: int) -> None:
        self.index += count


class Error(Exception):
    pass


class Reader:
    def __init__(self, stream: str):
        self.string = stream
        self.position = Position(stream)
        self.mark = 0

    def has_next(self) -> bool:
        return self.position.index < len(self.string)

    def set_mark(self) -> None:
        self.mark = self.position.start()

    def get_marked(self) -> str:
        return self.string[self.mark:self.position.index]

    def peek(self, count: int = 1) -> str:
        return self.string[self.position.index:self.position.index + count]

    def read(self, count: int = 1) -> str:
        result = self.string[self.position.index:self.position.index + count]
        self.position.advance(count)
        return result

    def read_regex(self, regex: Pattern[str]) -> str:
        match = regex.match(self.string, self.position.index)
        if match:
            self.position.advance(len(match.group(0)))
            return match.group(0)
        return ""


def make_regex(pattern: str) -> Pattern[str]:
    return re.compile(pattern)


def decode_escapes(s: str) -> str:
    """Process escape sequences in a string."""
    return codecs.decode(s, 'unicode_escape')


_KEY_REGEX = make_regex(r"[a-zA-Z_][a-zA-Z0-9_]*")
_EXPORT_REGEX = make_regex(r"export\s+")
_WHITESPACE_REGEX = make_regex(r"\s*")
_NEWLINE_REGEX = make_regex(r"(\r\n|\r|\n)")
_SINGLE_QUOTE_REGEX = make_regex(r"'([^']*)'")
_DOUBLE_QUOTE_REGEX = make_regex(r'"([^"]*)"')
_UNQUOTED_VALUE_REGEX = make_regex(r"[^\s#\r\n]*")
_COMMENT_REGEX = make_regex(r"#[^\r\n]*")


def parse_key(reader: Reader) -> str:
    reader.read_regex(_EXPORT_REGEX)
    # Check for quoted key
    if reader.has_next() and reader.peek() == "'":
        match = _SINGLE_QUOTE_REGEX.match(reader.string, reader.position.index)
        if match:
            reader.position.advance(len(match.group(0)))
            return match.group(1)
    if reader.has_next() and reader.peek() == '"':
        match = _DOUBLE_QUOTE_REGEX.match(reader.string, reader.position.index)
        if match:
            reader.position.advance(len(match.group(0)))
            return match.group(1)
    key = reader.read_regex(_KEY_REGEX)
    if not key:
        raise Error("Expected key")
    return key


def parse_unquoted_value(reader: Reader) -> str:
    value = reader.read_regex(_UNQUOTED_VALUE_REGEX)
    return value.strip()


def parse_value(reader: Reader) -> str:
    if not reader.has_next() or reader.peek() in ('\r', '\n', '#'):
        return ""
    if reader.peek() == "'":
        match = _SINGLE_QUOTE_REGEX.match(reader.string, reader.position.index)
        if match:
            reader.position.advance(len(match.group(0)))
            return match.group(1)
    if reader.peek() == '"':
        match = _DOUBLE_QUOTE_REGEX.match(reader.string, reader.position.index)
        if match:
            reader.position.advance(len(match.group(0)))
            return decode_escapes(match.group(1))
    return parse_unquoted_value(reader)


def parse_binding(reader: Reader, line: int) -> Binding:
    reader.set_mark()
    try:
        reader.read_regex(_WHITESPACE_REGEX)
        if not reader.has_next() or reader.peek() in ('\r', '\n', '#'):
            # Skip empty lines and comments
            reader.read_regex(_COMMENT_REGEX)
            reader.read_regex(_NEWLINE_REGEX)
            original_string = reader.get_marked()
            return Binding(key="", value="", original=Original(string=original_string, line=line), error=False)
        key = parse_key(reader)
        reader.read_regex(_WHITESPACE_REGEX)
        if reader.has_next() and reader.peek() == '=':
            reader.read(1)
        else:
            raise Error("Expected '='")
        reader.read_regex(_WHITESPACE_REGEX)
        value = parse_value(reader)
        reader.read_regex(_WHITESPACE_REGEX)
        reader.read_regex(_COMMENT_REGEX)
        reader.read_regex(_NEWLINE_REGEX)
        original_string = reader.get_marked()
        return Binding(key=key, value=value, original=Original(string=original_string, line=line), error=False)
    except Error:
        # Read to end of line on error
        while reader.has_next() and reader.peek() not in ('\r', '\n'):
            reader.read(1)
        reader.read_regex(_NEWLINE_REGEX)
        original_string = reader.get_marked()
        return Binding(key="", value="", original=Original(string=original_string, line=line), error=True)


def parse_stream(stream: str) -> Iterator[Binding]:
    reader = Reader(stream)
    line = 1
    while reader.has_next():
        binding = parse_binding(reader, line)
        if binding.key or binding.error:
            yield binding
        line += 1

# variables.py
"""variables.py - Module for parsing variable expressions from strings."""

from __future__ import annotations

import re
from typing import Optional


class Atom:
    """Base class for parsed atoms."""

    def resolve(self, env: dict[str, str] | None = None) -> str:
        raise NotImplementedError


class Literal(Atom):
    """Represents a literal string value."""

    def __init__(self, value: str):
        self.value = value

    def resolve(self, env: dict[str, str] | None = None) -> str:
        return self.value

    def __eq__(self, other):
        if isinstance(other, Literal):
            return self.value == other.value
        return NotImplemented

    def __repr__(self):
        return f"Literal(value={self.value!r})"


class Variable(Atom):
    """Represents a variable reference with optional default."""

    def __init__(self, name: str, default: Optional[str] = None):
        self.name = name
        self.default = default

    def resolve(self, env: dict[str, str] | None = None) -> str:
        if env is None:
            env = {}
        value = env.get(self.name)
        if value is not None:
            return value
        if self.default is not None:
            return self.default
        return ""

    def __eq__(self, other):
        if isinstance(other, Variable):
            return self.name == other.name and self.default == other.default
        return NotImplemented

    def __repr__(self):
        return f"Variable(name={self.name!r}, default={self.default!r})"


def parse_variables(text: str) -> list[Atom]:
    """Parse a string into a list of Literal and Variable atoms.

    Supports ${name} and ${name:-default} syntax.
    """
    if not text:
        return []

    results: list[Atom] = []
    pattern = re.compile(r'\$\{([^}]*)\}')
    pos = 0

    for match in pattern.finditer(text):
        start = match.start()
        # Add any literal text before this variable
        if start > pos:
            results.append(Literal(value=text[pos:start]))

        content = match.group(1)
        # Check for default value separator :-
        if ':-' in content:
            name, default = content.split(':-', 1)
            results.append(Variable(name=name, default=default))
        else:
            results.append(Variable(name=content, default=None))

        pos = match.end()

    # Add any remaining literal text
    if pos < len(text):
        results.append(Literal(value=text[pos:]))

    return results

# version.py
"""Version module for tracking and comparing software versions."""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple, Union


class ReleaseType(Enum):
    """Enumeration of release types."""
    ALPHA = "alpha"
    BETA = "beta"
    RC = "rc"
    RELEASE = "release"


@dataclass
class Version:
    """Represents a semantic version (major.minor.patch) with optional pre-release info."""

    major: int
    minor: int
    patch: int
    pre_release: Optional[ReleaseType] = None
    pre_release_num: Optional[int] = None
    build_metadata: Optional[str] = None

    def __post_init__(self):
        if self.major < 0 or self.minor < 0 or self.patch < 0:
            raise ValueError("Version numbers must be non-negative integers")
        if self.pre_release_num is not None and self.pre_release_num < 0:
            raise ValueError("Pre-release number must be non-negative")

    @property
    def is_pre_release(self) -> bool:
        """Check if this version is a pre-release."""
        return self.pre_release is not None and self.pre_release != ReleaseType.RELEASE

    @property
    def version_tuple(self) -> Tuple[int, int, int]:
        """Return the version as a tuple of (major, minor, patch)."""
        return (self.major, self.minor, self.patch)

    def _pre_release_order(self) -> int:
        """Return numeric ordering for pre-release types."""
        order = {
            ReleaseType.ALPHA: 0,
            ReleaseType.BETA: 1,
            ReleaseType.RC: 2,
            ReleaseType.RELEASE: 3,
            None: 3,
        }
        return order.get(self.pre_release, 3)

    def __str__(self) -> str:
        """Return string representation of the version."""
        version_str = f"{self.major}.{self.minor}.{self.patch}"
        if self.pre_release and self.pre_release != ReleaseType.RELEASE:
            version_str += f"-{self.pre_release.value}"
            if self.pre_release_num is not None:
                version_str += f".{self.pre_release_num}"
        if self.build_metadata:
            version_str += f"+{self.build_metadata}"
        return version_str

    def __repr__(self) -> str:
        """Return detailed string representation."""
        return (
            f"Version(major={self.major}, minor={self.minor}, patch={self.patch}, "
            f"pre_release={self.pre_release}, pre_release_num={self.pre_release_num})"
        )

    def __eq__(self, other: object) -> bool:
        """Check equality between two versions (ignoring build metadata)."""
        if not isinstance(other, Version):
            return NotImplemented
        return (
            self.version_tuple == other.version_tuple
            and self.pre_release == other.pre_release
            and self.pre_release_num == other.pre_release_num
        )

    def __lt__(self, other: "Version") -> bool:
        """Check if this version is less than another."""
        if not isinstance(other, Version):
            return NotImplemented
        if self.version_tuple != other.version_tuple:
            return self.version_tuple < other.version_tuple
        if self._pre_release_order() != other._pre_release_order():
            return self._pre_release_order() < other._pre_release_order()
        self_num = self.pre_release_num if self.pre_release_num is not None else 0
        other_num = other.pre_release_num if other.pre_release_num is not None else 0
        return self_num < other_num

    def __le__(self, other: "Version") -> bool:
        """Check if this version is less than or equal to another."""
        return self == other or self < other

    def __gt__(self, other: "Version") -> bool:
        """Check if this version is greater than another."""
        if not isinstance(other, Version):
            return NotImplemented
        return other < self

    def __ge__(self, other: "Version") -> bool:
        """Check if this version is greater than or equal to another."""
        return self == other or self > other

    def __hash__(self) -> int:
        """Return hash of the version."""
        return hash((self.major, self.minor, self.patch, self.pre_release, self.pre_release_num))

    def bump_major(self) -> "Version":
        """Return a new Version with major incremented, minor and patch reset."""
        return Version(major=self.major + 1, minor=0, patch=0)

    def bump_minor(self) -> "Version":
        """Return a new Version with minor incremented, patch reset."""
        return Version(major=self.major, minor=self.minor + 1, patch=0)

    def bump_patch(self) -> "Version":
        """Return a new Version with patch incremented."""
        return Version(major=self.major, minor=self.minor, patch=self.patch + 1)

    def is_compatible_with(self, other: "Version") -> bool:
        """Check if this version is API-compatible with another (same major, >= minor)."""
        if self.major != other.major:
            return False
        if self.major == 0:
            return self.minor == other.minor and self.patch >= other.patch
        return self >= other


def parse(version_string: str) -> Version:
    """Parse a version string into a Version object.

    Supports formats like:
        - "1.2.3"
        - "1.2.3-alpha.1"
        - "1.2.3-beta.2+build.123"
    """
    pattern = (
        r"^v?(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"
        r"(?:-(?P<pre_release>alpha|beta|rc)(?:\.(?P<pre_num>\d+))?)?"
        r"(?:\+(?P<build>.+))?$"
    )
    match = re.match(pattern, version_string.strip())
    if not match:
        raise ValueError(f"Invalid version string: '{version_string}'")

    major = int(match.group("major"))
    minor = int(match.group("minor"))
    patch = int(match.group("patch"))

    pre_release = None
    pre_release_num = None
    if match.group("pre_release"):
        pre_release = ReleaseType(match.group("pre_release"))
        if match.group("pre_num"):
            pre_release_num = int(match.group("pre_num"))

    build_metadata = match.group("build")

    return Version(
        major=major,
        minor=minor,
        patch=patch,
        pre_release=pre_release,
        pre_release_num=pre_release_num,
        build_metadata=build_metadata,
    )


def is_valid(version_string: str) -> bool:
    """Check if a string is a valid version string."""
    try:
        parse(version_string)
        return True
    except ValueError:
        return False


def compare(v1: Union[str, Version], v2: Union[str, Version]) -> int:
    """Compare two versions. Returns -1, 0, or 1."""
    if isinstance(v1, str):
        v1 = parse(v1)
    if isinstance(v2, str):
        v2 = parse(v2)

    if v1 < v2:
        return -1
    elif v1 > v2:
        return 1
    return 0


def latest(*versions: Union[str, Version]) -> Version:
    """Return the latest (highest) version from a list of versions."""
    if not versions:
        raise ValueError("At least one version must be provided")
    parsed = [parse(v) if isinstance(v, str) else v for v in versions]
    return max(parsed)


def sort_versions(versions: list, reverse: bool = False) -> list:
    """Sort a list of version strings or Version objects."""
    parsed = [(parse(v) if isinstance(v, str) else v, v) for v in versions]
    parsed.sort(key=lambda x: x[0], reverse=reverse)
    return [original for _, original in parsed]


# Module-level version info
__version__ = "1.0.0"
CURRENT_VERSION = Version(major=1, minor=0, patch=0)


def get_version() -> str:
    """Return the current module version string."""
    return __version__


def get_version_info() -> Version:
    """Return the current module version as a Version object."""
    return CURRENT_VERSION