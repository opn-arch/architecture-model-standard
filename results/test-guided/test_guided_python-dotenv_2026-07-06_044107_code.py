# cli.py
"""cli.py - Command line interface for dotenv management."""

import os
import sys
from subprocess import Popen

import click

from .main import dotenv_values, set_key, unset_key
from .version import __version__


@click.group()
@click.option('-f', '--file', default=os.path.join(os.getcwd(), '.env'),
              type=click.Path(exists=False),
              help='Location of the .env file.')
@click.option('-q', '--quote', default='always',
              type=click.Choice(['always', 'never', 'auto']),
              help='Whether to quote or not the variable values.')
@click.option('-e', '--export', default=True,
              type=bool,
              help='Whether to write export in front of key/value pairs.')
@click.version_option(version=__version__)
@click.pass_context
def cli(ctx, file, quote, export):
    """A CLI interface for managing .env files."""
    ctx.ensure_object(dict)
    ctx.obj['FILE'] = file
    ctx.obj['QUOTE'] = quote
    ctx.obj['EXPORT'] = export


def enumerate_env(dotenv_path):
    """Return a list of key-value pairs from the env file."""
    if not os.path.exists(dotenv_path):
        return []
    values = dotenv_values(dotenv_path)
    return list(values.items())


def stream_file(dotenv_path):
    """Stream the contents of the env file."""
    if not os.path.isfile(dotenv_path):
        raise click.BadParameter("Error opening env file", param_hint="'-f'")
    with open(dotenv_path, 'r') as f:
        content = f.read()
    return content


@cli.command()
@click.pass_context
def list_values(ctx):
    """Display all the stored key/value pairs."""
    dotenv_path = ctx.obj['FILE']
    if not os.path.isfile(dotenv_path):
        raise click.UsageError("Error opening env file")
    values = enumerate_env(dotenv_path)
    for key, value in values:
        click.echo(f"{key}={value}")


@cli.command('set')
@click.argument('key')
@click.argument('value')
@click.pass_context
def set_value(ctx, key, value):
    """Store the given key/value pair."""
    dotenv_path = ctx.obj['FILE']
    quote = ctx.obj['QUOTE']
    export = ctx.obj['EXPORT']
    success, key, value = set_key(dotenv_path, key, value, quote=quote, export=export)
    if success:
        click.echo(f"{key}={value}")
    else:
        exit(1)


@cli.command()
@click.argument('key')
@click.pass_context
def get(ctx, key):
    """Retrieve the value for the given key."""
    dotenv_path = ctx.obj['FILE']
    stored_values = dotenv_values(dotenv_path)
    stored_value = stored_values.get(key)
    if stored_value:
        click.echo(f"{key}={stored_value}")
    else:
        exit(1)


@cli.command()
@click.argument('key')
@click.pass_context
def unset(ctx, key):
    """Remove the given key."""
    dotenv_path = ctx.obj['FILE']
    success, key = unset_key(dotenv_path, key)
    if success:
        click.echo(f"Successfully removed {key}")
    else:
        exit(1)


@cli.command()
@click.argument('commandline', nargs=-1, required=True)
@click.pass_context
def run(ctx, commandline):
    """Run a command with the environment variables set."""
    dotenv_path = ctx.obj['FILE']
    if not commandline:
        raise click.UsageError("Missing argument 'COMMANDLINE'")
    run_command(commandline, dotenv_path)


def run_command(commandline, dotenv_path):
    """Run a command with the dotenv file loaded into the environment."""
    env = os.environ.copy()
    if os.path.isfile(dotenv_path):
        values = dotenv_values(dotenv_path)
        env.update(values)

    cmd = list(commandline) if isinstance(commandline, (list, tuple)) else [commandline]

    try:
        proc = Popen(cmd, env=env)
        proc.communicate()
        sys.exit(proc.returncode)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
# ipython.py
"""IPython extension for dotenv magic commands."""

from IPython.core.magic import Magics, magics_class, line_magic

