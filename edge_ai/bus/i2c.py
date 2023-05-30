import smbus2

from .basebus import BaseBus

class I2C(BaseBus):
    def __init__(self, address: int, busnum: int) -> None:
        self._address = address
        self._busnum = busnum

        self._i2c = None

    def _get_bus(self) -> smbus2.SMBus:
        if self._i2c is None:
            self.start()

        return self._i2c

    def start(self) -> None:
        self._i2c = smbus2.SMBus(self._busnum)

    def stop(self) -> None:
        if self._i2c is None:
            raise Exception("Attempted to stop bus before starting")

        self._i2c.close()

    def write_register(self, register: int, value: int) -> None:
        self._get_bus().write_byte_data(self._address, register, value)

    def read_register(self, register: int) -> int:
        return self._get_bus().read_byte_data(self._address, register)