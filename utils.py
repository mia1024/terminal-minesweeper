import os
from config import Config
config=Config()

fd = 0


def init_print():
    global fd
    if config.debug:
        if not os.path.exists('debug'):
            os.mkfifo('debug')
        print('waiting for receiving pipe to attach')
        fd = os.open('debug', os.O_WRONLY )
        print('attached')


def debug_print(*args, end = '\n', sep = ' '):
    if config.debug:
        os.write(fd, sep.join(map(str,args)).encode())
        os.write(fd, end.encode())


def end_print():
    if config.debug:
        os.close(fd)

