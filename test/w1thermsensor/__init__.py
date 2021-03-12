#!/usr/bin/env python3

# Copyright 2021 Jonathan Haigh <jonathanhaigh@gmail.com>
# SPDX-License-Identifier: MIT

import os
import pathlib

class W1ThermSensorError(RuntimeError):
    pass

class FakeSensor:
    def __init__(self):
        self.id = "fakesensor"
        self._temps_path = pathlib.Path(os.environ["FAKE_SENSOR_PATH"])
        self._temps = list(map(int, self._temps_path.read_text().split(";")))
        self._current = 0

    def get_temperature(self):
        if self._current < len(self._temps):
            temp = self._temps[self._current]
            self._current += 1
            return temp
        # Removal of the fake sensor file indicates that we've finished
        self._temps_path.unlink(missing_ok=True)
        raise W1ThermSensorError("Error reading temperature")



class W1ThermSensor:
    _sensor = FakeSensor()

    @staticmethod
    def get_available_sensors():
        return (W1ThermSensor._sensor,)
