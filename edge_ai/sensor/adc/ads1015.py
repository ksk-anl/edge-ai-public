import Adafruit_ADS1x15

from ..basesensor import BaseSensor

class ADS1015(BaseSensor):
    # This currently uses the Adafruit ADS1x15 library.
    # Might be a good idea to generalize this by using spidev/smbus,
    # but that would take time we don't have right now

    def __init__(self, address: int = 0x48, busnum: int = 1) -> None:
        self._address = address
        self._busnum = busnum

        # set up the bus
        self._adc = Adafruit_ADS1x15.ADS1015(address = self._address,
                                             busnum = self._busnum)
        # defaults
        self._adc_gain = 1

    # Overload Base class start implementation
    def start(self) -> None:
        self.start_single(0)

    def start_single(self, channel: int = 0) -> None:
        self._adc.start_adc(channel, gain = self._adc_gain)

    def start_diff(self, differential: int = 0) -> None:
        self._adc.start_adc_difference(differential, gain = self._adc_gain)

    def stop(self) -> None:
        self._adc.stop_adc()

    def read(self) -> float:
        raw_diff = self._adc.get_last_result()
        return self._sensor_raw_value_to_v(raw_diff)

    def read_single(self, channel: int = 0) -> float:
        raw = self._adc.read_adc(channel)
        return self._sensor_raw_value_to_v(raw)

    def read_diff(self, differential: int = 0) -> float:
        raw = self._adc.read_adc_difference(differential)
        return self._sensor_raw_value_to_v(raw)

    # TODO: ADC gain setters
    @staticmethod
    def _sensor_raw_value_to_v(value: int) -> float:
        return value * 4.096 * 2 / 4096
