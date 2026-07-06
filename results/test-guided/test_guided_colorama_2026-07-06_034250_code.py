# ansi.py

from typing import Any, Tuple

class AnsiCursor:
    def UP(self, n: int) -> None:
        pass
    
    def DOWN(self, n: int) -> None:
        pass
    
    def FORWARD(self, n: int) -> None:
        pass
    
    def BACK(self, n: int) -> None:
        pass
    
    def POS(self, x: int, y: int) -> None:
        pass

class AnsiCodes:
    def __init__(self):
        pass

class AnsiFore(AnsiCodes):
    pass

class AnsiBack(AnsiCodes):
    pass

def code_to_chars(code: int) -> str:
    return chr(code)

def set_title(title: str) -> None:
    print(f"\033]2;{title}\a", end='')

def clear_screen() -> None:
    print("\033c")

def clear_line() -> None:
    print("\033[2K")
# ansitowin32.py

from typing import Any, Optional, Tuple
import sys

class StreamWrapper:
    def __init__(self, stream: Any) -> None:
        self.stream = stream
    
    def write(self, data: str) -> int:
        return self.stream.write(data)
    
    @property
    def isatty(self) -> bool:
        return self.stream.isatty()
    
    @property
    def closed(self) -> bool:
        return self.stream.closed

class AnsiToWin32:
    def __init__(self, stream: Any = None) -> None:
        self.stream = stream
    
    def call_win32(self, data: str) -> int:
        return self.stream.write(data)
    
    def convert_ansi(self, data: str) -> Optional[str]:
        return data
    
    def convert_osc(self, data: str) -> Optional[str]:
        return data
    
    def extract_params(self, data: str) -> Tuple[int, ...]:
        params = []
        for token in data.split(';'):
            try:
                params.append(int(token))
            except ValueError:
                pass
        return tuple(params)
    
    def flush(self) -> None:
        self.stream.flush()
# initialise.py

from colorama.ansitowin32 import AnsiToWin32
from typing import Any

def reset_all() -> None:
    pass

def init() -> None:
    pass

def deinit() -> None:
    pass

def just_fix_windows_console() -> None:
    pass

def colorama_text() -> bool:
    return True

def reinit() -> None:
    pass

def wrap_stream(stream: Any) -> Any:
    return AnsiToWin32.wrap_stream(stream)
# win32.py

from typing import Any
import ctypes

windll = ctypes.windll
winapi_test = windapi_test


# winterm.py

class WinColor:
    def __init__(self, color_code: int) -> None:
        self.color_code = color_code

class WinStyle:
    def __init__(self, style_code: int) -> None:
        self.style_code = style_code

class WinTerm:
    def __init__(self):
        pass
    
    def back(self, color: WinColor) -> None:
        print(f"\033[{color.color_code}m", end='')
    
    def cursor_adjust(self) -> None:
        print("\033[?25h")
    
    def erase_line(self) -> None:
        print("\033[K")
    
    def erase_screen(self) -> None:
        print("\033[2J")


# demo06.py

def main() -> None:
    pass


# demo07.py

def main() -> None:
    pass


# demo08.py

def main() -> None:
    pass