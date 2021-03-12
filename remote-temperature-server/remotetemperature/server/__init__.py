#!/usr/bin/env python3

# Copyright 2021 Jonathan Haigh <jonathanhaigh@gmail.com>
# SPDX-License-Identifier: MIT

import argparse
import daemon
from daemon.pidfile import TimeoutPIDLockFile
import logging
from logging.handlers import RotatingFileHandler
import sqlite3
import xmlrpc
from xmlrpc.server import SimpleXMLRPCServer

class DBError(RuntimeError):
    pass

class DBClient:
    def __init__(self, host, port, database):
        try:
            self._connection = sqlite3.connect(f"file:{database}?mode=rwc")
            self._connection.execute((
                "CREATE TABLE IF NOT EXISTS temperatures"
                " (device_id, sensor_id, time, temperature)"
            ))
            self._connection.commit()
        except sqlite3.Error as e:
            raise DBError(str(e))

    def write(self, fields):
        try:
            self._connection.execute(
                "INSERT INTO temperatures VALUES (?,?,?,?)",
                (
                    fields["device_id"],
                    fields["sensor_id"],
                    fields["time"],
                    fields["temperature"],
                ),
            )
            self._connection.commit()
        except sqlite3.Error as e:
            raise DBError(str(e))


class TemperatureRecorder:
    def __init__(self, logger, database):
        self._logger = logger
        self._database = database

    def record_temperature(self, device_id, sensor_id, read_time, temperature):
        self._logger.debug((
            f"Received temperature ({temperature})"
            f" from sensor {sensor_id}"
            f" on device {device_id}"
            f" read at time {read_time}"
        ))
        try:
            self._database.write(fields={
                "device_id": device_id,
                "sensor_id": sensor_id,
                "time": read_time,
                "temperature": temperature,
            })
        except DBError as e:
            self._logger.error(f"Database write failed: {str(e)}")
            return 1
        return 0


class RemoteTemperatureServer:
    def __init__(self, args):
        self._init_logger(args)
        self._logger.info("remote-temperature-server starting")
        try:
            self._database = DBClient(host="localhost", port=8086, database=args.database)
            self._rpc_server = SimpleXMLRPCServer((args.address, args.port))
            self._rpc_server.register_instance(TemperatureRecorder(self._logger, self._database))
        except Exception as e:
            self._logger.error(f"Failed to initialize server: {str(e)}")
            raise

    def serve_forever(self):
        self._rpc_server.serve_forever()

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


def parse_args():
    default_address = "localhost"
    default_port = 8080
    default_database = "/var/temperatures"
    default_log_level = "INFO"

    parser = argparse.ArgumentParser(
        description="Record temperatures from remote clients"
    )
    parser.add_argument(
        "--address",
        help=(
            f"The hostname or IP address on which to listen."
            f" Default: {default_address}"
        ),
        default=default_address,
    )
    parser.add_argument(
        "--port",
        help=f"The port on which to listen. Default: {default_port}",
        type=int,
        default=default_port,
    )
    parser.add_argument(
        "--database",
        help=(
            f"The path to the database file to record"
            f" temperatures in. Default: {default_database}"
        ),
        default=default_database,
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
            f"The severity threshold for events to be logged"
            f" Default: {default_log_level}"
        ),
        default=default_log_level,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    )
    args = parser.parse_args()
    if args.pid_file:
        setattr(args, "daemonize", True)
    return args


def run(args):
    server = RemoteTemperatureServer(args)
    server.serve_forever()


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
