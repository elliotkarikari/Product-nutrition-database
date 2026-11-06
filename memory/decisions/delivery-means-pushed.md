# Delivery means pushed and read back

Status: active

Decision date: 2026-11-05

Decision maker: Elliot Karikari; SPEC §14.

Decision: Delivery requires pushing to elliotkarikari/Product-nutrition-database, shelfscale-open, and reading the commit back from GitHub. Name repository, branch and commit. Otherwise say local-only and provide a patch or bundle.

Reasoning: Work confined to an agent workspace is unavailable to the owner on another machine. A local commit alone does not establish delivery.

Evidence: SPEC.md §14. Its old 2f44f9c handover is historical, not the current head; use build_memory.md and fresh Git metadata.
