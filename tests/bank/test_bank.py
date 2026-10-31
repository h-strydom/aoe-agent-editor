import json
import shutil
import zlib

import make_fixture
import pytest

from aoe2ed import bank as bankmod
from aoe2ed.bank import Bank, BankFormatError, GameRunningError, load
from aoe2ed.bank.__main__ import main


@pytest.fixture
def nfp(tmp_path):
    p = tmp_path / "Player.nfp"
    shutil.copy(make_fixture.FIXTURE, p)
    return p


@pytest.fixture(autouse=True)
def game_not_running(monkeypatch):
    import aoe2ed.game

    monkeypatch.setattr(aoe2ed.game, "is_running", lambda: False)


def test_fixture_is_current():
    assert make_fixture.FIXTURE.read_bytes() == make_fixture.build()


def test_read(nfp):
    b = load(nfp)
    assert b.campaigns() == ["3kcam1", "3kcam2", "crucible", "kv_persist"]
    assert b.keys("crucible") == {"meta_gold": 250, "perk_armor": 1, "best_wave": (1 << 40) + 7}
    assert b.keys("3kcam1") == {"LuBuExecuted(1)orSpared(2)": 2, "VillagersFound": -1}
    assert b.keys("3kcam2") == {"LüBuRecruited(1)Yes(2)No": 0}
    assert b.keys("nope") == {}
    assert b.get("kv_persist", "kvp_key") == 1234


def test_roundtrip_unchanged_is_byte_identical(nfp, tmp_path):
    out = tmp_path / "out.nfp"
    assert load(nfp).save(out) is None  # no backup: target didn't exist
    assert out.read_bytes() == nfp.read_bytes()


def test_noop_set_keeps_bytes(nfp):
    b = load(nfp)
    b.set("kv_persist", "kvp_key", 1234)
    assert b.to_bytes() == nfp.read_bytes()


def test_raw_rebuild_matches_decompressed(nfp):
    b = load(nfp)
    assert b.raw() == zlib.decompress(nfp.read_bytes(), -15)


def test_set_delete_roundtrip(nfp):
    original = zlib.decompress(nfp.read_bytes(), -15)
    b = load(nfp)
    b.set("crucible", "meta_gold", 900)       # update in place
    b.set("crucible", "mission", 3)           # new key: appended
    b.set("new camp", "x", -(1 << 63))        # space in campaign, int64 min
    assert b.delete("kv_persist", "kvp_key")
    assert not b.delete("kv_persist", "kvp_key")
    backup = b.save()
    assert backup.read_bytes() == make_fixture.FIXTURE.read_bytes()

    r = load(nfp)
    assert r.keys("crucible") == {"meta_gold": 900, "perk_armor": 1,
                                  "best_wave": (1 << 40) + 7, "mission": 3}
    assert r.keys("new camp") == {"x": -(1 << 63)}
    assert "kv_persist" not in r.campaigns()
    assert r.items()[-1] == ("new camp", "x", -(1 << 63))
    # everything outside the bank section is untouched
    raw = r.raw()
    assert raw.startswith(make_fixture.head()) and raw.endswith(make_fixture.tail())
    assert raw != original
    # and a second unchanged save keeps the new bytes
    assert r.to_bytes() == nfp.read_bytes()


def test_empty_bank_still_found(nfp):
    b = load(nfp)
    for c in b.campaigns():
        b.delete_campaign(c)
    b.save()
    e = load(nfp)
    assert len(e) == 0 and e.campaigns() == []
    e.set("crucible", "meta_gold", 1)
    e.save()
    assert load(nfp).keys("crucible") == {"meta_gold": 1}


def test_backup_names_unique(nfp):
    b = load(nfp)
    b.set("crucible", "meta_gold", 1)
    first = b.save()
    b.set("crucible", "meta_gold", 2)
    second = b.save()
    assert first != second and first.exists() and second.exists()


def test_refuses_while_game_running(nfp, monkeypatch):
    import aoe2ed.game

    monkeypatch.setattr(aoe2ed.game, "is_running", lambda: True)
    b = load(nfp)
    b.set("crucible", "meta_gold", 1)
    with pytest.raises(GameRunningError):
        b.save()
    assert nfp.read_bytes() == make_fixture.FIXTURE.read_bytes()
    assert list(nfp.parent.glob("*.bak")) == []


