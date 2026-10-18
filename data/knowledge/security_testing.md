# Security testing learning guide

Security testing checks confidentiality, integrity, and availability of the thing under test. Work from a threat model rather than from a tool list: identify the assets, the entry points, and the trust boundaries, then test the controls that guard them. Injection, broken authentication, and missing authorization are the failures worth checking first because they appear often and cost the most.

Practice: enumerate the entry points of one small service, attempt one injection and one authorization bypass against it, and record what you observed and what you fixed.
