from setuptools import setup

setup(
    name = 'minesweeper',
    description='A pure Python implementation of minesweeper using curses.',
    version = '0.1.0',
    author = 'Mia Celeste',
    python_requires = '>=3.8',
    scripts=['minesweeper/minesweeper'],
    packages=['minesweeper']
)
