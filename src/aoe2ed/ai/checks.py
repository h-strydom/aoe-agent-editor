"""What can go wrong with a computer player, as checks: lint() reads an AI spec before any game is played,
run() reads a probe record (aoe2ed.ai.probe) of what the AI actually did.

Each check is one known way an AI misbehaves, written down once it's understood (docs/ai-behaviour.md explains
them and how they were found). A finding says what was seen, when, and what usually fixes it. Add a check when a
playtest or probe turns up a new failure: a function taking (Context) and yielding findings, registered with
@check.
"""
from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass, field

from .. import tables
from .probe import timeline
from .spec import _step, resolve

LINTS: list[tuple[str, Callable]] = []
CHECKS: list[tuple[str, Callable]] = []


@dataclass
class Finding:
    check: str
    player: int | None
    severity: str             # problem | warning | info
    message: str
    t: int | None = None      # game seconds
    fix: str = ""

    def as_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v not in (None, "")}


@dataclass
class Context:
    game: str
    spec: dict
    player: int | None = None
    record: dict | None = None
    others: list[int] = field(default_factory=list)
    have: set[int] = field(default_factory=set)     # objects the scenario starts the player with

    def series(self, stat: str) -> list[tuple[int, int]]:
        return timeline(self.record, self.player, stat) if self.record else []

    def items(self) -> list[tuple[str, str, int]]:
        """(kind, name, count) of the build order and keep list."""
        return [_step(s) for s in [*(self.spec.get("build_order") or []), *(self.spec.get("keep") or [])]]


def lint_check(fn: Callable) -> Callable:
    LINTS.append((fn.__name__, fn))
    return fn


def check(fn: Callable) -> Callable:
    CHECKS.append((fn.__name__, fn))
    return fn


def _oid(name: str, kind: str, game: str) -> int | None:
    try:
        return resolve(name, "tech" if kind == "research" else "object", game)
    except (KeyError, ValueError):
        return None


# ----------------------------------------------------------------------------------------- lints (no game)
@lint_check
def made_where(c: Context) -> Iterator[Finding]:
    """A unit or tech whose building the AI never builds (and wasn't given) can never be made."""
    t = tables.load(c.game)

    def base(oid: int) -> int:
        return t["objects"].get(str(oid), {}).get("variant_of", oid)

    available = {base(o) for o in {_oid(n, k, c.game) for k, n, _ in c.items() if k == "build"} | c.have
                 if o is not None}
    for kind, name, _ in c.items():
        if kind == "build":
            continue
        oid = _oid(name, kind, c.game)
        entry = t["techs" if kind == "research" else "objects"].get(str(oid), {})
        places = entry.get("researched_at" if kind == "research" else "made_at", [])
        if places and not {base(p) for p in places} & available:
            where = ", ".join(t["objects"][str(p)]["name"] for p in places)
            yield Finding("made_where", c.player, "problem",
                          f"{kind} {name} is made at {where}, which the AI never builds",
                          fix=f"add {{build: {t['objects'][str(places[0])]['name']}}} before it, or check the "
                              f"scenario gives the player one")


@lint_check
def age_variant(c: Context) -> Iterator[Finding]:
    """Building a later-age look (ACADEMY_AGE3) instead of the buildable Age1 base: villagers can't build it."""
    t = tables.load(c.game)
    for kind, name, _ in c.items():
        if kind != "build":
            continue
        entry = t["objects"].get(str(_oid(name, kind, c.game)), {})
        if "variant_of" in entry:
            base = t["objects"][str(entry["variant_of"])]["name"]
            yield Finding("age_variant", c.player, "problem", f"build {name} is an age look of {base}",
                          fix=f"build {base}; the game shows the later look by itself")


