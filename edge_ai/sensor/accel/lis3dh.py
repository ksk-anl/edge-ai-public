from __future__ import annotations

from typing import Type

from ...bus import I2C, SPI, BaseBus
from ..basesensor import BaseSensor


class LIS3DH(BaseSensor):
    # Allowed values for settings
    DATARATES = {
        1: 1,
        10: 2,
        25: 3,
        50: 4,
        100: 5,
        200: 6,
        400: 7,
        1344: 9,
        1620: 8,
        5376: 9,
    }
    MEASUREMENT_RANGES = {2: 0b00, 4: 0b01, 8: 0b10, 16: 0b11}
    SELFTEST_MODES = ["off", "low", "high"]
    RESOLUTIONS = {"low": 8, "normal": 10, "high": 12}

    # Register addresses
    # Config Registers
    CTRL_REG0 = 0x1E
    CTRL_REG1 = 0x20
    CTRL_REG2 = 0x21
    CTRL_REG3 = 0x22
    CTRL_REG4 = 0x23
    CTRL_REG5 = 0x24
    CTRL_REG6 = 0x25

    REFERENCE_REGISTER = 0x26
    STATUS_REGISTER = 0x27

    # Output Registers
    OUT_X_L = 0x28
    OUT_X_H = 0x29
    OUT_Y_L = 0x2A
    OUT_Y_H = 0x2B
    OUT_Z_L = 0x2C
    OUT_Z_H = 0x2D

    def __init__(self, bus: Type[BaseBus]) -> None:
        super().__init__(bus)

        # defaults
        self._resolution = "low"
        self._measurement_range = 2
        self._datarate = 5376
        self._selftest = "off"
        self._highpass = False

        # TODO: setters should update these

    @staticmethod
    def SPI(busnum: int, cs: int, maxspeed: int = 10_000_000, mode: int = 3) -> LIS3DH:
        bus = SPI(busnum, cs, maxspeed, mode)
        return LIS3DH(bus)

    @staticmethod
    def I2C(address: int, busnum: int) -> LIS3DH:
        bus = I2C(address, busnum)
        return LIS3DH(bus)

    def set_measurement_range(self, measurement_range: int) -> None:
        if measurement_range not in self.MEASUREMENT_RANGES.keys():
            raise Exception(
                f"Measurement range must be one of: {', '.join([str(range) for range in self.MEASUREMENT_RANGES.keys()])}"
            )

        cfg = self._bus.read_register(self.CTRL_REG4)

        cfg &= 0b11001111
        cfg |= self.MEASUREMENT_RANGES[measurement_range] << 4

        self._bus.write_register(self.CTRL_REG4, cfg)

    def set_datarate(self, datarate: int) -> None:
        if datarate not in self.DATARATES.keys():
            valid_rates = [str(rate) for rate in self.DATARATES.keys()]
            raise Exception(f"Data Rate must be one of: {', '.join(valid_rates)}Hz")

        if ((datarate == 1620) or (datarate == 5376)) and (self._resolution != "low"):
            raise Exception("1620Hz and 5376Hz mode only allowed on Low Power mode")

        if datarate == 1344 and self._resolution == "low":
            raise Exception("1344Hz mode not allowed on Low Power mode")

        cfg = self._bus.read_register(self.CTRL_REG1)

        cfg |= self.DATARATES[datarate] << 4

        self._bus.write_register(self.CTRL_REG1, cfg)

    def set_resolution(self, resolution: str) -> None:
        if resolution not in self.RESOLUTIONS.keys():
            raise Exception(f'Mode must be one of {", ".join(self.RESOLUTIONS.keys())}')

        self._resolution = resolution

        if resolution == "low":
            LPen_bit = True
            HR_bit = False
        elif resolution == "high":
            LPen_bit = False
            HR_bit = True
        else:
            LPen_bit = False
            HR_bit = False

        cfg = self._bus.read_register(self.CTRL_REG1)

        if LPen_bit:
            cfg |= 0b00001000  # set LPen bit on register 20 to on
        else:
            cfg &= 0b11110111  # set LPen bit on register 20 to off

        self._bus.write_register(self.CTRL_REG1, cfg)

        cfg = self._bus.read_register(self.CTRL_REG4)

        if HR_bit:
            cfg |= 0b00000100  # set HR bit on register 23 to on
        else:
            cfg &= 0b11111011  # set HR bit on register 23 to off

        self._bus.write_register(self.CTRL_REG4, cfg)

    def set_selftest(self, mode: str = "high") -> None:
        if mode not in self.SELFTEST_MODES:
            raise Exception(
                f"Selftest Mode must be one of: {' ,'.join(self.SELFTEST_MODES)}"
            )

        cfg = self._bus.read_register(self.CTRL_REG4)

        cfg &= 0b001
        if mode == "off":
            return
        elif mode == "high":
            cfg |= 0b100
        elif mode == "low":
            cfg |= 0b010

        self._bus.write_register(self.CTRL_REG4, cfg)

    def enable_highpass(self, highpass: bool = True) -> None:
        cfg = self._bus.read_register(self.CTRL_REG2)

        if highpass:
            cfg |= 0b10001000
        else:
            cfg &= 0b00000111

        self._bus.write_register(self.CTRL_REG2, cfg)

    def enable_axes(self, x: bool = True, y: bool = True, z: bool = True) -> None:
        cfg = self._bus.read_register(self.CTRL_REG1)

        if x:
            cfg |= 0b001
        if y:
            cfg |= 0b010
        if z:
            cfg |= 0b100

        self._bus.write_register(self.CTRL_REG1, cfg)

    def read(self) -> list[float]:
        raw_values = self._read_sensors()
        return [self._raw_sensor_value_to_gravity(value) for value in raw_values]

    def new_data_available(self) -> bool:
        status = self._bus.read_register(self.STATUS_REGISTER)
        status = (status >> 3) & 1
        return bool(status)

    def _read_sensors(self) -> tuple[int, int, int]:
        x = self._bus.read_register(self.OUT_X_H)
        y = self._bus.read_register(self.OUT_Y_H)
        z = self._bus.read_register(self.OUT_Z_H)

        if self._resolution != "low":
            xl = self._bus.read_register(self.OUT_X_L)
            yl = self._bus.read_register(self.OUT_Y_L)
            zl = self._bus.read_register(self.OUT_Z_L)

            # Determine the number of "empty bits" on the right
            bitshift = 16 - self.RESOLUTIONS[self._resolution]

            x = (x << 8 | xl) >> bitshift
            y = (y << 8 | yl) >> bitshift
            z = (z << 8 | zl) >> bitshift

        return (x, y, z)

    def _raw_sensor_value_to_gravity(self, value: int) -> float:
        bits = self.RESOLUTIONS[self._resolution]

        max_val = 2**bits
        if value > max_val / 2.0:
            value -= max_val

        return float(value) / ((max_val / 2) / self._measurement_range)
