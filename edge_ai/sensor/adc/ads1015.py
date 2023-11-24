from __future__ import annotations

from typing import Type

from ...bus import I2C, BaseBus
from ..basesensor import BaseSensor


class ADS1015(BaseSensor):
    CONVERSION_REGISTER = 0x00
    CONFIG_REGISTER = 0x01
    LO_THRESH_REGISTER = 0x02
    HI_THRESH_REGISTER = 0x03

    CONFIG_REGISTER_DEFAULT = [0x85, 0x83]

    # Multiplexer (channel comparator values)
    # bits [14:12] on config register
    CH_COMP = {(0, 1): 0b000, (0, 3): 0b001, (1, 3): 0b010, (2, 3): 0b011}  # default
    CH_SINGLE = {0: 0b100, 1: 0b101, 2: 0b110, 3: 0b111}

    # Full Scale Range Values
    # Volt: bit setting
    # bits [11:9] on config register
    RANGES = {
        6.144: 0b000,
        4.096: 0b001,
        2.048: 0b010,  # default
        1.024: 0b011,
        0.512: 0b100,
        0.256: 0b101,
    }

    # Operating Mode
    # bit 8 on config register
    MODE_CONTINUOUS = 0b0
    MODE_SINGLE = 0b1  # default

    # Data Rate Setting
    # bits 7:5 on config register
    DATARATES = {
        128: 0b000,
        250: 0b001,
        490: 0b010,
        920: 0b011,
        1600: 0b100,  # default
        2400: 0b101,
        3300: 0b110,
    }

    # Comparator Mode
    # bit 4 on config register
    COMP_TRADITIONAL = 0b0  # default
    COMP_WINDOW = 0b1

    # Comparator Polarity
    # bit 3 on config register
    COMP_POL_LOW = 0b0  # default
    COMP_POL_HIGH = 0b1

    # Latching comparator
    # bit 2 on config register
    LATCH_OFF = 0b0  # default
    LATCH_ON = 0b1

    # Comparator queue
    # Bits [1:0] on config register
    ASSERT_AFTER_1 = 0b00
    ASSERT_AFTER_2 = 0b01
    ASSERT_AFTER_4 = 0b10
    QUEUE_OFF = 0b11  # default

    def __init__(self, bus: Type[BaseBus]) -> None:
        super().__init__(bus)

        # set up the bus
        # self._adc = Adafruit_ADS1x15.ADS1015(address = self._address,
        #                                      busnum = self._busnum)
        # defaults
        self._adc_gain = 1
        self._read_diff = (0, 1)
        self._read_single = None
        self._full_range = 2.048
        self._continuous_mode = True
        self._datarate = 1600
        self._traditional_comp = True
        self._comp_polarity = 0
        self._latching_comp = False
        self._comp_queue = 0

    @staticmethod
    def I2C(address: int = 0x48, busnum: int = 1) -> ADS1015:
        bus = I2C(address, busnum)

        adc = ADS1015(bus)

        # defaults
        adc.start_adc()
        adc.set_continuous(adc._continuous_mode)
        adc.set_data_range(adc._full_range)
        adc.set_data_rate(adc._datarate)

        # return ADS1015(bus)
        return adc

    def set_differential_mode(self, channel1: int = 0, channel2: int = 1) -> None:
        # TODO: checks
        cfg = self._bus.read_register_list(self.CONFIG_REGISTER, 2)

        cfg[0] &= 10001111
        cfg[0] |= self.CH_COMP[(channel1, channel2)] << 4

        self._bus.write_register_list(self.CONFIG_REGISTER, cfg)

    def set_single_channel(self, channel: int = 0) -> None:
        # TODO: checks
        cfg = self._bus.read_register_list(self.CONFIG_REGISTER, 2)

        cfg[0] &= 10001111  # TODO: change these to xor
        cfg[0] |= self.CH_SINGLE[channel] << 4

        self._bus.write_register_list(self.CONFIG_REGISTER, cfg)

    def set_data_range(self, full_scale_range: float = 2.048) -> None:
        # TODO: checks
        cfg = self._bus.read_register_list(self.CONFIG_REGISTER, 2)

        cfg[0] &= 11110001
        cfg[0] |= self.RANGES[full_scale_range] << 1

        self._bus.write_register_list(self.CONFIG_REGISTER, cfg)

    def set_continuous(self, continuous: bool = True) -> None:
        # TODO: checks
        cfg = self._bus.read_register_list(self.CONFIG_REGISTER, 2)

        cfg[0] &= 11111110
        cfg[0] |= 0 if continuous else 1

        self._bus.write_register_list(self.CONFIG_REGISTER, cfg)

    def set_data_rate(self, data_rate: int = 1600) -> None:
        # TODO: checks
        cfg = self._bus.read_register_list(self.CONFIG_REGISTER, 2)

        cfg[1] &= 0b11111000
        cfg[1] |= self.DATARATES[data_rate] << 5

        self._bus.write_register_list(self.CONFIG_REGISTER, cfg)

    def set_alert_ready_polarity(self, polarity=0) -> None:
        cfg = self._bus.read_register_list(self.CONFIG_REGISTER, 2)

        cfg[1] &= 0b11110111
        cfg[1] |= polarity << 3

        self._bus.write_register_list(self.CONFIG_REGISTER, cfg)

    def set_comp_mode_traditional(self) -> None:
        cfg = self._bus.read_register_list(self.CONFIG_REGISTER, 2)

        cfg[1] &= 0b11101111

        self._bus.write_register_list(self.CONFIG_REGISTER, cfg)

    def set_comp_mode_window(self) -> None:
        cfg = self._bus.read_register_list(self.CONFIG_REGISTER, 2)

        cfg[1] |= 0b1 << 4

        self._bus.write_register_list(self.CONFIG_REGISTER, cfg)

    def enable_latching_comparator(self, latch=True) -> None:
        cfg = self._bus.read_register_list(self.CONFIG_REGISTER, 2)

        cfg[1] &= 0b11111011
        if latch:
            cfg[1] |= 1 << 2

        self._bus.write_register_list(self.CONFIG_REGISTER, cfg)

    def set_comparator_queue(self, length=0) -> None:
        cfg = self._bus.read_register_list(self.CONFIG_REGISTER, 2)

        cfg[1] &= 0b11111100
        if length != 0:
            cfg[1] |= length - 1
        else:
            cfg[1] |= 3

        self._bus.write_register_list(self.CONFIG_REGISTER, cfg)

    # TODO: make this use V units rather than hex/binary
    def set_lo_thresh(self, value=0x800) -> None:
        thresh_in_bytes = self._divide_into_bytes(value)

        self._bus.write_register_list(self.LO_THRESH_REGISTER, thresh_in_bytes)

    def set_hi_thresh(self, value=0x7FF) -> None:
        thresh_in_bytes = self._divide_into_bytes(value)

        self._bus.write_register_list(self.HI_THRESH_REGISTER, thresh_in_bytes)

    # starts continuous conversion
    def start_continuous(self) -> None:
        cfg = self._bus.read_register_list(self.CONFIG_REGISTER, 2)

        cfg[0] |= 0x80

        self._bus.write_register_list(self.CONFIG_REGISTER, cfg)

    def start_singleshot(self) -> None:
        cfg = self._bus.read_register_list(self.CONFIG_REGISTER, 2)

        cfg[0] |= 0x81

        self._bus.write_register_list(self.CONFIG_REGISTER, cfg)

    def start_adc(self) -> None:
        if self._continuous_mode:
            self.start_continuous()
        else:
            self.start_singleshot()

    # TODO: stop conversions
    def stop(self) -> None:
        # set config register to default
        self._bus.write_register_list(
            self.CONFIG_REGISTER, self.CONFIG_REGISTER_DEFAULT
        )

    def new_data_available(self) -> bool:
        cfg = self._bus.read_register_list(self.CONFIG_REGISTER, 2)

        return cfg[0] >> 15

    def read(self) -> float:
        raw_diff = self._bus.read_register_list(self.CONVERSION_REGISTER, 2)
        final = self._combine_bytes(raw_diff[0], raw_diff[1], 12)

        return self._sensor_raw_value_to_v(final)

    # TODO: ADC gain setters
    @staticmethod
    def _sensor_raw_value_to_v(value: int) -> float:
        # convert two's complement
        max_value = 2**12
        if value > max_value:
            value -= max_value

        return (value * 4.096 * 2) / (max_value)
