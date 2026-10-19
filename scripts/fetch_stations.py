#!/usr/bin/env python3
"""Fetch a validated Radio Browser snapshot; publish nothing on partial failure."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import socket
import tempfile
from datetime import datetime, timezone
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

COUNTRIES = ("PT", "ES", "FR", "NL", "CH", "DE")
FIELDS = ("stationuuid", "name", "url_resolved", "homepage", "favicon", "tags",
          "countrycode", "language", "codec", "bitrate", "clickcount")
USER_AGENT = "Waveline/1.0 (github.com/djtugamuc-tech/Waveline-Data)"
MIN_STATIONS = 25
MAX_BYTES = 10 * 1024 * 1024


def discover_servers():
    addresses = {item[4][0] for item in socket.getaddrinfo(
        "all.api.radio-browser.info", 443, type=socket.SOCK_STREAM)}
    servers = set()
    for address in addresses:
        try:
            host = socket.gethostbyaddr(address)[0].rstrip(".")
            if host.endswith(".api.radio-browser.info"):
                servers.add(host)
        except OSError:
            continue
    if not servers:
        raise RuntimeError("No verified Radio Browser server could be resolved")
    result = list(servers)
    random.SystemRandom().shuffle(result)
    return result


def fetch_country(country, servers):
    query = urlencode(dict(countrycode=country, hidebroken="true", order="clickcount",
                           reverse="true", limit=500))
    for server in servers:
        try:
            request = Request(f"https://{server}/json/stations/search?{query}",
                              headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
            with urlopen(request, timeout=30) as response:
                payload = response.read(MAX_BYTES + 1)
            if len(payload) > MAX_BYTES:
                raise ValueError("Response exceeds size limit")
            rows = json.loads(payload)
            if not isinstance(rows, list) or len(rows) > 500:
                raise ValueError("Expected station list")
            return rows
        except (OSError, ValueError) as error:
            print(f"{country}: {server}: {type(error).__name__}; trying next server")
    raise RuntimeError(f"All Radio Browser servers failed for {country}")


def filter_stations(rows, country, seen_urls):
    stations = []
    seen_ids = set()
    for row in rows:
        if not isinstance(row, dict) or row.get("lastcheckok") != 1:
            continue
        url = str(row.get("url_resolved") or "").strip()
        uuid = str(row.get("stationuuid") or "").strip()
        name = str(row.get("name") or "").strip()
        if (row.get("countrycode") != country or not uuid or not name or
                urlsplit(url).scheme not in ("http", "https") or not urlsplit(url).netloc or
                url in seen_urls or uuid in seen_ids):
            continue
        station = {field: str(row.get(field) or "").strip() for field in FIELDS}
        for field in ("bitrate", "clickcount"):
            station[field] = max(0, int(row.get(field) or 0))
        station.update(stationuuid=uuid, name=name, url_resolved=url)
        stations.append(station)
        seen_urls.add(url)
        seen_ids.add(uuid)
    if len(stations) < MIN_STATIONS:
        raise ValueError(f"{country}: only {len(stations)} valid stations; minimum {MIN_STATIONS}")
    return stations


def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def update_snapshot(output, fetch=fetch_country, servers=None):
    servers = discover_servers() if servers is None else servers
    seen = set()
    payloads = {}
    countries = {}
    for country in COUNTRIES:
        rows = filter_stations(fetch(country, servers), country, seen)
        payload = encode(rows)
        filename = f"stations_{country}.json"
        payloads[filename] = payload
        countries[country] = dict(file=filename, count=len(rows),
                                  sha256=hashlib.sha256(payload).hexdigest())
    old_index = output / "index.json"
    if old_index.exists():
        previous = json.loads(old_index.read_text())
        if previous.get("countries") == countries and all(
                (output / name).exists() and (output / name).read_bytes() == payload
                for name, payload in payloads.items()):
            print("Snapshot unchanged")
            return False
    index = dict(updatedAt=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                 countries=countries)
    payloads["index.json"] = encode(index)
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".stations-", dir=output.parent) as staging:
        for name, payload in payloads.items():
            (Path(staging) / name).write_bytes(payload)
        for name in payloads:
            os.replace(Path(staging) / name, output / name)
    print("Snapshot updated: " + ", ".join(f"{c}: {v['count']}" for c, v in countries.items()))
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data"))
    args = parser.parse_args()
    update_snapshot(args.output)
