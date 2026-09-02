"""Which dependencies the bot's handlers ASK FOR — read out of the source, not a list.

**The class of error this module exists to find: a dependency that is alive in the tests
and dead in battle.**  ``bot/routers/photo.py`` read ``data.get("vision")``; ``bot/app.py``
put no such key; ``tests/photo/conftest.py`` put one in by fixture.  Result: 645 green
tests, eighteen gates out of eighteen passed, and every photograph a teacher sent
answered «Разбор фото не настроен».  The same shape had already cost this project a night
with ``BOT_TOKEN = ""``.

WHY A SCANNER AND NOT A TEST THAT NAMES ``vision``.  A test that asserts ``"vision" in
workflow_data`` is green forever and finds nothing: the NEXT ``data.get("что-то")`` opens
the hole again, and it is invisible to the handler's signature, to the type checker and
to any test that builds its own dispatcher.  So the two sides are both derived —
consumption from the syntax tree of ``bot/**``, provision from a dispatcher that is
actually built — and the gate is their difference.

TWO WAYS A HANDLER ASKS AIOGRAM FOR SOMETHING, AND BOTH ARE SCANNED
-------------------------------------------------------------------
1. ``**data`` and then ``data["x"]`` / ``data.get("x")`` — invisible to the signature.
   This is the one that hid ``vision``.
2. A NAMED parameter, which aiogram resolves out of ``workflow_data`` by name.  This is
   the one that hides ``transcriber``: ``voice.on_voice`` declares it, and a missing key
   is a ``TypeError`` at the moment a teacher speaks, not at start-up.

WHY THE FSM DICT IS EXCLUDED BY CONSTRUCTION AND NOT BY A LIST OF NAMES
-----------------------------------------------------------------------
``data = await state.get_data()`` binds the SAME popular name to a completely different
dictionary, and ``data.get("surname")`` on it is not a DI lookup at all.  Filtering those
out by listing «surname, name, last_mark, …» would rot the moment somebody adds an FSM
slot.  Instead the scanner refuses to read any function whose ``**data`` name is
REASSIGNED anywhere in its body, and counts those functions out loud (see ``rebound``) so
that «excluded» can never quietly become «not looked at».
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Dict, List, Set, Tuple

#: The package that is scanned.  Handlers live nowhere else.
BOT_PACKAGE = Path(__file__).resolve().parents[2] / "bot"


class Ask:
    """One dependency a handler asks for: where it is asked and how."""

    def __init__(self, key: str, where: str, how: str) -> None:
        self.key = key
        self.where = where
        self.how = how

    def __repr__(self) -> str:  # pragma: no cover -- assertion messages only
        return "%s (%s, %s)" % (self.key, self.where, self.how)


class Scan:
    """The result of reading the sources: what is asked, and what could not be read."""

    def __init__(self) -> None:
        self.asks: List[Ask] = []
        #: Functions whose ``**data`` name is rebound in the body: FSM dictionaries, not DI.
        self.rebound: List[str] = []
        #: ``data.get(SOMETHING)`` where SOMETHING is not a literal.  NOT silently dropped:
        #: an unreadable key is a hole in the COVERAGE of this gate and fails it.
        self.unreadable: List[str] = []
        #: Files parsed, so a negative verdict can carry its own coverage.
        self.files: List[str] = []

    def keys(self) -> Set[str]:
        return {ask.key for ask in self.asks}

    def where(self, key: str) -> str:
        return ", ".join(sorted({ask.where for ask in self.asks if ask.key == key}))


def _rebinds(function: ast.AST, name: str) -> bool:
    """Is ``name`` assigned to anywhere inside this function?

    ``data = await state.get_data()`` is the case this exists for, but the question is
    asked in general: ANY rebinding means the reads below it are reads of something else,
    and this scanner will not guess which.
    """
    for node in ast.walk(function):
        targets: List[ast.AST] = []
        if isinstance(node, ast.Assign):
            targets = list(node.targets)
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
            targets = [node.target]
        elif isinstance(node, ast.For):
            targets = [node.target]
        elif isinstance(node, ast.withitem):
            targets = [node.optional_vars] if node.optional_vars else []
        elif isinstance(node, ast.comprehension):
            targets = [node.target]
        for target in targets:
            for inner in ast.walk(target):
                if isinstance(inner, ast.Name) and inner.id == name:
                    return True
    return False


def _string(node: ast.AST):
    """The literal string a node is, or ``None`` if it is not one."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def scan_bot(package: Path = BOT_PACKAGE) -> Scan:
    """Every dependency asked for under ``bot/**``, by both routes."""
    scan = Scan()
    for path in sorted(package.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        scan.files.append(str(path.relative_to(package.parent)))
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            _read_function(scan, node, str(path.relative_to(package.parent)))
    return scan


def _read_function(scan: Scan, node, where: str) -> None:
    kwarg = node.args.kwarg
    if kwarg is None:
        return
    site = "%s:%s:%s" % (where, node.lineno, node.name)
    if _rebinds(node, kwarg.arg):
        # An FSM dictionary wearing the same name.  Counted, never silently dropped.
        scan.rebound.append(site)
        return
    for inner in ast.walk(node):
        key = None
        how = ""
        if isinstance(inner, ast.Subscript) and _is_name(inner.value, kwarg.arg):
            key = _string(_index(inner))
            how = "%s[...]" % kwarg.arg
            if key is None:
                scan.unreadable.append("%s -- %s[<not a literal>]" % (site, kwarg.arg))
                continue
        elif (
            isinstance(inner, ast.Call)
            and isinstance(inner.func, ast.Attribute)
            and inner.func.attr == "get"
            and _is_name(inner.func.value, kwarg.arg)
        ):
            key = _string(inner.args[0]) if inner.args else None
            how = "%s.get(...)" % kwarg.arg
            if key is None:
                scan.unreadable.append("%s -- %s.get(<not a literal>)" % (site, kwarg.arg))
                continue
        if key is not None:
            scan.asks.append(Ask(key, site, how))


def _is_name(node: ast.AST, name: str) -> bool:
    return isinstance(node, ast.Name) and node.id == name


def _index(node: ast.Subscript) -> ast.AST:
    """The subscript's index, across the 3.8 ``ast.Index`` wrapper and 3.9+ without it."""
    value = node.slice
    return getattr(value, "value", value) if value.__class__.__name__ == "Index" else value


# ---------------------------------------------------------------- the second route

def named_parameters(handler) -> List[str]:
    """The parameters aiogram must resolve BY NAME for this handler.

    Everything with a default is excluded: aiogram leaves it alone and the default stands.
    ``self`` and the event argument (the first positional) are excluded too -- aiogram
    passes the event positionally and never looks it up.
    """
    import inspect

    try:
        signature = inspect.signature(handler)
    except (TypeError, ValueError):  # pragma: no cover -- not a python callable
        return []
    wanted: List[str] = []
    for index, parameter in enumerate(signature.parameters.values()):
        if parameter.kind in (parameter.VAR_KEYWORD, parameter.VAR_POSITIONAL):
            continue
        if index == 0 or parameter.name == "self":
            continue
        if parameter.default is not inspect.Parameter.empty:
            continue
        wanted.append(parameter.name)
    return wanted


def registered_handlers(dispatcher) -> List[Tuple[str, object, object]]:
    """``(where, callback, handler)`` for every handler on every router the dispatcher includes."""
    found: List[Tuple[str, object, object]] = []
    for router in _routers(dispatcher):
        for name, observer in router.observers.items():
            for handler in getattr(observer, "handlers", []):
                callback = getattr(handler.callback, "callback", handler.callback)
                found.append((
                    "%s.%s:%s" % (router.name, name, getattr(callback, "__name__", callback)),
                    callback,
                    handler,
                ))
    return found


#: What a FILTER puts into ``data`` when it matches, by the filter's own class.  This is
#: the one thing here that cannot be derived: aiogram merges whatever dictionary a filter
#: RETURNS, and the return value of a filter that has not run yet is not a readable fact.
#: So it is written down per filter class -- and it buys nothing on a handler that does
#: not carry that filter, which is what ``filter_supplied`` checks.  A blanket
#: ``{"command", "callback_data"}`` would forgive those names on every handler in the bot.
FILTER_SUPPLIED = {
    "Command": ("command",),
    "CommandStart": ("command",),
    "CallbackQueryFilter": ("callback_data",),
}


def filter_supplied(handler) -> Set[str]:
    """The names the filters registered ON THIS handler will put into ``data``."""
    names: Set[str] = set()
    for wrapper in getattr(handler, "filters", None) or []:
        callback = getattr(wrapper, "callback", wrapper)
        for base in type(callback).__mro__:
            names.update(FILTER_SUPPLIED.get(base.__name__, ()))
    return names


def _routers(root) -> List[object]:
    out = [root]
    for child in getattr(root, "sub_routers", []):
        out.extend(_routers(child))
    return out


def grouped(asks: List[Ask]) -> Dict[str, List[Ask]]:
    out: Dict[str, List[Ask]] = {}
    for ask in asks:
        out.setdefault(ask.key, []).append(ask)
    return out


# ------------------------------------------------------------- the third provider

def middleware_providers(package: Path = BOT_PACKAGE) -> Dict[str, str]:
    """``key -> where`` for every ``data["key"] = ...`` written by this project's own middleware.

    Derived, not listed.  ``identity`` is stamped by ``bot/middleware.py`` and is therefore
    never missing from a handler's ``data``, but a gate that carried the word «identity» as
    a constant would go red the day that middleware stamped a second thing, and stale-green
    the day it stopped stamping this one.

    The shape scanned is aiogram's middleware protocol and nothing else: a ``__call__``
    whose LAST parameter is the data dictionary.  Without that restriction the walk also
    collects ``draft["checked"] = ...`` from a handler -- an ordinary local dictionary that
    provides nobody anything, and every such false provider is a hole punched in the gate.
    """
    found: Dict[str, str] = {}
    for path in sorted(package.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if node.name != "__call__":
                continue
            positional = [a.arg for a in node.args.args] + [a.arg for a in node.args.kwonlyargs]
            if not positional:
                continue
            bag = positional[-1]
            for inner in ast.walk(node):
                if not isinstance(inner, ast.Assign):
                    continue
                for target in inner.targets:
                    if not isinstance(target, ast.Subscript):
                        continue
                    if not _is_name(target.value, bag):
                        continue
                    key = _string(_index(target))
                    if key is not None:
                        found.setdefault(
                            key, "%s:%s" % (path.relative_to(package.parent), inner.lineno)
                        )
    return found
