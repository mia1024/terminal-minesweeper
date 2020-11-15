import sys, os, time
from config import config
import signal


def sigint_handler(signum, frame):
    print('\033[0m\nAlright. Alright. You are not sweeping any mines today')
    print('\033[?25h', end='')  # reenable cursor
    sys.exit(2)


system_sigint_handler = signal.getsignal(signal.SIGINT)
signal.signal(signal.SIGINT, sigint_handler)


def print_slow(text: str, trailing_newline=True, prefix='', suffix='', delay=0.02):
    for i in range(len(text) + 1):
        print('\r' + prefix + text[:i] + suffix, end='', flush=True)
        time.sleep(delay)
    if trailing_newline: print()


def check(condition: bool, name: str, error_message: str):
    if config.silent_checks:
        if not (condition or config.ignore_failures):
            print('\033[37mError: ' + error_message + '\033[0m')
            sys.exit(1)
        else:
            return
    prefix = 'Checking ' + name + '...'
    print_slow(prefix, trailing_newline=False)
    if condition:
        for i in range(7):
            print(f"\r{prefix}\033[92m{'PASSED'[:i]}\033[0m", flush=True, end='')
            time.sleep(0.02)
        print()
    else:
        if not config.ignore_failures:
            for i in range(7):
                print(f"\r{prefix}\033[91m{'FAILED'[:i]}\033[0m", flush=True, end='')
                time.sleep(0.02)
            print('\033[91m')
            print_slow(error_message)
            print('\033[37m', end='')
            print_slow('Alternatively, you may pass in the --ignore-failure switch.', delay=0.01)
            print_slow('However, you will probably encounter a curses error if you do so.', delay=0.01)
            print('\033[0m', end='')
            sys.exit(1)
        else:
            for i in range(16):
                print(f"\r{prefix}\033[91m{'FAILURE IGNORED'[:i]}\033[0m", flush=True, end='')
            print()


if not config.silent_checks:
    print('\033[?25l', end='')  # disable cursor
    print_slow('Welcome to terminal minesweeper by Mia Celeste')
    print_slow('Commencing system check.')

v = sys.version_info
check(v.major == 3 and v.minor >= 8,
      'Python version',
      'Please use Python3.8 or above.'
      )

check('xterm-256color' in os.environ.get('TERM', ''),
      'terminal compatibility',
      'Please use an xterm-256color compatible terminal'
      ' such as MinTTY' if sys.platform == 'win32' else '.'
      )

try:
    import curses
except:
    curses_ok = False
else:
    curses_ok = True

check(curses_ok, 'if curses is present',
      'Cannot import curses, please check your Python installation.'
      ' Perhaps try installing Cygwin or windows-curses?' if sys.platform == 'win32' else ''
      )

width, height = os.get_terminal_size()

min_width = config.board_width * 5 + 1 + 10 + 22
min_height = config.board_height * 2 + 4
check(width >= min_width, 'window width',
      f'Please make sure your terminal window has at least {min_width} ({min_width - width} more) columns.')
check(height >= min_height, 'window height',
      f'Please make sure your terminal window has at least {min_height} ({min_height - height} more) rows.')

if not config.silent_checks:
    print_slow('All system checks completed （＾ω＾） ready to sweep some mines ┗(＾0＾)┓')
    print_slow('Making a window...',trailing_newline=False)

from ui import main, calc_first_frame, FG, BG

# only import everything after the system checks so we don't get random errors

if not config.silent_checks:
    for i, row in enumerate(calc_first_frame(height, width)):
        print()
        print(f'[38;5;{FG}m\033[48;5;{BG}m', end='')
        print_slow(row, delay=max(0.02 / 2 ** i, 0.001), prefix=f'\033[38;5;{FG}m\033[48;5;{BG}m', suffix='\033[0m',
                   trailing_newline=False)
        print('\033[0m', end='')
    print('\033[0m', end='')
    sys.stdout.flush()
else:
    print()

signal.signal(signal.SIGINT,system_sigint_handler)
main()
