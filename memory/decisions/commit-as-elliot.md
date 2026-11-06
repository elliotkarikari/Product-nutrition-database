# Commit identity

Status: active

Decision date: 2026-11-05

Decision maker: Elliot Karikari; current owner instruction, corroborated by local Git configuration.

Decision: Use the repository owner’s configured identity, Elliot Karikari <elliotsnowkari@gmail.com>, with no agent co-author trailers. Keep commits small and independently describable.

Reasoning: Consistent ownership and descriptive commits make changes traceable across agent sessions. Do not substitute an agent identity.

Evidence: git config user.name and user.email verified this round; commits 94b7959e through 3077478 use this identity. The no-trailer instruction is adopted from the owner’s current instruction, not inferred from history.
