#! /usr/bin/python

import os,sys

fps=os.environ.get("MINESWEEPER_FORCE_FPS")
print("\033[95mWelcome! Run \033[96mminesweeper\033[95m to start the game. "
      "Run \033[96mminesweeper --help\033[95m for a list of available options. Have fun ^_^\033[0m\n")

if fps is not None:
    try:
        fps = int(fps)
        print(f"\033[38;5;244mTo reduce server stress, your frame rate is limited to {fps} fps. "
              f"You can download the game at https://minesweeper.mia1024.io/ to enjoy uncapped performance. "
              f"If you like the game, please consider giving this project a star on GitHub.\033[0m")
    except (ValueError,TypeError):
        pass
sys.stdout.flush()
os.execv("/bin/sh",["/bin/sh"])