@lint_check
def attack_without_army(c: Context) -> Iterator[Finding]:
    """An attack plan with nothing to attack with."""
    attack = c.spec.get("attack")
    if not attack:
        return
    civilian = ("VILLAGER", "FISHING", "TRADE", "TRANSPORT", "MERCHANT")
    army = [n for k, n, _ in c.items() if k == "train" and not any(w in n.upper() for w in civilian)]
    if not army:
        yield Finding("attack_without_army", c.player, "warning",
                      "attack is set but the AI trains no soldiers (only what the scenario gives it can attack)")


@lint_check
def naval_without_ships(c: Context) -> Iterator[Finding]:
    attack = c.spec.get("attack") or {}
    if attack.get("naval") and not c.spec.get("transports") and not any(
            k == "build" and n.upper() == "DOCK" for k, n, _ in c.items()):
        yield Finding("naval_without_ships", c.player, "warning",
                      "naval attacks are on but the AI builds no dock and keeps no transports",
                      fix="add {build: DOCK} and warships, or transports: 2 for island maps")


# --------------------------------------------------------------------------------------- checks (probe)
def _first(series, pred) -> int | None:
    return next((t for t, v in series if pred(v)), None)


@check
def never_made(c: Context) -> Iterator[Finding]:
    """Things in the build order or keep list the AI never had, not even under construction."""
    for kind, name, _ in c.items():
        if kind == "research":
            continue
        s = c.series(_label(c, name))
        if s and max(v for _, v in s) == 0:
            yield Finding("never_made", c.player, "problem", f"{kind} {name}: never had one",
                          fix="see the lint findings; otherwise the AI can't afford it or a step before it stalls")


@check
def stalled_build_order(c: Context) -> Iterator[Finding]:
    """The first build-order step whose count is never reached; everything after it waits."""
    for i, (kind, name, count) in enumerate(_step(s) for s in c.spec.get("build_order") or []):
        if kind == "research":
            continue
        s = c.series(_label(c, name))
        if s and max(v for _, v in s) < count:
            yield Finding("stalled_build_order", c.player, "problem",
                          f"build order step {i + 1} ({kind} {name} x{count}) never completed: "
                          f"reached {max(v for _, v in s)}; steps after it are skipped only by the step timeout",
                          fix="check what the step costs against the stockpile timeline, and its building")
            return


@check
def hoarding(c: Context) -> Iterator[Finding]:
    """A big unspent stockpile for minutes: the AI has nothing it can spend it on."""
    for res in ("food", "wood", "gold", "stone"):
        s = c.series(res)
        run_start = None
        for t, v in s:
            if v >= 600:
                run_start = t if run_start is None else run_start
                if t - run_start >= 180:
                    yield Finding("hoarding", c.player, "warning", f"{v} {res} unspent for 3+ minutes", t=run_start,
                                  fix="a stalled step or a missing building; or keep more units that cost it")
                    break
            else:
                run_start = None


@check
def villagers(c: Context) -> Iterator[Finding]:
    """Fewer villagers than the spec asks for, well into the game."""
    want = int(c.spec.get("villagers") or 0)
    s = c.series("villagers")
    if not want or not s:
        return
    late = [(t, v) for t, v in s if t >= 480]
    if late and max(v for _, v in late) < want * 0.6:
        yield Finding("villagers", c.player, "problem",
                      f"at most {max(v for _, v in late)} villagers after 8 minutes (spec: {want})", t=late[0][0],
                      fix="town center busy or missing, housing, or food income too low")


@check
def housed(c: Context) -> Iterator[Finding]:
    """Population at its cap for minutes: no houses."""
    pop, cap = c.series("population"), dict(c.series("population_cap"))
    start = None
    for t, v in pop:
        if cap.get(t) and v >= cap[t] - 1:
            start = t if start is None else start
            if t - start >= 120:
                yield Finding("housed", c.player, "problem", f"population {v}/{cap[t]} for 2+ minutes", t=start,
                              fix="houses: true, and wood income")
                return
        else:
            start = None