from .main import find_dotenv, load_dotenv


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
            %dotenv -v /path/to/.env  (verbose output)
        """
        import os

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
                print("Error: Could not find .env file")
                return

        dotenv_path = os.path.expanduser(dotenv_path)

        if not os.path.exists(dotenv_path):
            print(f"Error: Path '{dotenv_path}' does not exist")
            return

        if verbose:
            print(f"Loading .env file: {dotenv_path}")

        load_dotenv(dotenv_path, override=override, verbose=verbose)


def load_ipython_extension(ipython):
    """Register the dotenv magic command when the extension is loaded.

    Usage in IPython/Jupyter:
        %load_ext dotenv
        %dotenv
    """
    ipython.register_magics(IPythonDotEnv)
# main.py
"""main.py - DotEnv module for parsing and managing .env files."""

import os
import re
import sys
import warnings
from collections import OrderedDict
from pathlib import Path
from typing import Dict, Iterator, Optional, Tuple, Union, IO

from .parser import Binding, parse_stream
from .variables import parse_variables


def with_warn_for_invalid_lines(mappings: Iterator[Binding]) -> Iterator[Tuple[str, Optional[str]]]:
    """Filter out invalid lines and warn about them."""
    for mapping in mappings:
        if mapping.key is not None:
            yield mapping.key, mapping.value
        if mapping.error:
            warnings.warn(
                "Python-dotenv could not parse statement starting at line {}".format(
                    mapping.original.string
                ),
                UserWarning,
            )


class DotEnv:
    """Main class for handling .env files."""

    def __init__(
        self,
        dotenv_path: Optional[Union[str, Path]] = None,
        stream: Optional[IO[str]] = None,
        verbose: bool = False,
        encoding: Optional[str] = "utf-8",
        interpolate: bool = True,
        override: bool = True,
    ):
        self.dotenv_path = dotenv_path
        self.stream = stream
        self.verbose = verbose
        self.encoding = encoding
        self.interpolate = interpolate
        self.override = override
        self._dict: Optional[Dict[str, str]] = None

    def _get_stream(self) -> IO[str]:
        """Get the stream to read from."""
        if self.stream is not None:
            return self.stream
        if self.dotenv_path and os.path.isfile(self.dotenv_path):
            return open(self.dotenv_path, encoding=self.encoding)
        if self.verbose:
            warnings.warn(f"File not found: {self.dotenv_path}")
        from io import StringIO
        return StringIO("")

    def dict(self) -> Dict[str, str]:
        """Return the parsed .env file as a dictionary."""
        if self._dict is not None:
            return self._dict

        raw_values = self.parse()

        if self.interpolate:
            self._dict = resolve_variables(raw_values)
        else:
            self._dict = OrderedDict(raw_values)

        return self._dict

    def parse(self) -> Iterator[Tuple[str, Optional[str]]]:
        """Parse the .env file and yield key-value pairs."""
        stream = self._get_stream()
        try:
            for mapping in with_warn_for_invalid_lines(parse_stream(stream)):
                yield mapping
        finally:
            if self.stream is None and hasattr(stream, 'close'):
                stream.close()

    def set_as_environment_variables(self) -> bool:
        """Set the parsed values as environment variables."""
        for key, value in self.dict().items():
            if self.override or key not in os.environ:
                os.environ[key] = value
        return True

    def get(self, key: str) -> Optional[str]:
        """Get a specific key from the .env file."""
        data = self.dict()
        return data.get(key)


def get_key(dotenv_path: Union[str, Path], key_to_get: str, encoding: str = "utf-8") -> Optional[str]:
    """Get the value of a key from a .env file."""
    dotenv = DotEnv(dotenv_path=dotenv_path, encoding=encoding, interpolate=True)
    return dotenv.get(key_to_get)


def rewrite(path: Union[str, Path], encoding: str = "utf-8") -> Iterator[Tuple[str, str]]:
    """Context-manager like generator for rewriting .env files."""
    from io import StringIO

    if not os.path.isfile(path):
        with open(path, "w", encoding=encoding) as f:
            f.write("")

    with open(path, "r", encoding=encoding) as f:
        lines = f.readlines()

    output = StringIO()

    for line in lines:
        orig_line = line
        yield orig_line, output.getvalue()

    with open(path, "w", encoding=encoding) as f:
        f.write(output.getvalue())


def set_key(
    dotenv_path: Union[str, Path],
    key_to_set: str,
    value_to_set: str,
    quote_mode: str = "always",
    export: bool = False,
    encoding: str = "utf-8",
) -> Tuple[Optional[bool], str, str]:
    """Set a key-value pair in the .env file."""
    dotenv_path = Path(dotenv_path)

    if not dotenv_path.exists():
        dotenv_path.parent.mkdir(parents=True, exist_ok=True)
        dotenv_path.touch()

    if quote_mode == "always":
        value_out = f'"{value_to_set}"'
    elif quote_mode == "never":
        value_out = value_to_set
    else:
        value_out = f'"{value_to_set}"'

    if export:
        line_out = f"export {key_to_set}={value_out}\n"
    else:
        line_out = f"{key_to_set}={value_out}\n"

    with open(dotenv_path, "r", encoding=encoding) as f:
        lines = f.readlines()

    key_found = False
    new_lines = []
    key_pattern = re.compile(
        rf"^(export\s+)?{re.escape(key_to_set)}\s*[=:]"
    )

    for line in lines:
        if key_pattern.match(line.strip()):
            new_lines.append(line_out)
            key_found = True
        else:
            new_lines.append(line)

    if not key_found:
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines.append("\n")
        new_lines.append(line_out)

    with open(dotenv_path, "w", encoding=encoding) as f:
        f.writelines(new_lines)

    return True, key_to_set, value_to_set


def unset_key(
    dotenv_path: Union[str, Path],
    key_to_unset: str,
    quote_mode: str = "always",
    encoding: str = "utf-8",
) -> Tuple[Optional[bool], str]:
    """Remove a key from the .env file."""
    dotenv_path = Path(dotenv_path)

    if not dotenv_path.exists():
        warnings.warn(f"Can't delete from {dotenv_path} - it doesn't exist.")
        return None, key_to_unset

    with open(dotenv_path, "r", encoding=encoding) as f:
        lines = f.readlines()

    key_pattern = re.compile(
        rf"^(export\s+)?{re.escape(key_to_unset)}\s*[=:]"
    )

    new_lines = [line for line in lines if not key_pattern.match(line.strip())]

    with open(dotenv_path, "w", encoding=encoding) as f:
        f.writelines(new_lines)

    return True, key_to_unset


def resolve_variables(
    values: Iterator[Tuple[str, Optional[str]]],
    override: bool = False,
) -> Dict[str, str]:
    """Resolve variable interpolation in values."""
    new_values: Dict[str, str] = OrderedDict()

    for key, value in values:
        if key is None:
            continue
        if value is None:
            new_values[key] = ""
            continue

        atoms = parse_variables(value)
        new_values[key] = "".join(
            atom.resolve(new_values, os.environ) for atom in atoms
        )

    return new_values


def find_dotenv(
    filename: str = ".env",
    raise_error_if_not_found: bool = False,
    usecwd: bool = False,
) -> str:
    """Search for a .env file by walking up directories."""
    if usecwd:
        start = os.getcwd()
    else:
        frame = sys._getframe(1)
        caller_dir = os.path.dirname(os.path.abspath(frame.f_code.co_filename))
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
        raise IOError(f"File not found: {filename}")

    return ""


def load_dotenv(
    dotenv_path: Optional[Union[str, Path]] = None,
    stream: Optional[IO[str]] = None,
    verbose: bool = False,
    interpolate: bool = True,
    override: bool = False,
    encoding: Optional[str] = "utf-8",
) -> bool:
    """Load a .env file and set environment variables."""
    if dotenv_path is None and stream is None:
        dotenv_path = find_dotenv()

    dotenv = DotEnv(
        dotenv_path=dotenv_path,
        stream=stream,
        verbose=verbose,
        interpolate=interpolate,
        override=override,
        encoding=encoding,
    )
    return dotenv.set_as_environment_variables()


def dotenv_values(
    dotenv_path: Optional[Union[str, Path]] = None,
    stream: Optional[IO[str]] = None,
    verbose: bool = False,
    interpolate: bool = True,
    encoding: Optional[str] = "utf-8",
) -> Dict[str, str]:
    """Parse a .env file and return values as a dictionary without modifying the environment."""
    if dotenv_path is None and stream is None:
        dotenv_path = find_dotenv()

    dotenv = DotEnv(
        dotenv_path=dotenv_path,
        stream=stream,
        verbose=verbose,
        interpolate=interpolate,
        override=True,
        encoding=encoding,
    )
    return dotenv.dict()
# parser.py
# parser.py

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
    def __init__(self, chars: str, line: int):
        self.chars = chars
        self.line = line
        self.index = 0

    def start(self) -> 'Position':
        self.index = 0
        return self

    def set(self, index: int) -> None:
        self.index = index

    def advance(self, count: int) -> None:
        self.index += count


class Error(Exception):
    pass


class Reader:
    def __init__(self, chars: str, line: int = 1):
        self.chars = chars
        self.line = line
        self.pos = 0
        self.mark = 0

    def has_next(self) -> bool:
        return self.pos < len(self.chars)

    def set_mark(self) -> None:
        self.mark = self.pos

    def get_marked(self) -> str:
        return self.chars[self.mark:self.pos]

    def peek(self, count: int = 1) -> str:
        return self.chars[self.pos:self.pos + count]

    def read(self, count: int = 1) -> str:
        result = self.chars[self.pos:self.pos + count]
        self.pos += count
        return result

    def read_regex(self, regex: Pattern[str]) -> str:
        match = regex.match(self.chars, self.pos)
        if match:
            self.pos = match.end()
            return match.group()
        return ""


def make_regex(pattern: str) -> Pattern[str]:
    return re.compile(pattern)


def decode_escapes(s: str) -> str:
    return codecs.decode(s, 'unicode_escape')


_key_pattern = make_regex(r"[A-Za-z_][A-Za-z0-9_.]*")
_unquoted_value_pattern = make_regex(r"[^\s#]*")
_single_quoted_pattern = make_regex(r"'([^']*)'")
_double_quoted_pattern = make_regex(r'"([^"]*)"')
_export_pattern = make_regex(r"export\s+")
_whitespace_pattern = make_regex(r"\s*")
_comment_pattern = make_regex(r"#[^\n]*")


def parse_key(reader: Reader) -> str:
    # Handle quoted keys
    if reader.has_next() and reader.peek() == "'":
        match = _single_quoted_pattern.match(reader.chars, reader.pos)
        if match:
            reader.pos = match.end()
            return match.group(1)
        raise Error("Invalid single-quoted key")
    if reader.has_next() and reader.peek() == '"':
        match = _double_quoted_pattern.match(reader.chars, reader.pos)
        if match:
            reader.pos = match.end()
            return match.group(1)
        raise Error("Invalid double-quoted key")
    # Unquoted key
    key = reader.read_regex(_key_pattern)
    if not key:
        raise Error("Expected key")
    return key


def parse_unquoted_value(reader: Reader) -> str:
    value = reader.read_regex(_unquoted_value_pattern)
    return value.strip()


def parse_value(reader: Reader) -> str:
    if not reader.has_next():
        return ""
    ch = reader.peek()
    if ch == "'":
        match = _single_quoted_pattern.match(reader.chars, reader.pos)
        if match:
            reader.pos = match.end()
            return match.group(1)
        raise Error("Invalid single-quoted value")
    if ch == '"':
        match = _double_quoted_pattern.match(reader.chars, reader.pos)
        if match:
            reader.pos = match.end()
            return decode_escapes(match.group(1))
        raise Error("Invalid double-quoted value")
    return parse_unquoted_value(reader)


def parse_binding(line: str, line_number: int) -> Binding:
    original = Original(string=line, line=line_number)
    reader = Reader(line.strip())

    try:
        # Skip export prefix
        reader.read_regex(_export_pattern)

        if not reader.has_next():
            raise Error("Empty binding")

        key = parse_key(reader)

        # Skip whitespace around =
        reader.read_regex(_whitespace_pattern)
        if not reader.has_next() or reader.peek() != '=':
            raise Error("Expected '='")
        reader.read(1)  # consume '='
        reader.read_regex(_whitespace_pattern)

        value = parse_value(reader)

        return Binding(key=key, value=value, original=original, error=False)
    except Error:
        return Binding(key="", value="", original=original, error=True)


def parse_stream(stream: IO[str]) -> Iterator[Binding]:
    for line_number, line in enumerate(stream, start=1):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        yield parse_binding(line, line_number)

# variables.py
"""variables.py - Parse variable expressions with literal and variable atoms."""

from __future__ import annotations

import re
from typing import Optional


class Atom:
    """Base class for atoms in a variable expression."""

    def resolve(self, env: dict[str, str]) -> str:
        raise NotImplementedError


class Literal(Atom):
    """A literal string atom."""

    def __init__(self, value: str):
        self.value = value

    def resolve(self, env: dict[str, str]) -> str:
        return self.value

    def __eq__(self, other):
        if not isinstance(other, Literal):
            return NotImplemented
        return self.value == other.value

    def __repr__(self):
        return f"Literal(value={self.value!r})"


class Variable(Atom):
    """A variable reference atom with optional default."""

    def __init__(self, name: str, default: Optional[str] = None):
        self.name = name
        self.default = default

    def resolve(self, env: dict[str, str]) -> str:
        value = env.get(self.name)
        if value is not None:
            return value
        if self.default is not None:
            return self.default
        return ""

    def __eq__(self, other):
        if not isinstance(other, Variable):
            return NotImplemented
        return self.name == other.name and self.default == other.default

    def __repr__(self):
        return f"Variable(name={self.name!r}, default={self.default!r})"


def parse_variables(text: str) -> list[Atom]:
    """Parse a string into a list of Literal and Variable atoms.

    Supports ${name} and ${name:-default} syntax.
    """
    atoms: list[Atom] = []
    if not text:
        return atoms

    pattern = re.compile(r'\$\{([^}]*)\}')
    pos = 0

    for match in pattern.finditer(text):
        start = match.start()
        if start > pos:
            atoms.append(Literal(value=text[pos:start]))

        content = match.group(1)
        if ":-" in content:
            name, default = content.split(":-", 1)
            atoms.append(Variable(name=name, default=default))
        else:
            atoms.append(Variable(name=content, default=None))

        pos = match.end()

    if pos < len(text):
        atoms.append(Literal(value=text[pos:]))

    return atoms

# version.py
"""Version management module for tracking and comparing software versions."""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Tuple


class ReleaseType(Enum):
    """Enumeration of release types."""
    ALPHA = "alpha"
    BETA = "beta"
    RC = "rc"
    RELEASE = "release"


@dataclass(order=False)
class Version:
    """Represents a semantic version with optional pre-release and build metadata."""
    
    major: int = 0
    minor: int = 0
    patch: int = 0
    pre_release: Optional[str] = None
    build_metadata: Optional[str] = None
    release_type: ReleaseType = field(default=ReleaseType.RELEASE)

    _PATTERN = re.compile(
        r"^v?(?P<major>\d+)"
        r"(\.(?P<minor>\d+))?"
        r"(\.(?P<patch>\d+))?"
        r"(-(?P<pre_release>[a-zA-Z0-9.]+))?"
        r"(\+(?P<build_metadata>[a-zA-Z0-9.]+))?$"
    )

    def __post_init__(self):
        if self.major < 0 or self.minor < 0 or self.patch < 0:
            raise ValueError("Version components must be non-negative integers")
        if self.pre_release:
            self.release_type = self._determine_release_type(self.pre_release)

    def _determine_release_type(self, pre_release: str) -> ReleaseType:
        lower = pre_release.lower()
        if lower.startswith("alpha"):
            return ReleaseType.ALPHA
        elif lower.startswith("beta"):
            return ReleaseType.BETA
        elif lower.startswith("rc"):
            return ReleaseType.RC
        return ReleaseType.RELEASE

    @classmethod
    def parse(cls, version_string: str) -> "Version":
        """Parse a version string into a Version object."""
        match = cls._PATTERN.match(version_string.strip())
        if not match:
            raise ValueError(f"Invalid version string: '{version_string}'")
        
        groups = match.groupdict()
        return cls(
            major=int(groups["major"]),
            minor=int(groups["minor"]) if groups["minor"] else 0,
            patch=int(groups["patch"]) if groups["patch"] else 0,
            pre_release=groups.get("pre_release"),
            build_metadata=groups.get("build_metadata"),
        )

    @property
    def tuple(self) -> Tuple[int, int, int]:
        """Return version as a tuple of (major, minor, patch)."""
        return (self.major, self.minor, self.patch)

    @property
    def is_stable(self) -> bool:
        """Check if this is a stable release (no pre-release tag)."""
        return self.pre_release is None and self.major > 0

    @property
    def is_pre_release(self) -> bool:
        """Check if this version has a pre-release identifier."""
        return self.pre_release is not None

    def bump_major(self) -> "Version":
        """Return a new Version with major incremented, minor and patch reset."""
        return Version(major=self.major + 1, minor=0, patch=0)

    def bump_minor(self) -> "Version":
        """Return a new Version with minor incremented, patch reset."""
        return Version(major=self.major, minor=self.minor + 1, patch=0)

    def bump_patch(self) -> "Version":
        """Return a new Version with patch incremented."""
        return Version(major=self.major, minor=self.minor, patch=self.patch + 1)

    def with_pre_release(self, pre_release: str) -> "Version":
        """Return a new Version with the given pre-release identifier."""
        return Version(
            major=self.major,
            minor=self.minor,
            patch=self.patch,
            pre_release=pre_release,
            build_metadata=self.build_metadata,
        )

    def with_build_metadata(self, build_metadata: str) -> "Version":
        """Return a new Version with the given build metadata."""
        return Version(
            major=self.major,
            minor=self.minor,
            patch=self.patch,
            pre_release=self.pre_release,
            build_metadata=build_metadata,
        )

    def _pre_release_priority(self) -> int:
        """Return numeric priority for release type ordering."""
        priority_map = {
            ReleaseType.ALPHA: 0,
            ReleaseType.BETA: 1,
            ReleaseType.RC: 2,
            ReleaseType.RELEASE: 3,
        }
        return priority_map[self.release_type]

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return (
            self.major == other.major
            and self.minor == other.minor
            and self.patch == other.patch
            and self.pre_release == other.pre_release
        )

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        if self.tuple != other.tuple:
            return self.tuple < other.tuple
        # A version without pre-release has higher precedence
        if self.pre_release is None and other.pre_release is None:
            return False
        if self.pre_release is None:
            return False
        if other.pre_release is None:
            return True
        return self._pre_release_priority() < other._pre_release_priority()

    def __le__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return self == other or self < other

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return not self <= other

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return not self < other

    def __hash__(self) -> int:
        return hash((self.major, self.minor, self.patch, self.pre_release))

    def __str__(self) -> str:
        version_str = f"{self.major}.{self.minor}.{self.patch}"
        if self.pre_release:
            version_str += f"-{self.pre_release}"
        if self.build_metadata:
            version_str += f"+{self.build_metadata}"
        return version_str

    def __repr__(self) -> str:
        return (
            f"Version(major={self.major}, minor={self.minor}, patch={self.patch}, "
            f"pre_release={self.pre_release!r}, build_metadata={self.build_metadata!r})"
        )


class VersionRange:
    """Represents a range of acceptable versions."""

    def __init__(self, min_version: Optional[Version] = None, max_version: Optional[Version] = None,
                 include_min: bool = True, include_max: bool = False):
        self.min_version = min_version
        self.max_version = max_version
        self.include_min = include_min
        self.include_max = include_max

        if min_version and max_version and min_version > max_version:
            raise ValueError("min_version cannot be greater than max_version")

    def contains(self, version: Version) -> bool:
        """Check if a version falls within this range."""
        if self.min_version:
            if self.include_min and version < self.min_version:
                return False
            if not self.include_min and version <= self.min_version:
                return False

        if self.max_version:
            if self.include_max and version > self.max_version:
                return False
            if not self.include_max and version >= self.max_version:
                return False

        return True

    def __contains__(self, version: Version) -> bool:
        return self.contains(version)

    def __str__(self) -> str:
        left = "[" if self.include_min else "("
        right = "]" if self.include_max else ")"
        min_str = str(self.min_version) if self.min_version else "*"
        max_str = str(self.max_version) if self.max_version else "*"
        return f"{left}{min_str}, {max_str}{right}"

    def __repr__(self) -> str:
        return (
            f"VersionRange(min_version={self.min_version!r}, max_version={self.max_version!r}, "
            f"include_min={self.include_min}, include_max={self.include_max})"
        )


def is_compatible(current: Version, required: Version) -> bool:
    """Check if current version is compatible with required version (same major, >= minor)."""
    if current.major != required.major:
        return False
    if current.major == 0:
        # For 0.x.y, minor version changes are breaking
        return current.minor == required.minor and current.patch >= required.patch
    return current >= required


def get_latest(versions: list) -> Optional[Version]:
    """Return the latest (highest) version from a list of versions."""
    if not versions:
        return None
    return max(versions)


def get_latest_stable(versions: list) -> Optional[Version]:
    """Return the latest stable version from a list."""
    stable_versions = [v for v in versions if v.is_stable]
    if not stable_versions:
        return None
    return max(stable_versions)


def sort_versions(versions: list, reverse: bool = False) -> list:
    """Sort a list of versions."""
    return sorted(versions, reverse=reverse)


# Module-level version info
__version__ = "1.0.0"
__version_info__ = Version.parse(__version__)
# __init__.py
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
from .main import DotEnv
from .parser import Binding, parse_stream
from .variables import Literal, Variable, parse_variables

__all__ = [
    "dotenv_values",
    "find_dotenv",
    "get_key",
    "load_dotenv",
    "set_key",
    "unset_key",
    "DotEnv",
    "Binding",
    "parse_stream",
    "Literal",
    "Variable",
    "parse_variables",
]

# is_interactive.py
# is_interactive.py
"""is_interactive.py - Determine if the current environment is interactive."""

import os
import sys


def is_interactive():
    """Check if the current session is interactive.

    Returns True if:
    - stdin is connected to a terminal (TTY)
    - Running in an IPython/Jupyter session
    - The TERM environment variable is set and stdin is a TTY

    Returns False if:
    - stdin is not a TTY (e.g., piped input)
    - Running in a non-interactive script
    - stdin is None (e.g., pythonw on Windows)
    """
    try:
        # Check if stdin exists and is a TTY
        if sys.stdin is None:
            return False
        if hasattr(sys.stdin, 'isatty') and sys.stdin.isatty():
            return True
    except ValueError:
        # stdin might be closed
        return False

    # Check for IPython/Jupyter environment
    try:
        from IPython import get_ipython
        if get_ipython() is not None:
            return True
    except (ImportError, NameError):
        pass

    # Check for interactive Python shell
    if hasattr(sys, 'ps1'):
        return True

    return False

# zip_imports.py
# zip_imports.py
"""zip_imports.py - Handle dotenv loading when running from zip imports."""

import os
import sys
from pathlib import Path


def _is_zip_path(path: str) -> bool:
    """Check if a path appears to be inside a zip archive."""
    zip_extensions = ('.zip', '.egg', '.whl')
    path_lower = path.lower()
    for ext in zip_extensions:
        if ext in path_lower:
            # Check if the zip extension appears as part of the path
            idx = path_lower.find(ext)
            # Verify it's followed by a path separator or end of string
            end_idx = idx + len(ext)
            if end_idx == len(path) or path[end_idx] in (os.sep, os.altsep, '/'):
                return True
    return False


def _find_dotenv_from_zip(filename: str = ".env", usecwd: bool = False) -> str:
    """Find a .env file when running from a zip import.

    When the caller is inside a zip archive, fall back to using
    the current working directory as the starting point for the search.
    """
    if usecwd:
        start = os.getcwd()
    else:
        # Try to determine caller's directory
        try:
            frame = sys._getframe(2)  # Go up two frames (caller of caller)
            caller_file = frame.f_code.co_filename
            if _is_zip_path(caller_file):
                # Fall back to cwd when inside a zip
                start = os.getcwd()
            else:
                start = os.path.dirname(os.path.abspath(caller_file))
        except (ValueError, AttributeError):
            start = os.getcwd()

    current = start
    while True:
        check_path = os.path.join(current, filename)
        if os.path.isfile(check_path):
            return check_path

        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent

    return ""


def load_dotenv_gracefully(
    dotenv_path=None,
    stream=None,
    verbose=False,
    interpolate=True,
    override=False,
    encoding="utf-8",
):
    """Load dotenv gracefully handling zip imports.

    When running from within a zip archive (e.g., a .pyz file or zipapp),
    this function handles the case where the .env file cannot be found
    by the normal directory traversal mechanism, returning False instead
    of raising an error.
    """
    from .main import load_dotenv, find_dotenv, DotEnv

    try:
        if dotenv_path is None and stream is None:
            # Check if we're in a zip context
            try:
                frame = sys._getframe(1)
                caller_file = frame.f_code.co_filename
                if _is_zip_path(caller_file):
                    # Try to find .env from cwd instead
                    dotenv_path = _find_dotenv_from_zip(usecwd=True)
                    if not dotenv_path:
                        # No .env file found, return gracefully
                        return False
            except (ValueError, AttributeError):
                pass

        return load_dotenv(
            dotenv_path=dotenv_path,
            stream=stream,
            verbose=verbose,
            interpolate=interpolate,
            override=override,
            encoding=encoding,
        )
    except (IOError, OSError):
        # Gracefully handle cases where the env file can't be read
        return False
