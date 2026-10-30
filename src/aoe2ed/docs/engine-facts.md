# Engine facts (verified in game)

Behaviour of AoE2 DE that blocks and skills rely on. Each entry says how it was verified.
Add to this file whenever a playtest teaches something; never record guesses here.

## Files and loading
- Scenarios written by AoE2ScenarioParser 0.9.8 at version 1.59 load and run in the current
  game (build 101.103.54800, Oct 2026). *Smoke test, 2026-10-30.*
- `.aoe2campaign` layout is documented in `src/aoe2ed/campaign.py`; the writer reproduces all 47
  campaigns on the dev machine byte for byte, and generated campaigns load. *Round-trip + earlier tests.*

## XS
- XS embedded in a Script Call effect (the parser's XS trigger) compiles and runs, including
  `rule` blocks. *Smoke test: chat line at t=0.*
- Script Call messages compile in trigger order and XS requires definition before use, so the
  shared XS trigger must be the first trigger (`Ctx.flush_xs` does this).
- Int literals are limited to 9 digits. *xs-check, matches engine.*
- `xsCreateFile` writes `<profile>/profile/<scenario file name>.xsdat`; `xsWriteInt` writes raw
  little-endian int32. *Smoke test telemetry.*
- XS chat/print output does not appear in `logs/<session>/MainLog.txt`.
- `xsChatData("... %d", value)` substitutes the value. *Smoke test results message.*

## Players and victory
- A player who owns only Houses is defeated immediately; if that is the only enemy, the other
  side wins at t=0 even with victory condition Custom. Use the `anchor` block. *Smoke test.*

## Triggers
- Timer conditions on triggers enabled at start fire at that game time (waves at 20 s and 50 s
  logged at exactly t=20/t=50). *Smoke telemetry.*
- Display Timer with message `"Survive: %d"` shows the remaining seconds. *Smoke test.*
- `create_object` + `attack_move` over the spawn area sends spawned units to the target. *Smoke
  test: all 7 wave units engaged and died.*
- Create Decision shows a two-option popup; Decision Triggered fires for the chosen option. *Smoke test.*
- Modify Attribute quantities are integers unless the attribute is stored as a float (speed, rate
  of fire, work rate...). `MULTIPLY HIT_POINTS by 1.5` became "multiply by 1" — no effect. The
  trigger layer now rejects fractional quantities on integer attributes. *Smoke test.*
- Modify Attribute HIT_POINTS ADD 15 on ARCHER took effect in game. *Smoke replay, user-confirmed.*
- Several `create_object` effects at the same tile place only **one** unit ("+4 Men-at-Arms" gave 1).
  Give each unit its own tile with the `spawn` helper. *Crucible playtest, 2026-10-30.*

## Campaign bank (Store / Load / Delete Key Value)
*Verified with the kv_* test campaigns, 2026-10-19.*
- Values are int64 per campaign, stored in `profile/Player.nfp` as `PKEY:<campaign>:<key>`.
- They persist across game restarts. They are scoped to one campaign, and standalone scenarios get the default.
- The bank is not directional: any mission reads any key. Store overwrites; there is no history.
- Load Key Value returns the effect's quantity when the key is missing.
- Replaying an earlier mission asks "save your choices?"; answering No discards that visit's stores.
- Works in Return of Rome too.
- Full hub/run loop works in a generated campaign: currency earned in a run is stored, loaded as
  Gold in the replayed hub, perks bought there are stored, and the next run applies them (starting
  resources, Town Center HP). Winning and losing a run both end correctly. *Crucible playtest, 2026-10-30.*
- Open: whether stores survive a mission that ends in defeat or is quit mid-way. `run_end`
  always ends in victory to sidestep this.
