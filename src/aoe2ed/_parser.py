"""Single import point for AoE2ScenarioParser, configured for non-interactive use.

The parser prints progress with emoji to stdout, which breaks MCP's stdio transport and
cp1252 consoles. Everything in aoe2ed imports the parser through this module.
"""
from __future__ import annotations

import warnings

# The parser's datasets contain invalid escape sequences in docstrings.
warnings.filterwarnings("ignore", category=SyntaxWarning)

from AoE2ScenarioParser import settings  # noqa: E402

settings.PRINT_STATUS_UPDATES = False
settings.NOTIFY_UNKNOWN_BYTES = False
settings.SHOW_VARIANT_WARNINGS = False
settings.SHOW_SCENARIO_VERSION_WARNINGS = False
settings.ALLOW_OVERWRITING_SOURCE = True  # aoe2ed handles backups itself
settings.ENABLE_XS_CHECK_INTEGRATION = False  # we run xs-check explicitly; see aoe2ed.xs

from AoE2ScenarioParser.scenarios.scenario_store import getters as _getters  # noqa: E402
from AoE2ScenarioParser.sections.retrievers.retriever_object_link import RetrieverObjectLink  # noqa: E402


def _unsupported_without_class_patch(self, class_reference, uuid) -> bool:
    """Upstream replaces the property on the *class* when an attribute is unsupported by a
    scenario's version, so after opening one old scenario every newer scenario in the process
    breaks (see the TODO in RetrieverObjectLink). We only report "unsupported" per scenario:
    pull returns None and push already skips by version, so nothing else changes."""
    if self.support is None:
        return False
    return not self.support.supports(_getters.get_scenario_version(uuid))


RetrieverObjectLink.overwrite_unsupported_properties = _unsupported_without_class_patch

from AoE2ScenarioParser.datasets.trigger_lists import ObjectAttribute  # noqa: E402

# Attributes that take fractions although the parser's table lists them as whole numbers. The parser writes a
# float-typed attribute's quantity into the effect's quantity_float field and leaves the integer field at -1.
#   110 POPULATION: the game's own techs set it to fractions (RoR's Logistics: infantry -0.5, i.e. half a
#   population space). Unverified that the trigger effect reads the fraction; if the game ignores the float
#   field it reads -1, an ordinary 1-population unit.
FRACTIONAL_ATTRIBUTES = {110}
_parser_storage_type = ObjectAttribute._storage_type


def _storage_type(value):
    return "float" if value in FRACTIONAL_ATTRIBUTES else _parser_storage_type(value)


ObjectAttribute._storage_type = staticmethod(_storage_type)

from AoE2ScenarioParser.datasets import conditions as condition_dataset  # noqa: E402
from AoE2ScenarioParser.datasets import effects as effect_dataset  # noqa: E402
from AoE2ScenarioParser.datasets.conditions import ConditionId  # noqa: E402
from AoE2ScenarioParser.datasets.effects import EffectId  # noqa: E402
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario  # noqa: E402

__all__ = [
    "AoE2DEScenario",
    "ConditionId",
    "EffectId",
    "condition_dataset",
    "effect_dataset",
    "settings",
]
