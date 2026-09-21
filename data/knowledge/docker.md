# Docker learning guide

Docker packages an application and its runtime into a repeatable container image. Start with a small Python base image, copy the lock files first, install locked dependencies, then copy application code. Run as a non-root user and keep secrets outside the image.

Practice: containerize a Python API, add a health check, build the image, and record the successful container command.
