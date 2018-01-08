# Connect to MicroPython Boards

`shell49` can connect to one or several boards simultaneously over wired or wireless connections.

## Serial Connections

```
connect serial [port]
```

connects to the board at the specified port (e.g. `/dev/ttyUSB0`). If the port parameter is not given, `shell49` looks it up in the configuration (`config` command). 

## Wireless (telnet) Connection

```
connect telnet [address]
```

`address` is the url of your board, e.g. `192.168.1.27` or `myboard.local`.

If no address is specified, the command connects to all boards advertising the `_repl` service over mDNS and whose hostname matches one of the names in the configuration (`config name ...`). `_repl` is just an alias for `_telnet`, avoiding confusion with unrelated telnet servers.