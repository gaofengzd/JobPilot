# RAG learning guide

Retrieval augmented generation, or RAG, grounds generated advice in an external knowledge base. A basic pipeline loads trusted documents, splits them into traceable chunks, embeds each chunk, retrieves Top-K candidates, and preserves chunk identifiers for citations.

Practice: prepare five labeled queries, calculate Hit at K, inspect failed retrievals, and reject learning claims that do not cite a retrieved chunk.
