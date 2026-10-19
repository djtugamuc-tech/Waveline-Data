import json
from pathlib import Path
import tempfile
import unittest
from fetch_stations import COUNTRIES, MIN_STATIONS, filter_stations, update_snapshot


def rows(country):
    return [dict(stationuuid=f"{country}-{i}", name=f"Radio {i}",
                 url_resolved=f"https://stream.example/{country}/{i}", countrycode=country,
                 lastcheckok=1, bitrate=128, clickcount=100 - i) for i in range(MIN_STATIONS)]


class SnapshotTest(unittest.TestCase):
    def test_filters_broken_and_duplicate_streams(self):
        source = rows("PT")
        source += [dict(source[0], stationuuid="duplicate"), dict(source[1], lastcheckok=0)]
        result = filter_stations(source, "PT", set())
        self.assertEqual(MIN_STATIONS, len(result))
        self.assertNotIn("lastcheckok", result[0])

    def test_partial_failure_preserves_entire_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "data"
            update_snapshot(output, lambda c, _: rows(c), ["unused"])
            before = {p.name: p.read_bytes() for p in output.iterdir()}
            with self.assertRaises(ValueError):
                update_snapshot(output, lambda c, _: [] if c == "CH" else rows(c), ["unused"])
            self.assertEqual(before, {p.name: p.read_bytes() for p in output.iterdir()})

    def test_unchanged_data_preserves_timestamp_and_hashes(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "data"
            self.assertTrue(update_snapshot(output, lambda c, _: rows(c), ["unused"]))
            before = (output / "index.json").read_bytes()
            self.assertFalse(update_snapshot(output, lambda c, _: rows(c), ["unused"]))
            self.assertEqual(before, (output / "index.json").read_bytes())
            self.assertEqual(set(COUNTRIES), set(json.loads(before)["countries"]))


if __name__ == "__main__":
    unittest.main()
