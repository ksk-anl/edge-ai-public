from __future__ import annotations

from multiprocessing.connection import Connection

import edge_ai.sensor as sensor

from ..basecontroller import BaseController


class ADS1015(BaseController):
    def __init__(self, mode: str, busconfig: dict[str, int]) -> None:
        super().__init__()
        self._mode = mode
        self._busconfig = busconfig

        # Default values
        self._continuous = True
        self._diff_channel1 = 0
        self._diff_channel2 = 1
        self._single_channel = 0
        self._diffmode = True
        self._datarange = 2.048
        self._data_rate = 1600
        self._comp_mode_traditional = True
        self._comp_polarity = 0
        self._comp_latch = False
        self._comp_queue_length = 0
        self._lo_thresh = 0x800
        self._hi_thresh = 0x7FF

    @staticmethod
    def I2C(address: int, busnum: int) -> ADS1015:
        busconfig = {"address": address, "busnum": busnum}
        controller = ADS1015("i2c", busconfig)
        return controller

    # External API
    # OS Bit: Read/Write status, continuous or singleshot controls
    def new_data_available(self) -> bool:
        self._external_pipe.send(["new_data_available"])

        return self._external_pipe.recv()

    def set_continuous(self) -> None:
        self._continuous = True

    def set_singleshot(self) -> None:
        self._continuous = False

    # MUX bit: set multiplexer state (which channels are to be used)
    def set_differential_mode(self, channel1: int = 0, channel2: int = 1) -> None:
        self._diff_channel1 = channel1
        self._diff_channel2 = channel2

        self._diffmode = True

    def set_single_channel(self, channel: int = 0) -> None:
        self._single_channel = channel

        self._diffmode = False

    # PGA bit: set full data range
    def set_data_range(self, full_scale_range: float = 2.048) -> None:
        self._datarange = full_scale_range

    # DR bits: set data rate in SPS
    def set_data_rate(self, data_rate: int = 1600) -> None:
        self._data_rate = data_rate

    # COMP_MODE bits: sets the comparator mode
    def set_comp_mode_traditional(self) -> None:
        self._comp_mode_traditional = True

    def set_comp_mode_window(self) -> None:
        self._comp_mode_traditional = False

    # COMP_POL bit: sets the ppolarity of the ALERT/RDY pin
    def set_alert_ready_polarity(self, polarity=0) -> None:
        self._comp_polarity = polarity

    # COMP_LAT bit: sets the comparator alter pin to latching mode
    def enable_latching_comparator(self, latch=True) -> None:
        self._comp_latch = latch

    # COMP_QUE bits: sets the number of consecutive conversions past the
    #   threshold before triggering the ALERT/RDY pin
    def set_comparator_queue(self, length=0) -> None:
        self._comp_queue_length = length

    # Lo and Hi_thresh registers: sets the low or high thresh register values
    def set_lo_thresh(self, value=0x800) -> None:
        self._lo_thresh = value

    def set_hi_thresh(self, value=0x7FF) -> None:
        self._hi_thresh = value

    # Internal methods
    def _initialize_sensor(self) -> sensor.adc.ADS1015:
        return sensor.adc.ADS1015.I2C(**self._busconfig)

    def _configure_sensor(self) -> None:
        self._sensor.set_data_range(self._datarange)
        self._sensor.set_data_rate(self._data_rate)
        self._sensor.set_alert_ready_polarity(self._comp_polarity)
        self._sensor.set_comparator_queue(self._comp_queue_length)
        self._sensor.enable_latching_comparator(self._comp_latch)
        self._sensor.set_lo_thresh(self._lo_thresh)
        self._sensor.set_hi_thresh(self._hi_thresh)

        if self._diffmode:
            self._sensor.set_differential_mode(self._diff_channel1, self._diff_channel2)
        else:
            self._sensor.set_single_channel(self._single_channel)

        if self._comp_mode_traditional:
            self._sensor.set_comp_mode_traditional()
        else:
            self._sensor.set_comp_mode_window()

        if self._continuous:
            self._sensor.start_continuous()
        else:
            self._sensor.start_singleshot()

    def _internal_loop(self, pipe: Connection) -> None:
        # this is a loop that manages the running of the sensor.

        # Initialize Sensor
        self._sensor = self._initialize_sensor()

        # Write any settings, config, etc
        self._configure_sensor()

        # TODO: add more control over which are read/etc
        while True:
            # poll the pipe
            if pipe.poll():
                message = pipe.recv()

                # if pipe says "read", send out the data into the pipe
                if message[0] == "read":
                    pipe.send(self._sensor.read())
                elif message[0] == "new data available":
                    pipe.send(self._sensor.new_data_available())
