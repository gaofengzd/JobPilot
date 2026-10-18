# White box testing learning guide

White box testing uses the implementation to choose cases, so coverage is the main measure. Start from statement coverage, then add branch coverage for every decision, and reserve path and condition coverage for the logic that guards a critical behaviour. A branch that cannot be reached is a defect in either the code or the test, and it must be recorded either way.

Practice: take one function with several branches, list the branches, write the minimum cases that cover them, and measure the coverage your tool reports. Save the coverage number you actually measured.
