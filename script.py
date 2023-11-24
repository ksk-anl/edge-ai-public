from __future__ import annotations

import io
import json
import logging
import math
import os
import time

import pandas as pd
import psycopg2
import psycopg2.extensions
import requests
from requests.auth import HTTPBasicAuth

from edge_ai.controller.accel import LIS3DH
from edge_ai.controller.adc import ADS1015

BASE_PATH = os.path.dirname(__file__)


def _parse_config() -> dict[str, any]:
    # TODO: Parse and validate JSON contents
    with open(f"{BASE_PATH}/config.json") as f:
        config = json.load(f)
    return config


def _event_loop(
    motionsensor: LIS3DH,
    adc: ADS1015,
    conn: psycopg2.extensions.connection,
    config: dict[str, any],
) -> int:
    logging.info("Waiting for high ADC reading (Object Detection)")
    while True:
        time.sleep(config["adc_measurement_interval"])
        val = adc.read()
        if val > config["adc_threshold"]:
            break
    logging.info(f'Object detected. Waiting for {config["wait_time"]} seconds')

    time.sleep(config["wait_time"])

    logging.info(
        f'Instructing motion sensor to read for {config["window_length"]} seconds'
    )
    values = motionsensor.read_for(
        config["window_length"], timeformat=config["timeformat"]
    )
    results = [[row[0], math.sqrt(sum([x**2 for x in row[1]]))] for row in values]

    logging.info(f"Finished reading motion sensor. {len(results)} lines recorded")

    cursor = conn.cursor()

    # write to section table, get section id
    logging.info("Attempting to write to sections database")
    cursor.execute(
        "INSERT INTO sections (device_id, start_time) VALUES (%s, %s) RETURNING id;",
        (config["device_id"], results[0][0]),
    )
    conn.commit()

    id = cursor.fetchone()[0]
    logging.info(f"Finished writing to sections database (Section {id})")

    # Arrange data into correct columns
    logging.info("Preparing data for copy")
    final = pd.DataFrame(
        data={
            "section_id": [id] * len(results),
            "time": [row[0] for row in results],
            "gravity": [row[1] for row in results],
        }
    )

    # Load data into a file-like object for copying
    output_stream = io.StringIO()

    # If training mode is on, write to the gravities table
    if config["train"]:
        final.to_csv(output_stream, header=False, index=False)

        # Write data to gravities table
        output_stream.seek(0)

        logging.info("Attempting to copy data to gravities table")
        cursor.copy_from(output_stream, "gravities", sep=",")
        conn.commit()

        logging.info("Finished writing to gravities table")

    # If not in training mode, send the data to real-time scoring
    else:
        res = None
        if config["rts_url"] != "":
            # Make rts_url more intuituve to work with
            res = requests.post(
                url=config["rts_url"],
                json={"data": final.to_dict(orient='records')},
            )

            logging.info(f"Wrote to RTS with response {res}")
        else:
            # TODO: Save data that's being wasted?
            logging.warning("No RTS URL set. Will not attempt to POST.")

        cursor.close()
    return id


def main() -> None:
    config = _parse_config()

    # Preparing logger
    logging.basicConfig(
        filename=f'{BASE_PATH}/{config["logfile"]}',
        format="[%(asctime)s] %(levelname)s: %(message)s",
        level=logging.INFO,
    )

    logging.info(f'{" Beginning of script ":=^50}')

    try:
        # Initialize Sensors
        logging.info("Intializing sensors")
        motionsensor = LIS3DH.SPI(**config["motionsensor_spi"])
        adc = ADS1015.I2C(**config["adc_i2c"])
        logging.info("Sensors Initialized")

        # Configure sensors
        logging.info("Configuring sensors")
        motionsensor.set_datarate(5376)
        motionsensor.enable_axes()
        motionsensor.start()

        adc.start()
        logging.info("Sensors Configured")

        # Initialize Database connection
        logging.info("Connecting to Postgres Database")
        conn = psycopg2.connect(**config["rdb_access"])
        logging.info("Successfuly connected to Postgres Database")

        logging.info("Beginning measurement event loop")

        if config["number_measurements"] != "infinite":
            written_sections = []
            for i in range(config["number_measurements"]):
                written_sections.append(_event_loop(motionsensor, adc, conn, config))
                logging.info(
                    f'Measurement {i + 1} of {config["number_measurements"]} finished'
                )
            logging.info(f"Finished writing {i + 1} sections:")
            logging.info(", ".join([str(x) for x in written_sections]))
        else:
            logging.info("Measuring indefinitely...")
            while True:
                _event_loop(motionsensor, adc, conn, config)

    except Exception as e:
        logging.exception(e)

    logging.info("Shutting sensors down")
    motionsensor.stop()
    adc.stop()
    logging.info("Finishing script")


if __name__ == "__main__":
    main()
