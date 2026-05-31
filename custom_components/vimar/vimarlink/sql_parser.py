"""SQL payload parser for Vimar web server responses."""

from __future__ import annotations

import logging
import sys

_LOGGER = logging.getLogger(__name__)


def parse_sql_payload(string: str | None) -> list[dict] | None:
    """Split string payload into dictionary array.

    FIX #20: aggiunto None guard in cima. Quando il webserver restituisce
    un tag payload vuoto, xml.find('.//payload').text e' None; chiamare
    None.split() sollevava AttributeError catturato dal BaseException handler
    e loggato come errore fuorviante. Ora restituisce None immediatamente.

    Example payload string:
    Response: DBMG-000
    NextRows: 2
    Row000001: 'MAIN_GROUPS'
    Row000002: '435,439,...'
    """
    if not string:
        return None

    return_list = []

    try:
        lines = string.split("\n")
        keys = []

        for line in lines:
            if not line:
                continue

            if line.find(":") == -1:
                raise Exception(f"Missing :-character in response line: {line}")

            prefix, values = line.split(":", 1)
            prefix = prefix.strip()

            if prefix in ["Response", "NextRows"]:
                continue

            values = values.strip()[1:-1].split("','")

            idx = 0
            row_dict = {}

            for value in values:
                if prefix == "Row000001":
                    keys.append(value)
                else:
                    row_dict[keys[idx]] = value
                    idx += 1

            if row_dict and len(row_dict) > 0:
                return_list.append(row_dict)

    except Exception as err:
        _, _, exc_tb = sys.exc_info()
        _LOGGER.warning(
            "Transient SQL parse error: %s at line %d - payload: %.200s",
            err,
            exc_tb.tb_lineno if exc_tb is not None else 0,
            string,
        )
        return None

    return return_list
