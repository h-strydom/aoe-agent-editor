"""Building blocks: tested generators for common mission mechanics. See base.Ctx."""
from __future__ import annotations

from .bank import load as bank_load
from .bank import resource_to_var, store as bank_store, var_to_resource
from .base import Ctx
from .boons import boon_offers
from .endings import earn, run_end
from .instrument import telemetry_harness
from .players import anchor
from .objectives import lose_if_destroyed, objective, survive
from .shop import pad_shop, perk_effects
from .waves import escalating, waves

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
    "run_end": run_end,
    "telemetry": telemetry_harness,
}

# Helpers that return data (effect dicts / wave lists) rather than editing the scenario.
HELPERS = {"escalating": escalating, "earn": earn, "var_to_resource": var_to_resource,
           "resource_to_var": resource_to_var}

__all__ = ["BLOCKS", "HELPERS", "Ctx", *BLOCKS, *HELPERS]
