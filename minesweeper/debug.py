"""
This file is necessary because contents printed to either stdout or stderr
will not be visible during runtime due to the nature of curses. So, a named
pipe is used for transmitting the data. To receive the data, open a new terminal
and cd into the directory containing this file, then run

while 1; do
    cat debug
done

in bash. Then, run this program with the --debug flag.
"""

import os
from .config import Config

config = Config()

fd = 0


def init_print():
    """initializes the pipe"""
    global fd
    if config.debug:
        if not os.path.exists('debug'):
            os.mkfifo('debug')
        print('waiting for receiving pipe to attach')
        fd = os.open('debug', os.O_WRONLY)
        print('attached')


def debug_print(*args, end = '\n', sep = ' '):
    """
    simulates the behavior of __builtins__.print but send it to the named pipe.
    ignores all invocations unless debug mode is set.
    """
    if config.debug:
        os.write(fd, sep.join(map(str, args)).encode())
        os.write(fd, end.encode())


def end_print():
    """
    closes the file descriptor associated with the pipe. do not delete it as
    the looping cat will complain otherwise.
    """
    if config.debug:
        os.close(fd)
