# Static testing learning guide

Static testing finds defects without executing the code, so it works before a build exists. Reviews find unclear intent and missing cases that tools cannot see, while static analysis finds unreachable code, unsafe constructs, and duplicated logic at a scale a reviewer cannot. Keep the two separate, because they produce different findings and different fixes.

Practice: run a static analyzer over one module, triage its findings into real defects and noise, then review the same module and compare what each pass found.
