"""Campaign screens: reading the game's layouts, building layouts, installing a campaign as a local mod."""
from __future__ import annotations

import json

import pytest

from aoe2ed import screens
from aoe2ed.campaign import Campaign, CampaignScenario

OFFICIAL_LAYOUT = """﻿{
   "BackgroundMaterial": "CampaignBackgroundAscent",
   "Widgets": [
      {"Widget": {"Type": "Label", "Name": "TitleLabel", "ZPlane": 2, "Text": "IDS_CAMPAIGN_X", "ChildWidgets": []}},
      {"Widget": {"Type": "Button", "Name": "ScenarioButton2", "ZPlane": 1,
                  "StateMaterials": {"StateNormal": {"Material": "CampaignIconScoutNormal"}},
                  "ChildWidgets": [{"Widget": {"Type": "CampaignTitle", "Text": "IDS_2"}}]}},
      {"Widget": {"Type": "Button", "Name": "ScenarioButton1", "ZPlane": 1,
                  "StateMaterials": {"StateNormal": {"Material": "CampaignIconVillagerHunterNormal"}},
                  "ChildWidgets": [{"Widget": {"Type": "CampaignTitle", "Text": "IDS_1"}}]}}
   ]
}"""
OFFICIAL_INTRO = '{"Scenarios": [{"IntroSequence": {"Duration": 09.21}}, {"IntroSequence": {}}]}'


@pytest.fixture
def game_dir(tmp_path):
    folder = tmp_path / "game" / screens.GAME_CAMPAIGN_DIRS["ror"]
    folder.mkdir(parents=True)
    (folder / "aoecam1_layout.json").write_text(OFFICIAL_LAYOUT, encoding="utf-8")
    (folder / "aoecam1.json").write_text(OFFICIAL_INTRO, encoding="utf-8")
    return tmp_path / "game"


def test_read_json_tolerates_what_the_game_does(game_dir):
    intro = screens.read_json(game_dir / screens.GAME_CAMPAIGN_DIRS["ror"] / "aoecam1.json")
    assert intro["Scenarios"][0]["IntroSequence"]["Duration"] == 9.21


def test_official_screens_lists_layouts(game_dir):
    [s] = screens.official_screens("ror", game_dir)
    assert s == {"name": "aoecam1", "title": "IDS_CAMPAIGN_X", "background": "CampaignBackgroundAscent",
                 "missions": 2, "icons": ["CampaignIconVillagerHunter", "CampaignIconScout"], "intro": True}


def test_layout_from_official_sets_text_and_drops_zplane(game_dir):
    lay = screens.layout_from_official("aoecam1", title="My Egypt", labels=["1. Hunt", "2. Scout"],
                                       game="ror", game_dir=game_dir)
    assert "ZPlane" not in json.dumps(lay)
    w = {x["Widget"]["Name"]: x["Widget"] for x in lay["Widgets"]}
    assert w["TitleLabel"]["Text"] == "My Egypt"
    assert w["ScenarioButton1"]["ChildWidgets"][0]["Widget"]["Text"] == "1. Hunt"
    assert w["ScenarioButton2"]["ChildWidgets"][0]["Widget"]["Text"] == "2. Scout"
    with pytest.raises(ValueError, match="2 mission buttons"):
        screens.layout_from_official("aoecam1", labels=["one"], game="ror", game_dir=game_dir)
    with pytest.raises(ValueError, match="2 intros"):
        screens.intro_from_official("aoecam1", missions=3, game="ror", game_dir=game_dir)


def test_build_layout():
    lay = screens.build_layout(title="T", background="Bg", buttons=[{"x": 10, "y": 20, "icon": "CampaignIconChariot",
                                                                   "label": "1. A"}],
                               user_materials=[{"Material": "Bg", "FileName": "bg.dds", "Blend": "None"}])
    assert list(lay) == ["UserMaterials", "BackgroundMaterial", "Widgets"]
    button = lay["Widgets"][1]["Widget"]
    assert button["Name"] == "ScenarioButton1" and button["ViewPort"]["xorigin"] == 10
    assert button["StateMaterials"]["StateHover"]["Material"] == "CampaignIconChariotHover"
    assert button["ChildWidgets"][0]["Widget"]["Type"] == "CampaignTitle"


def test_install_campaign_mod(tmp_path):
    camp = Campaign("Some Display Name", [CampaignScenario("One", "one.aoe2scenario", b"scenario")])
    src = camp.write(tmp_path / "my_campaign.aoe2campaign")
    profile = tmp_path / "profile"
    image = tmp_path / "bg.dds"
    image.write_bytes(b"dds")
    res = screens.install_campaign_mod(src, "My Mod", layout={"Widgets": []}, intro={"Scenarios": []},
                                       files=[image], game="ror", profile=profile)
    folder = profile / "mods" / "local" / "My Mod" / screens.GAME_CAMPAIGN_DIRS["ror"]
    assert Campaign.read(folder / "my_campaign.aoe2campaign").name == "my_campaign"
    assert {p.name for p in folder.iterdir()} == {"my_campaign.aoe2campaign", "my_campaign_layout.json",
                                                  "my_campaign.json", "bg.dds"}
    assert json.loads((profile / "mods" / "local" / "My Mod" / "info.json").read_text())["Title"] == "My Mod"
    assert res["enabled"] is None and res["next"]
    (profile / "mods" / "mod-status.json").write_text(json.dumps(
        {"Mods": [{"Path": "local//My Mod", "Enabled": True}]}), encoding="utf-8")
    assert screens.mod_enabled("My Mod", profile) is True
