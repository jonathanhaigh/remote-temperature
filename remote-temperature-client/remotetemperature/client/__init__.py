#!/usr/bin/env python3

# Copyright 2021 Jonathan Haigh <jonathanhaigh@gmail.com>
# SPDX-License-Identifier: MIT

import argparse
import daemon
from daemon.pidfile import TimeoutPIDLockFile
import datetime
import logging
from logging.handlers import RotatingFileHandler
import signal
import time
from w1thermsensor import W1ThermSensor, W1ThermSensorError
import xmlrpc
from xmlrpc.client import ServerProxy


class SanityCheckError(ValueError):
    pass


class RemoteTemperatureClient:

    def __init__(self, args):
        self._init_logger(args)
        self._logger.info("remote-temperature-client starting")
        self._device_id = args.device_id
        self._period = args.period
        self._sanity_check_low = args.sanity_check_low
        self._sanity_check_high = args.sanity_check_high
        self._quit = False
        try:
            self._rpc_proxy = xmlrpc.client.ServerProxy(args.server)
        except Exception as e:
            self._logger.error(f"Failed to initialize xmlrpc proxy: {str(e)}")
            raise

    def run_forever(self):
        while not self._quit:
            for sensor in W1ThermSensor.get_available_sensors():
                self._read_and_record_temperature(sensor)
            time.sleep(self._period)
        self._logger.info("quitting")

    def quit(self):
      self._logger.info("Received quit request")
      self._quit = True

    def _init_logger(self, args):
        self._logger = logging.getLogger(__name__)
        if args.log_file:
            self._logger.addHandler(RotatingFileHandler(
                args.log_file,
                maxBytes=1024 * 1024
            ))
        elif args.daemonize:
            # If we're a daemon then stderr will have been closed so we don't have
            # anywhere to log to
            self._logger.addHandler(logging.NullHandler())

        if args.log_level:
            self._logger.setLevel(level=getattr(logging, args.log_level))

    def _read_and_record_temperature(self, sensor):
        try:
            temperature = sensor.get_temperature()
            timestamp = datetime.datetime.now().timestamp()
            self._check_temperature_sanity(sensor.id, temperature)

            self._logger.debug((
                f"Read temperature {temperature}C"
                f" from sensor {sensor.id}"
                f" on device {self._device_id}"
                f" at timestamp {timestamp}"
                ))
            result = self._rpc_proxy.record_temperature(
                self._device_id,
                sensor.id,
                timestamp,
                temperature,
            )
            if result != 0:
                self._logger.error(
                    f"Received error status {result} from remote server"
                )
        except (W1ThermSensorError, SanityCheckError) as e:
            self._logger.error(f"Failed to read from sensor {sensor.id}: {str(e)}")
        except xmlrpc.client.Fault as e:
            self._logger.error(f"RPC error ({e.faultCode}): {e.faultString}")
        except (xmlrpc.client.ProtocolError) as e:
            self._logger.error(f"Protocol error ({e.errcode}): {e.errmsg}")
        except ConnectionError as e:
            self._logger.error(f"Connection error: {str(e)}")

    def _check_temperature_sanity(self, sensor_id, temperature):
        if (
            self._sanity_check_low is not None
            and temperature < self._sanity_check_low
        ):
            raise SanityCheckError(
                (
                    f"Temerature reading ({temperature}C)for sensor {sensor_id}"
                    f" failed sanity check; temperature is below low threshold of"
                    f" {self._sanity_check_low}C"
                )
            )

        if (
            self._sanity_check_high is not None
            and temperature > self._sanity_check_high
        ):
            raise SanityCheckError(
                (
                    f"Temerature reading ({temperature}C)for sensor {sensor_id}"
                    f" failed sanity check; temperature is above high threshold of"
                    f" {self._sanity_check_high}C"
                )
            )


def parse_args():
    default_log_level = "INFO"
    default_device_id = "unknown"
    default_period = 60.0
    default_sanity_check_low = -15.0
    default_sanity_check_high = 100.0

    parser = argparse.ArgumentParser(
        description="Log temperatures to remote database"
    )
    parser.add_argument(
        "--server",
        help="The URL of the remote server to send temperatures to (required)",
        required=True,
    )
    parser.add_argument(
        "--daemonize",
        help="Run as a daemon",
        action="store_true",
    )
    parser.add_argument(
        "--pid-file",
        help="Path to use as a PID file. Implies --daemonize",
    )
    parser.add_argument(
        "--log-file",
        help="The location of a file to log messages to",
    )
    parser.add_argument(
        "--log-level",
        help=(
            f"The severity threshold for events to be logged."
            f" Default: {default_log_level}"
        ),
        default=default_log_level,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    )
    parser.add_argument(
        "--device-id",
        help=(
            f"A string to sent to the remote server to identify"
            f" this device. Default: {default_device_id}"
        ),
        default=default_device_id,
    )
    parser.add_argument(
        "--period",
        help=(
            f"Time period between sensor reads in seconds."
            f" Default: {default_period}"
        ),
        type=float,
        default=default_period,
    )
    parser.add_argument(
        "--sanity-check-low",
        help=(
            f"A temperature, in degrees C, below which sensor readings should"
            f" be considered invalid. Default: {default_sanity_check_low}"
        ),
        type=float,
        default=default_sanity_check_low
    )
    parser.add_argument(
        "--sanity-check-high",
        help=(
            f"A temperature, in degrees C, above which sensor readings should"
            f" be considered invalid. Default: {default_sanity_check_high}"
        ),
        type=float,
        default=default_sanity_check_high,
    )
    args = parser.parse_args()
    if args.pid_file:
        setattr(args, "daemonize", True)
    return args


def run(args):
    client = RemoteTemperatureClient(args)

    def handle_sigterm(signum, frame):
      client.quit()

    signal.signal(signal.SIGINT, handle_sigterm)
    signal.signal(signal.SIGTERM, handle_sigterm)

    client.run_forever()


def main():
    args = parse_args()

    daemon_context_args = {}
    if args.pid_file:
        daemon_context_args["pidfile"] = TimeoutPIDLockFile(
            args.pid_file,
            acquire_timeout=1
        )

    if args.daemonize:
        with daemon.DaemonContext(**daemon_context_args):
            run(args)
    else:
        run(args)


if __name__ == "__main__":
    main()
