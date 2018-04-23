# Run Command

```
run [<file-name>]
```

sends the contents of the specified file to the default board (`boards` command) for execution and prints results on the `shell49` console. It has the same effect as typing the contents of the file at the `REPL` prompt.

If no `file-name` is specified, `run` re-runs the same file as last time.

**Note:** Interrupt or timer driven programs frequently relinquish control to the `repl` even though the interrupt handlers are still running. To see output (e.g. from `print`) from these handlers, issue the `repl` command at the `shell49` prompt after `run` terminates.
