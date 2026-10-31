---
name: aoe2-editor-ui
description: Drive the Age of Empires II DE in-game editor and menus through desktop automation (computer use) for the few things the file tools cannot do, such as opening a scenario or campaign to play, generating a map from a random map script, using the editor's Test button, or confirming that a generated file opens cleanly. Use only after checking that no aoe2-editor tool or run_python covers the task.
---

# AoE2 editor and menu automation

Almost everything a human does in the editor maps onto file edits (see `guide("coverage")`). Use the
UI only for these:

| Task | Why it needs the UI |
|---|---|
| Start a scenario or campaign to play | No command-line switch opens one |
| Generate a map from an RMS script | The generator runs inside the game |
| Editor "Test" button / live preview | Runs inside the editor |
| Check that a file opens in the editor | Final check after big structural changes |

## Rules
- Get the person's OK for desktop control first; some people prefer to play tests themselves. Ask for access to the game window (on Windows the process is `AoE2DE_s.exe`).
- Launch through `game_launch()` (Steam). The title screen takes about 20–40 s.
- Take a screenshot before every click. Menu positions depend on resolution and UI scale, so never replay coordinates from an earlier session.
- Don't change game settings, sign in or out, or touch multiplayer or the store.
- When done, return to the main menu or quit as the person prefers.

## Menu paths (DE, 2026)
- **Play a scenario:** Single Player → Scenario → choose a file from the list → Start Game.
- **Play a campaign:** Single Player → Campaigns → scroll to custom campaigns (the internal `name`) → choose a mission → Start. On a replay, the "save your choices for future scenarios?" dialog appears: answer **Yes** to keep bank writes.
- **Open in editor:** main menu → Editors → Scenario Editor → Open.
- **RMS map:** Scenario Editor → New scenario → Map tab → Random Map Script → Generate. Save it, then continue with the file tools (`scenario_open`).

Verify each step on screen. If a label differs, read the screen rather than guessing, and add the correction here.
