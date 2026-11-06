"""Matching assistant: propose CoFID identities for a product name. Never scores.

Shape (memory/decisions/matching.md): deterministic retrieval proposes a
candidate set; Jev (TypeSafe) scores each candidate's relevance as a
probability when TYPESAFE_API_KEY is set; a person confirms or rejects.
Nothing is scored from a proposal. Only a confirmed match is used, and its
recorded basis names how it was proposed (engine, model version,
probability) and that a user confirmed it.

Without the key, or if Jev cannot be reached, the assistant falls back to
the deterministic candidates and says so in every response; no candidate is
then called "proposed", only "possible". The key is read from the
environment per call and never logged, returned or stored.

Wire format (confirmed 2026-11-06 from the published TypeSafe adapter
source): POST {TYPESAFE_API_BASE or https://api.typesafe.ai}/v1/systemone,
Authorization: Bearer <key>, body {model, state, questions}; a yes/no
("noul") question is answered {"type": "noul", "noul": p}; the reply names
the versioned model that answered.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

from .ui_api import foods_by_id

CONFIG = Path(__file__).resolve().parents[2] / "data" / "matching.json"
KEY_VAR = "TYPESAFE_API_KEY"
BASE_VAR = "TYPESAFE_API_BASE"
DEFAULT_BASE = "https://api.typesafe.ai"
MAX_QUERY = 120

_STOP = {"and", "or", "with", "without", "in", "of", "the", "a", "an", "for", "per", "average"}


@lru_cache(maxsize=1)
def settings() -> dict[str, Any]:
    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    for name in ("candidates", "propose_at", "abstain_below", "timeout_seconds", "model"):
        if name not in data:
            raise ValueError(f"{CONFIG}: missing '{name}'.")
    if not 0 <= data["abstain_below"] <= data["propose_at"] <= 1:
        raise ValueError(f"{CONFIG}: need 0 <= abstain_below <= propose_at <= 1.")
    return data


def _stem(word: str) -> str:
    for suffix, keep in (("ies", "y"), ("oes", "o"), ("es", "e"), ("s", "")):
        if word.endswith(suffix) and len(word) > len(suffix) + 2 and not word.endswith("ss"):
            return word[: -len(suffix)] + keep
    return word


def tokens(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", text.casefold())
    return [_stem(w) for w in words if w not in _STOP]


@lru_cache(maxsize=1)
def _catalogue() -> list[tuple[str, frozenset[str], str, str]]:
    out = []
    for f in foods_by_id().values():
        words = tokens(f.name)
        if words:
            out.append((f.food_id, frozenset(words), f.name, words[0]))
    return out


def retrieve(query: str, k: int | None = None) -> list[dict[str, Any]]:
    """Deterministic candidates: shared words, weighted toward CoFID's head word."""
    k = k or settings()["candidates"]
    q = tokens(query)
    if not q:
        return []
    qset = set(q)
    scored = []
    for food_id, words, name, head in _catalogue():
        shared = qset & words
        if not shared:
            continue
        overlap = len(shared) / len(qset | words)
        # CoFID names lead with the food ("Eggs, chicken, ..."); producers often lead with a
        # describing word ("free range eggs"), so CoFID's head word anywhere in the query counts.
        score = 0.65 * overlap + 0.25 * (head in qset) + 0.10 * (q[0] in words)
        scored.append((round(score, 4), -len(words), name, food_id))
    scored.sort(reverse=True)
    foods = foods_by_id()
    return [{"food_id": fid, "code": foods[fid].source_code, "name": name, "group": foods[fid].group,
             "retrieval_score": score} for score, _, name, fid in scored[:k]]


def _jev_question(query: str, candidate: dict[str, Any]) -> dict[str, str]:
    return {"type": "noul", "instructions": (
        f"A food producer's product is named: \"{query}\". Is the reference food "
        f"\"{candidate['name']}\" (UK CoFID 2021, food group {candidate['group']}) the same food, "
        "in the same form and state as it is sold, so that its composition can stand for the product?")}


def _post(url: str, key: str, body: dict[str, Any], timeout: float) -> dict[str, Any]:
    request = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"), method="POST",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:   # noqa: S310 (fixed https host)
        return json.loads(response.read().decode("utf-8"))


