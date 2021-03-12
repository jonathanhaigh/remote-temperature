#!/usr/bin/env python3

import os
import pathlib
import signal
import sqlite3
import subprocess
import time

# Theres a fake w1thermsensor module at this path that reads temperatures from
# a file rather than an actual sensor.
THIS_DIR = pathlib.Path(__file__).parent

def get_daemon_pid(pid_file_path):
    for attempt in range(0, 100):
        try:
            return int(pid_file_path.read_text())
        except FileNotFoundError:
            time.sleep(0.1)
    raise RuntimeError(
        f"Timeout waiting for PID file {pid_file_path} to be created"
    )

def wait_for_file_removal(path):
    for attempt in range(0, 100):
        if not path.exists():
            break
        time.sleep(0.1)
    if path.exists():
        raise RuntimeError(f"Timeout waiting for file {path} to be removed")

def test_remote_temperature(tmp_path):

    server_pid_file_path = tmp_path / "remote-temperature-server.pid"
    server_log_path = tmp_path / "remote-temperature-server.log"
    server_db_path = tmp_path / "temperatures"
    subprocess.run([
            "remote-temperature-server",
            "--daemonize",
            "--pid-file", str(server_pid_file_path),
            "--address", "localhost",
            "--port", "8080",
            "--database", str(server_db_path),
            "--log-file", str(server_log_path),
            "--log-level", "DEBUG",
        ]
    )
    server_pid = get_daemon_pid(server_pid_file_path)

    client_pid_file_path = tmp_path / "remote-temperature-client.pid"
    client_log_path = tmp_path / "remote-temperature-client.log"

    # Pick up the fake w1thermsensor module
    client_env = os.environ
    client_env["PYTHONPATH"] = str(THIS_DIR)

    # And leave some fake temperatures for it to read
    fake_sensor_path = tmp_path / "fake-sensor"
    client_env["FAKE_SENSOR_PATH"] = str(fake_sensor_path)
    fake_temps = [22, 23, 24, 25, 26]
    fake_sensor_path.write_text(";".join(map(str, fake_temps)))

    subprocess.run([
            "remote-temperature-client",
            "--pid-file", str(client_pid_file_path),
            "--daemonize",
            "--server", "http://localhost:8080",
            "--log-file", str(client_log_path),
            "--log-level", "DEBUG",
            "--period", str(0.1),
        ],
        env=client_env,
    )
    client_pid = get_daemon_pid(client_pid_file_path)

    # Removal of the fake sensor file indicates that the client process has
    # finished reading the fake temperatures
    wait_for_file_removal(fake_sensor_path)

    os.kill(server_pid, signal.SIGTERM)
    os.kill(client_pid, signal.SIGTERM)

    database = sqlite3.connect(server_db_path)
    cursor = database.cursor()
    cursor.execute("SELECT temperature from temperatures ORDER BY time")
    temps = cursor.fetchall()
    assert temps == [(temp,) for temp in fake_temps]
