# LoadRunner learning guide

LoadRunner separates a scenario into a vuser script, a runtime scenario, and an analysis report. Correlate every dynamic value the server returns, such as a session id, before replaying, or the run will fail with errors that are not real load errors. Keep transactions around business steps rather than around single requests so the report answers a business question.

Practice: record one business flow, correlate every dynamic value, run a 30 minute scenario with a steady load, and save the analysis session. Report the transaction response times you measured, not an estimate.
