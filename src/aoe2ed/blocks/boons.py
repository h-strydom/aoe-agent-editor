"""Random two-choice boon offers during a mission, using the Create Decision popup."""
from __future__ import annotations

from .base import Ctx


def boon_offers(ctx: Ctx, *, boons: dict[str, dict], offers: list[dict], player: int = 1,
                prompt: str = "Choose a boon", name: str = "Boon") -> dict:
    """boons: {"swift": {"label": "Swift Feet: +15% speed", "effects": [...]}, ...}
    offers: [{"at": 600, "pairs": [["swift", "tough"], ["greed", "swift"]]}, ...]
    At each offer time one pair is picked at random (XS) and shown as a decision; the chosen
    boon's effects run. Each offer uses its own decision id."""
    created = []
    for k, offer in enumerate(offers, 1):
        pairs = offer["pairs"]
        pick = ctx.var(f"{name.lower()}_pick_{k}")
        var_id = _var_id(ctx, pick)
        fn = f"aoe2edPick{name}{k}"
        at = ctx.secs(offer["at"])
        # Script Call effects run the function defined in their message.
        ctx.trigger(f"{name} {k} roll", [{"type": "timer", "timer": max(1, at - 1)}], [
            {"type": "script_call", "message":
                f"void {fn}() {{ xsSetTriggerVariable({var_id}, xsGetRandomNumberLH(0, {len(pairs)})); }}"}])
        for i, (a, b) in enumerate(pairs):
            did = k * 10 + i
            t = f"{name} {k} offer {i}"
            ctx.trigger(t, [{"type": "timer", "timer": at},
                            {"type": "variable_value", "variable": pick, "comparison": "EQUAL", "quantity": i}],
                        [{"type": "create_decision", "decision_id": did, "message": prompt,
                          "message_option1": boons[a]["label"], "message_option2": boons[b]["label"]}])
            for opt, boon in ((1, a), (2, b)):
                ctx.trigger(f"{t} pick {boon}",
                            [{"type": "decision_triggered", "decision_id": did, "decision_option": opt}],
                            boons[boon]["effects"])
            created.append(t)
    return {"triggers": created}


def _var_id(ctx: Ctx, name: str) -> int:
    for v in ctx.scenario.trigger_manager.variables:
        if v.name == name:
            return v.variable_id
    raise KeyError(name)
