# Flash MicroPython Firmware

`shell49` can flash or upgrade firmware on MicroPython boards. Presently, only `ESP` processors are supported.

The first time, several configuration variables need to be set. After this initial step, the `flash` commands rewrites/updates the firmware using the parameters entered.

## Setting Parameters for Flashing

Set configuration values with

```
config --default <option> <value>
```

For example,

```
config --default port /dev/ttyUSB0
```

sets the serial port.

Do not specify the `--default` option if you have multiple boards with different configuration parameters. 

Type

```
config
```

without arguments to get a list of configuration values for the currently active board (see `boards` command) and all default values.

Below is a list of parameters used for flashing:

* `firmware_url`: url from which to fetch the firmware. No need to change unless you want to host firmware on your own server.
* `board`: presently only `HUZZAH32` is accepted. Will work for most ESP32 boards with 4MBytes of flash memory, except that on other hwardware the pin names in the boards module may be incorrect.
* `flash_options`: options for `esptool`. Usually the default works and does not need changing.
* `port`: USB port, e.g. `/dev/ttyUSB0`
* `flash_baudrate`: check the documentation for your board, usually `921600` works fine

Changes to the configuration are saved automatically when exiting `shell49`.

## Flashing

After the configuration has been set, the `flash` commands uploads firmware to the micrcotroller.

```
flash [options]
```

Options:

* `--list` prints a list of available firmware version.  No flashing is done.
* `--version ...` Sets the firmware option to flash. Usually the default (`STABLE`) is appropriate.
* `--erase` erases the entire flash. Without this option, the file stored on the microcontroller are left unchanged and only the new firmware is written. Use this option when flashing a new controller on which MicroPython has not previously been installed or when the file system is corrupt.
* `--board ...` overwrites the `board` option in the configuration.

After flashing the firmware for the first time, run

```
config -u name <board-name>
```

Replace `<board-name>` with the name for your board, e.g. `my-super-computer`. The `-u` option flashes the name to the board (file `config.py`). Later when connecting to a board `shell49` retrieves the name and matches it to the stored configuration.