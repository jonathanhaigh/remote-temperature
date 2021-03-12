# Remote Temperature Logging

This project contains two Python 3 packages:
* `remote-temperature-client` is a daemon that reads temperatures using a
  DS18B20 temperature sensor and sends those temperatures to a remote server
  running `remore-temperature-server`.
* `remote-temperature-server` is a daemon that receives temperature readings
  from remote clients and records them in a database.

## `remote-temperature-client`

### Installation
```
python3 -m pip install "https://github.com/jonathanhaigh/remote-temperature#egg=remote-temperature-client&subdirectory=remote-temperature-client"
```

The "w1\_therm" and "w1\_gpio" kernel modules must be available on the device.

### Usage
```
usage: remote-temperature-client [-h] --server SERVER [--daemonize]
                                 [--pid-file PID_FILE] [--log-file LOG_FILE]
                                 [--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}]
                                 [--device-id DEVICE_ID] [--period PERIOD]
                                 [--sanity-check-low SANITY_CHECK_LOW]
                                 [--sanity-check-high SANITY_CHECK_HIGH]

Log temperatures to remote database

optional arguments:
  -h, --help            show this help message and exit
  --server SERVER       The URL of the remote server to send temperatures to
                        (required)
  --daemonize           Run as a daemon
  --pid-file PID_FILE   Path to use as a PID file. Implies --daemonize
  --log-file LOG_FILE   The location of a file to log messages to
  --log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        The severity threshold for events to be logged.
                        Default: INFO
  --device-id DEVICE_ID
                        A string to sent to the remote server to identify this
                        device. Default: unknown
  --period PERIOD       Time period between sensor reads in seconds. Default:
                        60.0
  --sanity-check-low SANITY_CHECK_LOW
                        A temperature, in degrees C, below which sensor
                        readings should be considered invalid. Default: -15.0
  --sanity-check-high SANITY_CHECK_HIGH
                        A temperature, in degrees C, above which sensor
                        readings should be considered invalid. Default: 100.0
```

### Example
```
remote-temperature-client \
  --daemonize \
  --server "http://192.168.0.61:8080" \
  --log-file /var/log/remote-temperature-client.log \
  --log-level DEBUG \
  --device-id "D0001" \
  --period 10
```

## `remote-temperature-server`

## Installation
```
python3 -m pip install "https://github.com/jonathanhaigh/remote-temperature#egg=remote-temperature-server&subdirectory=remote-temperature-server"
```

## Usage
```
usage: remote-temperature-server [-h] [--address ADDRESS] [--port PORT] [--database DATABASE] [--daemonize] [--pid-file PID_FILE]
                                 [--log-file LOG_FILE] [--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}]

Record temperatures from remote clients

optional arguments:
  -h, --help            show this help message and exit
  --address ADDRESS     The hostname or IP address on which to listen. Default: localhost
  --port PORT           The port on which to listen. Default: 8080
  --database DATABASE   The path to the database file to record temperatures in. Default: /var/temperatures
  --daemonize           Run as a daemon
  --pid-file PID_FILE   Path to use as a PID file. Implies --daemonize
  --log-file LOG_FILE   The location of a file to log messages to
  --log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        The severity threshold for events to be logged Default: INFO
```

### Example
```
remote-temperature-server \
  --address 192.168.0.61 \
  --port 8080 \
  --database /tmp/database \
  --log-file /tmp/log \
  --daemonize --log-level DEBUG
```
