import spidev

from .basebus import BaseBus

class SPI(BaseBus):
    def __init__(self, busnum: int, cs: int, maxspeed: int = 1_000_000, mode: int = 3) -> None:
        self._busnum = busnum
        self._cs = cs
        self._maxspeed = maxspeed
        self._mode = mode

        self._spi = None

    def _get_bus(self) -> spidev.SpiDev:
        if self._spi is None:
            self.start()

        return self._spi

    def start(self) -> None:
        self._spi = spidev.SpiDev()
        self._spi.open(self._busnum, self._cs)
        self._spi.max_speed_hz = self._maxspeed
        self._spi.mode = self._mode

    def stop(self) -> None:
        if self._spi is None:
            raise Exception("Attempted to stop bus before starting")

        self._spi.close()

    def read_register(self, register: int) -> int:
        to_read = [register | 0x80, 0x00]

        return self._get_bus().xfer2(to_read)[1]

    def write_register(self, register: int, value: int) -> None:
        to_write = [register, value]

        self._get_bus().xfer2(to_write)

    #TODO: Multibyte version?