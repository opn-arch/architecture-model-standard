# src/dotenv/cli.py
from typing import Any, Dict, List, Optional

import dotenv_values
from .main import set_key, unset_key
from .version import __version__

def enumerate_env() -> None:
    """Enumerate all environment variables."""
    for key in os.environ.keys():
        print(key)

def cli() -> None:
    """Main command line interface function."""
    print("Python-dotenv CLI")

def stream_file(filename: str) -> Dict[str, Any]:
    """
    Stream the contents of a file.

    Args:
        filename (str): The path to the file.

    Returns:
        Dict[str, Any]: A dictionary with key-value pairs from the file.
    """
    return dotenv_values(filename)

def list_values() -> List[str]:
    """List all keys in the environment."""
    return os.environ.keys()

def set_value(key: str, value: str) -> None:
    """
    Set a key in the environment.

    Args:
        key (str): The key to set.
        value (str): The value to assign to the key.
    """
    os.environ[key] = value

def get(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Get a value from the environment.

    Args:
        key (str): The key to retrieve.
        default (Optional[str]): Default value if key is not found.

    Returns:
        Optional[str]: The value of the key or the default value.
    """
    return os.environ.get(key, default)

def unset(key: str) -> None:
    """
    Unset a key in the environment.

    Args:
        key (str): The key to remove.
    """
    del os.environ[key]

def run_command(command: str) -> int:
    """
    Run a command and return its exit status.

    Args:
        command (str): The command to execute.

    Returns:
        int: Exit status of the command.
    """
    return os.system(command)

def run() -> None:
    """Run the CLI application."""
    print("Running Python-dotenv CLI")

# src/dotenv/ipython.py
from typing import Any

import IPython

def load_ipython_extension(ip: IPython.core.extensions.ExtensionManager) -> None:
    """
    Load IPython extension.

    Args:
        ip (IPython.core.extensions.ExtensionManager): The IPython extension manager.
    """
    pass  # Placeholder implementation

# src/dotenv/main.py
from typing import Any, Dict, List, Optional

import os
from .parser import Binding, parse_stream
from .variables import Atom, parse_variables

def with_warn_for_invalid_lines() -> bool:
    """Return whether to warn for invalid lines."""
    return True

def get_key(dotenv: str) -> Dict[str, Any]:
    """
    Get key-value pairs from a dotenv file.

    Args:
        dotenv (str): The path to the .env file.

    Returns:
        Dict[str, Any]: Key-value pairs from the .env file.
    """
    return parse_stream(dotenv)

def rewrite() -> None:
    """Rewrite the environment with new values."""
    pass  # Placeholder implementation

def set_key(key: str, value: str) -> None:
    """
    Set a key in the environment.

    Args:
        key (str): The key to set.
        value (str): The value to assign to the key.
    """
    os.environ[key] = value

def unset_key(key: str) -> None:
    """
    Unset a key in the environment.

    Args:
        key (str): The key to remove.
    """
    del os.environ[key]

def resolve_variables(values: Dict[str, Any]) -> Dict[str, Any]:
    """
    Resolve variables in the given values dictionary.

    Args:
        values (Dict[str, Any]): Dictionary of values to resolve.

    Returns:
        Dict[str, Any]: Resolved dictionary.
    """
    return {k: v.resolve() if isinstance(v, Atom) else v for k, v in values.items()}

def find_dotenv() -> str:
    """Find the .env file."""
    return os.path.expanduser("~/.env")

def load_dotenv(filename: Optional[str] = None) -> Dict[str, Any]:
    """
    Load environment variables from a .env file.

    Args:
        filename (Optional[str]): The path to the .env file. Defaults to "~/.env".

    Returns:
        Dict[str, Any]: Key-value pairs from the .env file.
    """
    return parse_stream(filename or "~/.env")

def dotenv_values(filename: str) -> Dict[str, Optional[str]]:
    """
    Load environment variables from a file.

    Args:
        filename (str): The path to the file.

    Returns:
        Dict[str, Optional[str]]: Key-value pairs from the file.
    """
    return parse_variables(filename)

# src/dotenv/parser.py
from typing import Any, Dict, List

import os
from .variables import Atom, Binding

class Position:
    def __init__(self, line_no: int = 0) -> None:
        self.line_no = line_no

    def start(self) -> int:
        """Return the starting position."""
        return self.line_no

    def set(self, new_line_no: int) -> None:
        """Set the current position."""
        self.line_no = new_line_no

    def advance(self) -> None:
        """Advance the line number."""
        self.line_no += 1

class Error(Exception):
    pass

class Reader:
    def __init__(self, data: str) -> None:
        self.data = data
        self.mark = 0

    def has_next(self) -> bool:
        """Return whether there is more data to read."""
        return self.mark < len(self.data)

    def set_mark(self) -> int:
        """Set a mark for later use."""
        return self.mark

    def get_marked(self, mark: int) -> str:
        """Get the text marked at a given position."""
        return self.data[:mark]

    def peek(self) -> Optional[str]:
        """Peek at the next character without advancing."""
        if self.has_next():
            return self.data[self.mark]
        return None

    def read(self, n: int) -> str:
        """
        Read 'n' characters.

        Args:
            n (int): Number of characters to read.

        Returns:
            str: The read text.
        """
        result = self.data[self.mark:self.mark + n]
        self.mark += n
        return result

    def read_regex(self, regex: Any) -> Optional[str]:
        """
        Read until a regex pattern matches.

        Args:
            regex (Any): Regex pattern to match.

        Returns:
            str or None: The matched text or None if no match.
        """
        try:
            match = re.search(regex, self.data[self.mark:])
            if match:
                result = match.group(0)
                self.mark += len(result)
                return result
            return None
        except Exception as e:
            raise Error(f"Error while reading: {e}")

def make_regex(pattern: str) -> Any:
    """Compile a regex pattern."""
    return re.compile(pattern)

def decode_escapes(text: str) -> str:
    """Decode escape sequences in the given text."""
    return text.encode().decode('unicode_escape')

def parse_key(reader: Reader) -> Dict[str, str]:
    """
    Parse a key from the reader.

    Args:
        reader (Reader): The reader to read from.

    Returns:
        Dict[str, str]: A dictionary with the parsed key.
    """
    result = {}
    while True:
        line = reader.read_until('\n')
        if not line.strip():
            break
        k, v = line.split('=', 1)
        result[k] = v
    return result

def parse_unquoted_value(reader: Reader) -> str:
    """Parse an unquoted value from the reader."""
    return reader.read_until('=')

def parse_value(reader: Reader) -> Any:
    """
    Parse a value from the reader.

    Args:
        reader (Reader): The reader to read from.

    Returns:
        Any: The parsed value.
    """
    char = reader.peek()
    if not char or char.isspace():
        return None
    elif char == '"':
        return decode_escapes(reader.read_until('"'))
    else:
        return parse_unquoted_value(reader)

def parse_binding(reader: Reader) -> Binding:
    """
    Parse a binding from the reader.

    Args:
        reader (Reader): The reader to read from.

    Returns:
        Binding: The parsed binding.
    """
    result = {}
    while True:
        line = reader.read_until('\n')
        if not line.strip():
            break
        k, v = line.split('=', 1)
        result[k] = v
    return Binding(result)

def parse_stream(filename: str) -> Dict[str, Any]:
    """
    Parse the contents of a file and return key-value pairs.

    Args:
        filename (str): The path to the file.

    Returns:
        Dict[str, Any]: Key-value pairs from the file.
    """
    with open(filename, 'r') as f:
        data = f.read()
    reader = Reader(data)
    result = {}
    while reader.has_next():
        line = reader.read_until('\n')
        if not line.strip():
            continue
        k, v = line.split('=', 1)
        result[k] = v
    return result

# src/dotenv/variables.py
from typing import Any

import re
from .parser import Binding

class Atom:
    def resolve(self) -> Any:
        """Resolve the atom."""
        raise NotImplementedError("Subclasses must implement resolve")

class Literal(Atom):
    def __init__(self, value: str) -> None:
        self.value = value

    def resolve(self) -> str:
        return self.value

class Variable(Atom):
    def __init__(self, name: str) -> None:
        self.name = name

    def resolve(self) -> Any:
        """Resolve the variable."""
        raise NotImplementedError("Subclasses must implement resolve")

def parse_variables(filename: str) -> Dict[str, Any]:
    """
    Parse variables from a file.

    Args:
        filename (str): The path to the file.

    Returns:
        Dict[str, Any]: Key-value pairs of parsed variables.
    """
    with open(filename, 'r') as f:
        data = f.read()
    reader = Reader(data)
    result = {}
    while reader.has_next():
        binding = parse_binding(reader)
        for k, v in binding.items():
            result[k] = v
    return result

# src/dotenv/version.py
from typing import Any

def __version__() -> str:
    """Return the version of Python-dotenv."""
    return "1.0.0"
# __init__.py
from dotenv.parser import Binding

class DotEnv:
    def __init__(self, filename=None):
        self.filename = filename
        self.variables = {}

    def dict(self):
        return self.variables

    def parse(self, stream):
        for binding in parse_stream(stream):
            key = binding.key
            value = binding.value
            self.variables[key] = value

    def set_as_environment_variables(self):
        for key, value in self.variables.items():
            import os
            os.environ[key] = value

    def get(self, key, default=None):
        return self.variables.get(key, default)

    def rewrite(self, filename):
        with open(filename, 'w') as f:
            for key, value in self.variables.items():
                f.write(f'{key}={value}\n')

    def dotenv_values(self):
        return self.dict()
# src/dotenv/__init__.py

from .main import DotEnv, dotenv_values, load_dotenv, with_warn_for_invalid_lines
from .version import __version__

# zip_imports.py
from dotenv import load_dotenv, find_dotenv, dotenv_values

def test_load_dotenv_gracefully_handles_zip_imports_when_no_env_file():
    # Simulate a zip file that does not contain an env file
    from unittest.mock import MagicMock

    mock_open = MagicMock()
    mock_open.return_value.__enter__.return_value.read = lambda: ""
    with patch("zipfile.ZipFile", return_value=mock_open):
        assert load_dotenv(find_dotenv(follow_symlinks=False)) is False

# Ensure the test passes by verifying that load_dotenv returns False when no env file is found
# src/dotenv/cli.py
from typing import Any, Dict, List, Optional

import dotenv_values
from .main import set_key, unset_key
from .version import __version__

def enumerate_env() -> None:
    """Enumerate all environment variables."""
    for key in os.environ.keys():
        print(key)

def cli() -> None:
    """Main command line interface function."""
    print("Python-dotenv CLI")

def stream_file(filename: str) -> Dict[str, Any]:
    """
    Stream the contents of a file.

    Args:
        filename (str): The path to the file.

    Returns:
        Dict[str, Any]: A dictionary with key-value pairs from the file.
    """
    return dotenv_values(filename)

def list_values() -> List[str]:
    """List all keys in the environment."""
    return os.environ.keys()

def set_value(key: str, value: str) -> None:
    """
    Set a key in the environment.

    Args:
        key (str): The key to set.
        value (str): The value to assign to the key.
    """
    os.environ[key] = value

def get(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Get a value from the environment.

    Args:
        key (str): The key to retrieve.
        default (Optional[str]): Default value if key is not found.

    Returns:
        Optional[str]: The value of the key or the default value.
    """
    return os.environ.get(key, default)

def unset(key: str) -> None:
    """
    Unset a key in the environment.

    Args:
        key (str): The key to remove.
    """
    del os.environ[key]

def run_command(command: str) -> int:
    """
    Run a command and return its exit status.

    Args:
        command (str): The command to execute.

    Returns:
        int: Exit status of the command.
    """
    return os.system(command)

def run() -> None:
    """Run the CLI application."""
    print("Running Python-dotenv CLI")
