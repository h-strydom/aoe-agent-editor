"""Building blocks: tested generators for common mission mechanics. See base.Ctx."""
from __future__ import annotations

from .bank import load as bank_load
from .bank import resource_to_var, var_to_resource
from .bank import store as bank_store
from .ai import ai_signal, claim_base, start_ai
from .base import Ctx
from .boons import boon_offers
from .fog import reveal
from .endings import earn, run_end
from .factions import random_faction
from .instrument import telemetry_harness
from .objectives import lose_if_destroyed, objective, survive
from .players import anchor
from .shop import pad_shop, perk_effects
from .story import choice, escort, say_var
from .waves import escalating, spawn, waves

BLOCKS = {
    "anchor": anchor,
    "survive": survive,
    "objective": objective,
    "lose_if_destroyed": lose_if_destroyed,
    "waves": waves,
    "bank_load": bank_load,
    "bank_store": bank_store,
    "pad_shop": pad_shop,
    "perk_effects": perk_effects,
    "boon_offers": boon_offers,
    "choice": choice,
    "escort": escort,
    "random_faction": random_faction,
    "run_end": run_end,
    "telemetry": telemetry_harness,
    "start_ai": start_ai,
    "claim_base": claim_base,
    "reveal": reveal,
}

# Helpers that return data (effect dicts / wave lists) rather than editing the scenario.
HELPERS = {"escalating": escalating, "spawn": spawn, "say_var": say_var, "earn": earn, "var_to_resource": var_to_resource,
           "resource_to_var": resource_to_var, "ai_signal": ai_signal}

__all__ = ["BLOCKS", "HELPERS", "Ctx", *BLOCKS, *HELPERS]
