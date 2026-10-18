# Reliability testing learning guide

Reliability testing measures whether behaviour holds over time and under stress. Long duration runs expose leaks that short runs hide, and recovery testing restarts a component mid load to prove it returns to service. Record the failure rate, the time to recovery, and any state that was lost, because those three numbers describe the risk.

Practice: run one scenario for several hours at a steady load, then kill a dependency and restart it. Record the memory trend, the recovery time, and what state survived.
