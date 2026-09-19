#!/usr/bin/env python

import argparse
import json
import logging
import re
import sys
import time
from collections import defaultdict
from typing import Any, Generator

import requests
from bs4 import BeautifulSoup
from requests import Response

import openapi_client
from openapi_client import PartyRequest
from openapi_client.api.default_api import DefaultApi

LOG_FORMATTER = logging.Formatter(
    '[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt="%Y-%m-%dT%H:%M:%SZ")

API_HOST = "127.0.0.1:8000"
DEPUTIES_URL = "https://www.cdep.ro/ords/pls/parlam/structura2015.de?idl=1"
SENATORS_URL = "https://www.cdep.ro/ords/pls/parlam/structura2015.de?idl=1&cam=1"


def get_logger(name: str = None, level: int = logging.DEBUG) -> logging.Logger:

    if not name:
        name = __name__
    root_logger = logging.getLogger(name)
    root_logger.setLevel(level)

    fileHandler = logging.FileHandler("app.log_{}".format(
        time.strftime("%Y-%m-%d_%H-%M")), mode="a")
    fileHandler.setFormatter(LOG_FORMATTER)
    root_logger.addHandler(fileHandler)

    consoleHandler = logging.StreamHandler(sys.stdout)
    consoleHandler.setFormatter(LOG_FORMATTER)
    root_logger.addHandler(consoleHandler)

    return root_logger


_log = get_logger(__name__)


def get_api_client(api_host: str) -> Generator[DefaultApi, Any, None]:
    configuration = openapi_client.configuration.Configuration()
    configuration.host = api_host
    api_client = openapi_client.ApiClient(configuration)
    client = DefaultApi(api_client)

    return client


def fetch_page(url: str) -> Response:
    return requests.get(url)


def fetch_parliamentarians(page: Response) -> defaultdict[Any, int]:
    re_expression = "/ords/pls/parlam/structura2015\.gp\?idg=.*"
    data = defaultdict(int)

    soup = BeautifulSoup(page.content, "html.parser")

    _parliamentarians = soup.find_all(
            "div",
            class_="grup-parlamentar-list grupuri-parlamentare-list"
    )

    parliamentarians = _parliamentarians[0].find_all("a") \
        if len(_parliamentarians) > 1 \
        else _parliamentarians.find_all("a")  # fetch only those active

    for entry in parliamentarians:
        if re.match(re_expression, entry["href"]):
            party = entry.text
            data[party] = 1 \
                if data.get(party) == None \
                else data.get(party) + 1

    return data


def main(
        file_output: str = None,
        data_file: str = None
) -> None:
    parliamentarians = defaultdict(dict)

    if data_file is None:
        _log.debug("Fetching deputies page")
        deputies_page = fetch_page(DEPUTIES_URL)
        _log.debug("Fetching senators page")
        senators_page = fetch_page(SENATORS_URL)

        _log.debug(
            "Getting a yummy beautifulsoup out of the deputies page " +
            "and building data"
        )
        deputies = fetch_parliamentarians(deputies_page)
        for party in list(deputies.keys()):
            parliamentarians[party]["deputies"] = deputies.get(party, 0)

        _log.debug(
            "Getting a yummy beautifulsoup out of the senators page " +
            "and building data"
        )
        senators = fetch_parliamentarians(senators_page)
        for party in list(senators.keys()):
            parliamentarians[party]["senators"] = senators.get(party, 0)

        parties_list = list(parliamentarians.keys())
        for party in parties_list:
            parliamentarians[party]["total"] = \
                parliamentarians[party].get("deputies", 0) + \
                parliamentarians[party].get("senators", 0)

        if file_output is not None:
            _log.info(f"Writing data results to outputfile {file_output}")
            with open(file_output, "w") as fobj:
                json.dump(parliamentarians, fobj, indent=4)
            _log.debug(f"Done writing data results to {file_output}")
    else:
        parliamentarians = json.load(open(data_file, "rb"))

    _log.info("Populating the database using the API")
    api_client = get_api_client(API_HOST)
    all_db_parties = api_client.read_all_get()

    parties_list = list(parliamentarians.keys())
    for party in parties_list:
        party_data = parliamentarians[party]

        name = party
        deputies = party_data.get("deputies", 0)
        senators = party_data.get("senators", 0)
        total = party_data.get("total", 0)

        party_request = PartyRequest(
            name=name,
            deputies=deputies,
            senators=senators,
            total=total
        )

        party_id = None
        for db_party in all_db_parties:
            if party == db_party["name"]:
                party_id = db_party["id"]

        if party_id is not None:
            api_client.update_party_parties_party_id_put(
                party_id=party_id,
                party_request=party_request
            )
            continue

        api_client.create_party_parties_post(
            party_request
        )

    _log.info("Successfully populated the database through the API")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fetch all deputies and senators per party from the " + \
                    "Romanian parliament and populate into the database " + \
                    "by calling the API",
        epilog="Calls are made over non secure, non authorized, localhost"
    )
    parser.add_argument("-o", "--output", dest="file_output",
                        type=str, required=False,
                        help="Write to this file the data fetched " + \
                             "from the websites before commiting")
    parser.add_argument("-f", "--file", dest="data_file",
                        type=str, required=False,
                        help="Use this JSON data file to load the data " + \
                             "instead of fetching from the websites")
    args = parser.parse_args()

    file_output = None
    if args.file_output:
        file_output = args.file_output

    data_file = None
    if args.data_file:
        data_file = args.data_file
        file_output = None
        _log.debug(f"Using data file: {data_file}. Deactivated file output")

    if file_output:
        _log.debug(f"Using file output: {file_output}")

    _log.info("Starting")
    main(file_output=file_output, data_file=data_file)
    _log.info("Application finished successfully")