def jev_gate(query: str, candidates: list[dict[str, Any]],
             post: Callable[..., dict[str, Any]] = _post) -> dict[str, Any]:
    """Ask Jev for each candidate's probability. Returns an engine record."""
    key = os.environ.get(KEY_VAR)
    if not key:
        return {"engine": "deterministic", "reason": f"{KEY_VAR} is not set on this service, "
                "so Jev was not asked. Candidates are listed by shared words only."}
    if not candidates:
        return {"engine": "deterministic", "reason": "No candidate shares a word with the name."}
    config = settings()
    base = (os.environ.get(BASE_VAR) or DEFAULT_BASE).rstrip("/")
    body = {"model": config["model"], "state": f"Product name: {query}",
            "questions": {f"c{i}": _jev_question(query, c) for i, c in enumerate(candidates)}}
    try:
        reply = post(f"{base}/v1/systemone", key, body, config["timeout_seconds"])
        answers = reply["answers"]
        model = reply["model"]
        if not isinstance(model, str) or not model:
            raise ValueError("no model named")
        probabilities = []
        for i in range(len(candidates)):
            answer = answers[f"c{i}"]
            p = answer["noul"]
            if answer.get("type") != "noul" or isinstance(p, bool) or not isinstance(p, (int, float)) or not 0 <= p <= 1:
                raise ValueError("answer is not a probability")
            probabilities.append(float(p))
    except (urllib.error.URLError, TimeoutError, OSError, KeyError, TypeError, ValueError) as exc:
        kind = type(exc).__name__
        return {"engine": "deterministic", "reason": f"Jev could not be used ({kind}). Candidates are "
                "listed by shared words only."}
    return {"engine": "jev", "model": model, "probabilities": probabilities}


def propose(query: str, post: Callable[..., dict[str, Any]] = _post) -> dict[str, Any]:
    if not isinstance(query, str) or not query.strip():
        raise ValueError("Give a product name to match.")
    query = " ".join(query.split())
    if len(query) > MAX_QUERY:
        raise ValueError(f"Product names are limited to {MAX_QUERY} characters.")
    config = settings()
    candidates = retrieve(query)
    engine = jev_gate(query, candidates, post)
    for i, c in enumerate(candidates):
        if engine["engine"] == "jev":
            p = engine["probabilities"][i]
            c["probability"] = p
            c["verdict"] = ("proposed" if p >= config["propose_at"] else
                            "abstain" if p < config["abstain_below"] else "possible")
        else:
            c["probability"] = None
            c["verdict"] = "possible"
    if engine["engine"] == "jev":
        candidates.sort(key=lambda c: -c["probability"])
    record = {k: v for k, v in engine.items() if k != "probabilities"}
    return {
        "query": query,
        "engine": record,
        "thresholds": {"propose_at": config["propose_at"], "abstain_below": config["abstain_below"],
                       "basis": config["threshold_basis"]},
        "candidates": candidates,
        "status": "unconfirmed",
        "rule": ("A proposal is not a match. Nothing is scored until you confirm one candidate; "
                 "every nutrient value then comes from that CoFID record alone."),
    }


def confirmation(payload: Any) -> dict[str, Any]:
    """Validate a user's confirmation and return the record to keep."""
    if not isinstance(payload, dict):
        raise ValueError("Confirmation must be an object.")
    query, food_id = payload.get("query"), payload.get("food_id")
    if not isinstance(query, str) or not query.strip() or len(query) > MAX_QUERY:
        raise ValueError("Confirmation needs the product name as matched.")
    food = foods_by_id().get(food_id) if isinstance(food_id, str) else None
    if food is None:
        raise ValueError("Confirmation needs a CoFID food_id.")
    engine = payload.get("engine") if isinstance(payload.get("engine"), dict) else {}
    probability = payload.get("probability")
    if engine.get("engine") == "jev":
        model = engine.get("model")
        if not isinstance(model, str) or not isinstance(probability, (int, float)) or isinstance(probability, bool):
            raise ValueError("A Jev proposal needs its model and probability.")
        basis = f"model-proposed (Jev {model}, p={float(probability):.3f}), user-confirmed"
    else:
        model, probability = None, None
        basis = "user-selected from deterministic candidates, user-confirmed"
    return {"query": " ".join(query.split()), "food_id": food.food_id, "code": food.source_code,
            "name": food.name, "basis": basis, "engine": engine.get("engine", "deterministic"),
            "model": model, "probability": probability}
