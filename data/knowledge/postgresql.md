# PostgreSQL learning guide

PostgreSQL query performance depends on schema design, selective indexes, and evidence from EXPLAIN ANALYZE. Indexes speed suitable reads but add storage and write cost. Parameterized SQL prevents injection and improves safe query construction.

Practice: create a small table, compare a filtered query before and after an index, and save both EXPLAIN ANALYZE plans.
