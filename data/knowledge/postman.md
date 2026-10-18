# Postman learning guide

Postman is most useful when a collection is treated as a regression suite. Store the base url and tokens as environment variables, chain requests through tests that set variables from a response, and assert the status code, latency, and the shape of the body. Newman runs the same collection from a command line so it can join a pipeline.

Practice: build a collection covering create, read, update, and delete for one resource, add assertions for each request, run it with Newman, and attach the failing request names and status codes you observed.
