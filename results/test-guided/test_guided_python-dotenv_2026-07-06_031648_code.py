# component_cli.py

from typing import Any, Dict, Optional

def cli():
    pass

def enumerate_env() -> Dict[str, str]:
    return {}

def get(key: str) -> Optional[str]:
    return None

def list_values() -> Dict[str, str]:
    return {}

def run(*args: Any) -> Any:
    pass


# component_ipython.py

from IPython.core.magic import Magics
from typing import Any

class IPythonDotEnv(Magics):
    def dotenv(self):
        pass


def load_ipython_extension(ipython):
    pass


# component_main.py

from .parser import Binding, parse_stream
from .variables import Literal, Variable, parse_variables
from typing import Dict, Optional, Union

class DotEnv:
    def __init__(self, file_path: str = None) -> None:
        self.file_path = file_path
        self.cache = {}

    def dict(self) -> Dict[str, Optional[str]]:
        if not self.file_path:
            return {}
        return self._load_file()

    def get(self, key: str) -> Optional[str]:
        try:
            return self.dict()[key]
        except KeyError:
            return None

    def parse(self, stream: Any) -> Dict[str, Binding]:
        return parse_stream(stream)

    def resolve_variables(self, text: str) -> str:
        pass  # Implement based on usage in tests


def dotenv_values(filename: str = ".env") -> Dict[str, Optional[str]]:
    env_file = find_dotenv(filename)
    with open(env_file) as f:
        return parse_stream(f)

def find_dotenv(filename: str = ".env", usecwd: bool = False) -> str:
    pass  # Implement based on usage in tests

def get_key(key: str, default: Optional[str] = None) -> Optional[str]:
    try:
        return dict()[key]
    except KeyError:
        return default

def load_dotenv(filename: str = ".env", override: bool = False) -> Dict[str, Optional[str]]:
    pass  # Implement based on usage in tests

def resolve_variables(text: str) -> str:
    pass  # Implement based on usage in tests


# component_parser.py

from typing import Any, Dict, Iterator, List, Optional, Union
import re

class Position:
    def __init__(self, line: int = 1, column: int = 1) -> None:
        self.line = line
        self.column = column

    def start(self):
        return (self.line, self.column)

    def set(self, line: int, column: int) -> None:
        self.line = line
        self.column = column

    def advance(self) -> None:
        self.column += 1


class Reader:
    def __init__(self, stream: Any) -> None:
        self.stream = stream
        self.position = Position()

    def get_marked(self, offset: int) -> str:
        pass  # Implement based on usage in tests

    def has_next(self) -> bool:
        return hasattr(self.stream, '__next__') and next(self.stream, None) is not None

    def peek(self, n: int = 1) -> Any:
        if self.has_next():
            return next(iter(self.stream), None)
        else:
            return None


def decode_escapes(text: str) -> str:
    pass  # Implement based on usage in tests

def make_regex(pattern: str) -> re.Pattern:
    return re.compile(pattern)

def parse_binding(stream: Any, position: Position) -> Dict[str, Binding]:
    pass  # Implement based on usage in tests

def parse_key(stream: Any, position: Position) -> Optional[str]:
    pass  # Implement based on usage in tests

def parse_stream(stream: Any) -> Dict[str, Binding]:
    return {key: Binding() for key in stream}  # Placeholder implementation


# component_variables.py

from typing import Protocol
import re

class Atom(Protocol):
    def resolve(self) -> str:
        pass  # Implement based on usage in tests

class Literal:
    def __init__(self, value: Any) -> None:
        self.value = value

    def resolve(self) -> str:
        return str(self.value)

class Variable:
    def __init__(self, name: str) -> None:
        self.name = name

    def resolve(self) -> Optional[str]:
        pass  # Implement based on usage in tests


def parse_variables(stream: Any) -> Dict[str, Atom]:
    return {name: Literal(name) for name in stream}  # Placeholder implementation


# component_version.py

from typing import Any
__version__: str = "0.18.2"  # Hardcoded version number


# component_conftest.py

import pytest

def cli():
    pass

def dotenv_path() -> str:
    return ".env"

def run_dotenv(*args: Any) -> Any:
    pass  # Implement based on usage in tests

def check_process(process):
    assert process.returncode == 0


# component_test_cli.py

from .cli import cli, get
import pytest

def test_get_default_path():
    assert get("DEFAULT_PATH") is None

def test_get_existing_value():
    assert get("EXISTING_KEY") == "existing_value"

def test_get_non_existent_file():
    with pytest.raises(FileNotFoundError):
        get("NON_EXISTENT_FILE")

def test_get_non_existent_value():
    assert get("NON_EXISTENT_VALUE") is None

def test_get_not_a_file():
    with pytest.raises(IsADirectoryError):
        get("NOT_A_FILE")


# component_test_fifo_dotenv.py

from .test_cli import run_dotenv
import pytest

def test_load_dotenv_from_fifo():
    pass  # Implement based on usage in tests


# component_test_ipython.py

from .ipython import IPythonDotEnv, load_ipython_extension
import pytest

def test_ipython_existing_variable_no_override():
    ip = IPythonDotEnv()
    with pytest.raises(KeyError):
        ip.getenv("EXISTS", "default")

def test_ipython_existing_variable_override():
    ip = IPythonDotEnv()
    result = ip.getenv("EXISTS", "override")
    assert result == "override"

def test_ipython_new_variable():
    pass  # Implement based on usage in tests


# component_test_is_interactive.py

from .main import find_dotenv
import pytest
from pathlib import Path

class TestIsInteractive:
    def test_is_interactive_main_module_not_found(self):
        assert not is_interactive()

    def test_is_interactive_main_module_with_file_attribute_none(self):
        assert not is_interactive()

    def test_is_interactive_main_with_file(self):
        assert find_dotenv() == Path(".env")

    def test_is_interactive_main_without_file(self):
        pass  # Implement based on usage in tests


# component_test_lib.py

from .main import dotenv_values, load_dotenv
import pytest
from pathlib import Path

def run_dotenv():
    pass  # Implement based on usage in tests

def check_process(process):
    assert process.returncode == 0


# component_test_parser.py

from .parser import parse_stream
import pytest

def test_parse_stream():
    stream = ["KEY=value"]
    result = parse_stream(stream)
    assert result == {"KEY": Binding("value")}


# component_test_utils.py

from typing import Any

def to_cli_string(obj: Any) -> str:
    return repr(obj)


# component_test_variables.py

from .variables import Literal, Variable, parse_variables
import pytest

def test_parse_variables():
    stream = ["key1=value1", "key2=value2"]
    result = parse_variables(stream)
    assert result == {"key1": Literal("value1"), "key2": Literal("value2")}


# component_test_zip_imports.py

from .test_cli import run_dotenv
import pytest

def walk_to_root(path: str) -> List[str]:
    pass  # Implement based on usage in tests

def setup_zipfile(zip_file_name: str, file_list: List[str]) -> Any:
    pass  # Implement based on usage in tests

def test_load_dotenv_gracefully_handles_zip_imports_when_no_env_file():
    pass  # Implement based on usage in tests

def test_load_dotenv_outside_zip_file_when_called_in_zipfile():
    pass  # Implement based on usage in tests