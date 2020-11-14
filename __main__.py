import sys, os, time
from config import config


def print_slow(text: str, trailing_newline=True):
    for i in range(len(text) + 1):
        print('\r' + text[:i], end='', flush=True)
        time.sleep(0.035)
    if trailing_newline: print()


def check(condition: bool, name: str, err_message: str):
    if config.silent_check:
        if not condition:
            print('Error: '+err_message)
            sys.exit(1)
        else:
            return
    prefix = 'Checking ' + name + '...'
    print_slow(prefix, trailing_newline=False)
    if condition:
        for i in range(7):
            print(f"\r{prefix}\033[92m{'PASSED'[:i]}\033[0m", flush=True, end='')
        print()
    else:
        for i in range(7):
            print(f"\r{prefix}\033[91m{'FAILED'[:i]}\033[0m", flush=True, end='')
        print('\033[91m')
        print_slow(err_message)
        print('\033[0m')
        sys.exit(1)

if not config.silent_check:
    print_slow('Welcome to terminal minesweeper by Mia Celeste')
    print_slow('Running compatibility check...')

v = sys.version_info
check(v.major == 3 and v.minor >= 8,
      'Python version',
      'Please use Python3.8 or above'
      )

check('xterm' in os.environ.get('TERM', ''),
      'terminal compatibility',
      'Please use an xterm-compatible terminal'
      )

width, height = os.get_terminal_size()

min_width = config.board_width * 5 + 10
min_height = config.board_height * 2 + 4
check(width >= min_width, 'terminal width',
      f'Please make sure your terminal has at least {min_width} columns')
check(height >= min_height, 'terminal height',
      f'Please make sure your terminal has at least {min_height} rows')

from ui import main

main()
