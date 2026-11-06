# Never publish VJ content

Status: active

Decision date: 2026-11-05

Decision maker: Elliot Karikari; instruction recorded in the guard test.

Decision: Never copy, quote, publish or use reviewer comments or legacy _VJ content as a source. Keep the fingerprint guard passing; store fingerprints, not protected text.

Reasoning: The owner excluded this material. Importing legacy files must not republish the excluded content.

Evidence: tests/test_no_vj_content.py; tests/vj_fingerprints.json; commit 94b7959e. Guard passed in the recorded 103-test run.
