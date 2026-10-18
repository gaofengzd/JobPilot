# JMeter learning guide

JMeter drives load by running a thread group that replays HTTP samplers against a target. Record a realistic scenario first, then parameterize host, credentials, and payload data with CSV Data Set Config so one script covers many users. Add timers to model think time, assertions to catch wrong responses, and a backend listener only when the extra network cost is acceptable.

Practice: script one login plus one read and one write request, ramp from 10 to 200 threads, and record throughput, p95 latency, and error rate for each step. Verify the results against a fixed target before reporting them.
