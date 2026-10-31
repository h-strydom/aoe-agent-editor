"""Attach the telemetry harness to a scenario (see aoe2ed.telemetry)."""
from __future__ import annotations

from collections.abc import Sequence

from .. import telemetry
from .base import Ctx


def telemetry_harness(ctx: Ctx, *, players: Sequence[int] = (1, 2), track_vars: Sequence[str] = (),
                      interval_sec: int = 10, events: dict[str, int] | None = None,
                      mission_no: int = 0) -> dict:
    """Record resources/pop/kills per player and the given variables every `interval_sec` into
    <scenario>.xsdat (inside a campaign: <campaign name>.xsdat, shared by all missions; mission_no
    in the header tells them apart). events: {"trigger name": event_id} adds an event marker."""
    from .. import triggers as T
    var_ids = []
    for name in track_vars:
        ctx.var(name)
        var_ids.append(next(v.variable_id for v in ctx.scenario.trigger_manager.variables if v.name == name))
    ctx.xs(telemetry.xs_code(list(players), var_ids, interval_sec, mission_no))
    for trig, eid in (events or {}).items():
        t = T.find_trigger(ctx.scenario, trig)
        T.add_effect(t, telemetry.event_effect(eid), T.Resolver(ctx.scenario))
    return {"var_ids": dict(zip(track_vars, var_ids)), "events": events or {}}
