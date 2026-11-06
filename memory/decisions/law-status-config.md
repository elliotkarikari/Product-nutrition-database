# Law status is configuration

Status: active

Decision date: 2026-11-06

Decision maker: Elliot Karikari (requirement); implementing agent (mechanism).

Decision: Each model's status (in_force, shadow, retired) lives in data/laws.json, read by src/shelfscale/laws.py. The engines never read it. Every model block carries a `law` label (model, name, version, status, status_text, role) and the existing `status` string, whose wording is unchanged ("in force", "shadow model, not in force"). The page's today and coming framing follows `role`. Adoption is one configuration commit, by the procedure in docs/LAW_CHANGE.md. Startup refuses a configuration with an unknown status, a missing field or more than one model in force.

Reasoning: when the 2018 model is adopted, every in-scope product is rescored. Labels must follow the law without touching an engine, and past results must stay reproducible.

Evidence: tests/test_laws.py flips the configuration and shows every score, A and C point and traffic light identical for a supplied product, a CoFID lookup and a recipe, with labels and roles swapped.