@pytest.mark.parametrize("campaign,key,value,exc", [
    ("a:b", "k", 1, ValueError),
    ("", "k", 1, ValueError),
    ("c", "", 1, ValueError),
    ("c", "k", True, TypeError),
    ("c", "k", 1.5, TypeError),
    ("c", "k", 1 << 63, ValueError),
])
def test_set_validation(nfp, campaign, key, value, exc):
    with pytest.raises(exc):
        load(nfp).set(campaign, key, value)


def test_bad_files(tmp_path):
    with pytest.raises(BankFormatError):
        Bank(b"not deflate at all \xff\xff")
    c = zlib.compressobj(9, zlib.DEFLATED, -15)
    with pytest.raises(BankFormatError):
        Bank(c.compress(b"\0" * 100) + c.flush())


def test_find_profiles(tmp_path, monkeypatch, nfp):
    monkeypatch.setenv("AOE2DE_PROFILE", str(tmp_path))
    (tmp_path / "profile").mkdir()
    assert bankmod.find_profiles() == []
    shutil.copy(nfp, tmp_path / "profile" / "Player.nfp")
    assert bankmod.find_profiles() == [tmp_path / "profile" / "Player.nfp"]
    assert load().keys("kv_persist") == {"kvp_key": 1234}


# --- CLI ------------------------------------------------------------------------------

def run(capsys, *argv):
    code = main([str(a) for a in argv])
    out = capsys.readouterr()
    return code, out.out, out.err


def test_cli_list_show_export(nfp, capsys):
    code, out, _ = run(capsys, "-f", nfp, "list")
    assert code == 0 and "crucible\t3" in out and "3kcam1\t2" in out
    code, out, _ = run(capsys, "-f", nfp, "show", "kv_persist")
    assert out.strip() == "kvp_key\t1234"
    assert run(capsys, "-f", nfp, "show", "missing")[0] == 1
    code, out, _ = run(capsys, "-f", nfp, "export", "crucible", "--json")
    assert json.loads(out) == {"campaign": "crucible", "keys": load(nfp).keys("crucible")}
    code, out, _ = run(capsys, "-f", nfp, "export")
    assert set(json.loads(out)["campaigns"]) == set(load(nfp).campaigns())


def test_cli_set_delete(nfp, tmp_path, capsys):
    out = tmp_path / "edited.nfp"
    assert run(capsys, "-f", nfp, "set", "crucible", "meta_gold", "0x10", "-o", out)[0] == 0
    assert load(out).get("crucible", "meta_gold") == 16
    assert nfp.read_bytes() == make_fixture.FIXTURE.read_bytes()  # -o leaves the source alone

    assert run(capsys, "-f", nfp, "set", "crucible", "meta_gold", "5", "--dry-run")[0] == 0
    assert nfp.read_bytes() == make_fixture.FIXTURE.read_bytes()

    assert run(capsys, "-f", nfp, "delete", "3kcam1", "VillagersFound")[0] == 0
    assert "VillagersFound" not in load(nfp).keys("3kcam1")
    assert run(capsys, "-f", nfp, "delete", "3kcam1", "VillagersFound")[0] == 1
    assert run(capsys, "-f", nfp, "delete", "crucible", "--all")[0] == 0
    assert "crucible" not in load(nfp).campaigns()
    assert run(capsys, "-f", nfp, "delete", "crucible")[0] == 2


def test_cli_export_import(nfp, tmp_path, capsys):
    _, exported, _ = run(capsys, "-f", nfp, "export", "crucible", "--json")
    doc = json.loads(exported)
    doc["keys"] = {"meta_gold": 7, "new_perk": 1}
    f = tmp_path / "in.json"
    f.write_text(json.dumps(doc), "utf-8")

    assert run(capsys, "-f", nfp, "import", f)[0] == 0
    assert load(nfp).keys("crucible") == {"meta_gold": 7, "perk_armor": 1,
                                          "best_wave": (1 << 40) + 7, "new_perk": 1}
    assert run(capsys, "-f", nfp, "import", f, "--replace")[0] == 0
    assert load(nfp).keys("crucible") == {"meta_gold": 7, "new_perk": 1}

    all_doc = tmp_path / "all.json"
    all_doc.write_text(json.dumps({"campaigns": {"other": {"a": 1}}}), "utf-8")
    assert run(capsys, "-f", nfp, "import", all_doc)[0] == 0
    assert load(nfp).keys("other") == {"a": 1}
