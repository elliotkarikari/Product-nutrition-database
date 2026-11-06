# Shared memory lifecycle

Status: active

Decision date: 2026-11-05

Decision maker: Elliot Karikari; current Part B instruction.

Decision: After the sync check, read build_memory.md before code. End every round by updating the summary and recording decisions and verification in the same round’s commits. Keep facts dated and evidenced; supersede decisions with named successor files.

Reasoning: Separate sessions need durable evidence rather than chat recollection. Repository/live facts outrank stale memory; SPEC governs product behavior.

Evidence: AGENTS.md implements this instruction. Correct disagreements in the same round and record the correction. Move detail to sub-files; keep INDEX.md complete. A commit cannot contain its own SHA: record the checked base and identify the resulting round commit through Git history, never invent a self-hash.
