---
name: aoe2-xs
description: Write, lint and embed XS scripts for Age of Empires II DE scenarios, covering language rules, the documented API (xs_api tool), common patterns such as rules, trigger-variable bridges, randomness and file I/O, and debugging. Use when triggers alone can't express a mechanic, or when an XS error appears.
---

# AoE2 XS

XS is the game's C-like scripting language. aoe2ed embeds XS inside the scenario (in a Script Call
effect), so no external file has to travel with it.

## Workflow
1. Find functions with `xs_api("random")`, `xs_api("xsCreateFile")`, `xs_api("cAttributeGold")`. They come from the documented API bundled with xs-check: every function and constant, with its signature and doc.
2. Write the code and lint it with `xs_check(code=...)`. Fix every error. Review warnings: a float→int downcast is often fine.
3. Embed it: `xs_embed(handle, code)` on an open scenario, `xs:` in a campaign spec, or `ctx.xs()` in a block.

## Language rules that bite
- Types: `int`, `float`, `bool`, `string`, `vector`. Declare before use. No arrays as values; use the `xsArray*` functions.
- Functions and globals must be **defined before use**, even across Script Call effects, which compile in trigger order.
- Int literals have at most 9 digits.
- Parameters need default values: `void f(int a = 0)`.
- Rules: `rule name active minInterval 5 { ... }`. Call `xsDisableSelf()` for run-once rules. `highFrequency` runs every game tick.
- A Script Call **effect** runs the function defined in its message: `void myFn() { ... }`. A Script Call **condition** runs `xs_function` and expects a bool.

## Patterns
- **Trigger variables ↔ XS:** `xsTriggerVariable(id)` and `xsSetTriggerVariable(id, v)`. Ids come from `variables_list`.
- **Random choice:** `xsSetTriggerVariable(id, xsGetRandomNumberLH(0, n))`, then triggers compare the variable.
- **Chat output:** `xsChatData("Earned %d", value)`.
- **Player state:** `xsPlayerAttribute(p, cAttributeGold)` (returns a float), `xsGetObjectCount(p, unitId)`.
- **Time:** `xsGetGameTime()` returns seconds.
- **File I/O:** `xsCreateFile(append)` writes `<scenario>.xsdat` in the profile. Then `xsWriteInt/Float/String`, `xsCloseFile()`. `xsOpenFile(name)` / `xsRead*` read it back. The telemetry harness is built on this, and it can carry data between scenarios outside a campaign, unverified.

## Debugging
- Before the game: `xs_check`. In game, XS errors show a popup when the scenario starts. Ask the player for the exact text.
- `xsChatData` breadcrumbs, or telemetry events (`aoe2edTelemetryEvent(id)`), show how far the code got.
- XS output does not reach the game log files.
