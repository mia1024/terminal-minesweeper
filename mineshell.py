#! /usr/bin/python

import os, sys
import readline
import shlex
import signal
from minesweeper import __version__, config, main

fps = os.environ.get("MINESWEEPER_FORCE_FPS")
print("\033[95mWelcome! Run \033[96mminesweeper\033[95m to start the game. "
      "Run \033[96mminesweeper --help\033[95m for a list of available options. Have fun ^_^\033[0m\n")

if fps is not None:
    try:
        fps = int(fps)
        print(f"\033[38;5;244mTo reduce server stress, your frame rate is limited to {fps} fps. "
              f"You can download the game at https://minesweeper.mia1024.io/ to enjoy uncapped performance. "
              f"If you like the game, please consider giving this project a star on GitHub.\033[0m")
    except (ValueError, TypeError):
        pass
sys.stdout.flush()


def exit_handle(signum, frame):
    print()
    sys.exit(0)


signal.signal(signal.SIGINT, exit_handle)
signal.signal(signal.SIGHUP, exit_handle)
signal.signal(signal.SIGTERM, exit_handle)


def completer(i, s):
    if readline.get_line_buffer().startswith("minesweeper "):
        return None
    if not i:
        if s == 0:
            return "minesweeper "
        if s == 1:
            return "exit"
    elif s == 0:
        return "minesweeper "
    return None


readline.set_completer(completer)
readline.parse_and_bind("tab: complete")
readline.set_completer_delims(" ")

while True:
    try:
        args = shlex.split(input("$ "))
    except EOFError:
        print()
        sys.exit(0)
    if not args:
        continue
    if args[0] == "exit":
        sys.exit(0)
    elif args[0] != "minesweeper":
        print(f"mineshell {__version__}: {args[0]}: command not found. Have you tried minesweeper?")
        continue
    else:
        try:
            config.init_config(config.parser.parse_args(args[1:]))
        except SystemExit:
            continue

        main.run()
