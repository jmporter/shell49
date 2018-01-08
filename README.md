# shell49

Remote MicroPytyhon shell based on Dave Hylands [rshell](https://github.com/dhylands/rshell).

## Main features:

* Connect to one or more microcontrollers with MicroPython over a wired connection or wirelessly,
* Flash firmware to the microcontroller (`flash`),
* Copy files from the host to the microcontroller (`cp`, `rsync`, `ls`, `mkdir`, `cd`, `rm`),
* Send files from the host to the microcontroller for execution (`run`),
* Open a `REPL` console on the microcontroller (`repl`)


## Installation

`shell49` is written in pure Python and requires Python interpreter version 3.4 or later. Install from the console with

```
pip install shell49
```

To upgrade shell49 to the newest version, issue the command

```
pip install shell49 --upgrade
```

## Help

At the command prompt, type

```
shell49 -h
```

to get a list of command line options.

For information about available commands, start `shell49` and type

```
help
```

## Common Tasks

* [Flash MicroPython firmware](doc/flash.md)
* [Connect to MicroPython board](doc/connect.md)
* REPL console - type `repl` at the `shell49` prompt
* [Run program stored in file on host](doc/run.md)
* Copy files to/from MicroPython board