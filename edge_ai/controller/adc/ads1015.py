from __future__ import annotations

from multiprocessing.connection import Connection

import edge_ai.sensor as sensor
from ..basecontroller import BaseController

class ADS1015(BaseController):
    def __init__(self, mode: str, busconfig: dict[str, int]) -> None:
        super().__init__()
        self._mode = mode
        self._busconfig = busconfig

        # TODO: set up defaults for sensor initialization

    @staticmethod
    def I2C(address: int, busnum: int) -> ADS1015:
        busconfig = {
            'address': address,
            'busnum': busnum
        }
        controller = ADS1015('i2c', busconfig)
        return controller

    def _initialize_sensor(self)-> sensor.adc.ADS1015:
        return sensor.adc.ADS1015(**self._busconfig)

    def _internal_loop(self, pipe: Connection) -> None:
        # this is a loop that manages the running of the sensor.

        # Initialize Sensor
        adc = self._initialize_sensor()

        # Write any settings, config, etc
        #TODO: Setup sensor configs from the controller


        # TODO: add more control over which are read/etc
        while True:
            # poll the pipe
            if pipe.poll():
                message = pipe.recv()

                # if pipe says "read", send out the data into the pipe
                if message[0] == "read":
                    pipe.send(adc.read_diff(0))