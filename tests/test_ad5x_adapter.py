from forge.adapters.ad5x import AD5XAdapter
from forge import fixtures


def test_map_status_ready_is_idle():
    assert AD5XAdapter._map_status("ready") == "idle"


def test_map_status_printing_is_busy():
    assert AD5XAdapter._map_status("printing") == "printing"


def test_remote_name_sanitizes_spaces_and_symbols():
    assert AD5XAdapter._remote_name("/tmp/Red + Blue pair.gcode") == "Red_Blue_pair.gcode"


def test_build_mappings_from_fixture():
    slots = fixtures.load("ad5x", "ifs_slot_state")["matlStationInfo"]["slotInfos"]
    tool_cols = ["#FF0000", "#0000FF"]
    maps = AD5XAdapter.build_mappings(tool_cols, slots)
    assert len(maps) == 2
    assert maps[0]["toolId"] == 0
    assert maps[0]["slotId"] == 1
    assert maps[1]["toolId"] == 1
    assert maps[1]["slotId"] == 3


def test_status_uses_injected_detail_fetcher():
    def fetcher():
        return {"status": "ready"}

    adapter = AD5XAdapter("printer.local", "SERIAL", "CHECK", detail_fetcher=fetcher)
    assert adapter.status() == "idle"


def test_list_files_joins_names_to_slice_metadata():
    posted = []

    def post(path, body):
        posted.append((path, body))
        return {
            "gcodeList": ["ready.3mf", "raw-project.3mf"],
            "gcodeListDetail": [{
                "gcodeFileName": "ready.3mf",
                "gcodeToolCnt": 2,
                "printingTime": 3600,
                "totalFilamentWeight": 42.5,
            }],
        }

    adapter = AD5XAdapter("printer.local", "SERIAL", "CHECK", api_poster=post)

    assert adapter.list_files() == [
        {
            "name": "ready.3mf",
            "gcodeFileName": "ready.3mf",
            "gcodeToolCnt": 2,
            "printingTime": 3600,
            "totalFilamentWeight": 42.5,
        },
        {"name": "raw-project.3mf"},
    ]
    assert posted == [("/gcodeList", {"serialNumber": "SERIAL", "checkCode": "CHECK"})]
