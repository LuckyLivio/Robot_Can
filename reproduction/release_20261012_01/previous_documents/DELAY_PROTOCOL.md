# Delay-aware world-model control protocol

## Concrete question

The task is robosuite `PickPlaceCan` with the official robomimic Can PH low-dimensional demonstrations. At deployment, every command enters a FIFO queue of length `D=2` before it reaches the robot. This models communication, controller, and hardware latency. The question is whether a learned action-conditioned world model can use predicted future state and failure risk to choose a safer command under this delay and under small execution noise.

This is a state-diagnostic experiment. It is a robotics world model because the model recursively predicts the future physical state from the current state and pending/action commands; the later vision stage is optional and is not claimed by the current results.

## Proposed method

1. A shared chunk BC policy produces a nominal action chunk.
2. The local candidate set contains four constant-command shifts: repeat nominal action indices `0,1,2,3`.
3. The FIFO contents and a candidate command are passed to a GRU world model. It predicts the next eight physical states recursively. A progress/risk head reads only the recursively predicted state (`future_only=True`).
4. Candidate score is `last_progress + 0.5 * mean_progress - 0.5 * max_risk`.
5. A safety gate uses a fixed-shift prior. Before testing, `k=0,1,2,3` are all evaluated on the development split; the strongest is `k=1`, which is then frozen as the primary prior. The world model overrides it only when its score improvement is at least `delta=0.02`. This threshold and the prior are selected on development data and then frozen.

Training uses state prediction, progress/risk binary supervision, and an intra-start pairwise ranking loss (`lambda=0.2`) over simulator-generated counterfactual branches. Simulator outcomes are training labels only; no simulator reward or ground-truth object state is read during deployment.

## Comparators and ablations

- BC with the first nominal command.
- Fixed shift BC for all `k=0,1,2,3`; `k=1` is the frozen strongest baseline in the primary sealed comparison, while `k=2` is retained as the conventional delay-length diagnostic.
- Plain future-state model without pairwise ranking loss.
- Direct score network with no predicted future state.
- Full model with and without the safety gate.

All methods use the same policy, initial states, delay queue, candidate count, horizon, and step budget. Train/dev/test are split by complete parent trajectory. The sealed split is opened only after the threshold and model configuration are frozen.

## Evaluation axes

- Clean delayed execution (`D=2`, zero action noise).
- Robustness execution (`D=2`, Gaussian noise with position standard deviation `0.05`), declared before sealed evaluation.
- Success rate is primary; stage progress, completion steps, base-action fraction, and decision latency are secondary.
- The main frozen comparison uses the same training seed for all structural variants so that the ablation changes one design choice at a time. The earlier 100-demo, three-seed runs are reported separately as a sensitivity appendix because they used the conventional `k=2` fallback. Results are reported per run and as paired differences on the same initial states; an isolated favorable seed is not treated as proof.
