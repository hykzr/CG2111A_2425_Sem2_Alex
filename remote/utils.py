import sys
import traceback

def print_red(text:str, end="\n"):
    if type(text) != str:
        text = repr(text)
    print("\033[31m"+text+"\033[0m", end=end)  # Red
def print_green(text:str, end="\n"):
    if type(text) != str:
        text = repr(text)
    print("\033[32m"+text+"\033[0m", end=end)  # Red
def print_bold(text:str, end="\n"):
    if type(text) != str:
        text = repr(text)
    print("\033[1m"+text+"\033[0m", end=end)  # Red
def print_orange(text:str, end="\n"):
    if type(text) != str:
        text = repr(text)
    print("\033[38;5;208m"+text+"\033[0m", end=end)  # Orange-ish (256-color mode)
def get_key():
    import termios
    import tty
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        first = sys.stdin.read(1)
        
        if first == '\x1b':
            rest = sys.stdin.read(2)  # Read 2 more chars if it's ESC
            return first + rest
        else:
            return first
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
def get_key_command():
    key = get_key()
    if not key:
        return None
    arrow_map = {
        '\x1b[A': "f 20 100",  # Up
        '\x1b[B': "b 20 100",  # Down
        '\x1b[D': "l 50 100",  # Left
        '\x1b[C': "r 50 100",  # Right
    }

    wasd_map = {
        'w': "f 5 80",
        's': "b 5 80",
        'a': "l 5 95",
        'd': "r 5 95",
        'p': 's'
    }

    if key in arrow_map:
        return arrow_map[key]
    elif key in wasd_map:
        return wasd_map[key]
    else:
        return key[0]