@check
def no_income(c: Context) -> Iterator[Finding]:
    """A resource the plan needs that nobody gathers."""
    from .spec import cost
    need = set()
    for kind, name, _ in c.items():
        oid = _oid(name, kind, c.game)
        if oid is not None:
            need |= set(cost("tech" if kind == "research" else "object", oid, c.game))
    for res in sorted(need):
        s = c.series(f"{res}_total")
        late = [(t, v) for t, v in s if t >= 300]
        if len(late) >= 2 and late[-1][1] - late[0][1] <= 0:
            yield Finding("no_income", c.player, "problem",
                          f"no {res} gathered after 5 minutes, but the plan needs it", t=late[0][0],
                          fix="gatherer split (gatherers: auto), or no reachable mine/trees")


@check
def no_attack(c: Context) -> Iterator[Finding]:
    """An attack was due but the AI never fought: no kills, its army never shrank."""
    attack = c.spec.get("attack")
    if not attack or not c.record:
        return
    due = int(attack.get("first", 0)) + 180
    end = c.record["samples"][-1]["t"] if c.record["samples"] else 0
    if end < due:
        return
    kills = c.series("kills")
    mil = c.series("military")
    peak = max((v for _, v in mil), default=0)
    if max((v for _, v in kills), default=0) == 0:
        yield Finding("no_attack", c.player, "problem",
                      f"no kills by {end // 60} min although the first attack was due at {attack.get('first')} s "
                      f"(peak army {peak})",
                      fix="army below attack.min_group, sn-percent-attack-soldiers, or no path (water: transports)")


@check
def idle_villagers(c: Context) -> Iterator[Finding]:
    """Villagers standing around: idle time growing fast."""
    s = c.series("idle_seconds")
    vil = dict(c.series("villagers"))
    if len(s) < 3:
        return
    (t0, a), (t1, b) = s[-3], s[-1]
    if t1 > t0 and vil.get(t1):
        idle_share = (b - a) / ((t1 - t0) * vil[t1])
        if idle_share > 0.25:
            yield Finding("idle_villagers", c.player, "warning",
                          f"about {round(idle_share * 100)}% of villager time idle near the end", t=t0,
                          fix="nothing left to gather nearby, or no drop site near the resources")


def _label(c: Context, name: str) -> str:
    """The name a probe record uses for an object (the table's name for its id)."""
    oid = _oid(name, "train", c.game)
    return tables.load(c.game)["objects"].get(str(oid), {}).get("name", name)


def lint(spec: dict, game: str = "ror", player: int | None = None, have: list[int] = ()) -> list[dict]:
    """Problems visible in an AI spec without playing. have: object ids the scenario starts the player with."""
    c = Context(game, spec, player, have=set(have))
    return [f.as_dict() for _, fn in LINTS for f in fn(c)]


def run(record: dict, manifest: dict) -> dict:
    """All lints and checks for every player with a spec in the manifest, plus a short summary per player."""
    game = manifest.get("game", "ror")
    out: dict = {"ended": record.get("ended"), "last_sample": record["samples"][-1]["t"] if record["samples"] else 0,
                 "players": {}}
    for p in record["players"]:
        spec = manifest.get("specs", {}).get(str(p))
        last = record["samples"][-1]["players"][p] if record["samples"] else {}
        summary = {k: last.get(k) for k in ("villagers", "military", "population", "population_cap", "kills",
                                            "food", "wood", "gold", "stone")}
        summary["objects"] = {n: v[0] for n, v in last.get("objects", {}).items() if v[0]}
        findings = []
        if spec:
            c = Context(game, spec, p, record, [q for q in record["players"] if q != p],
                        set(manifest.get("start_objects", {}).get(str(p), [])))
            findings = [f.as_dict() for _, fn in [*LINTS, *CHECKS] for f in fn(c)]
        out["players"][p] = {"summary": summary, "findings": findings, "has_spec": bool(spec)}
    return out
