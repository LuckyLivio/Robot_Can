"""Exact same-environment branches; validated against executed-history replay.

MjData.__copy__ copies the complete native data, including solver warm starts.
Python controller, observable, gripper and robot-buffer state is copied too.
This adapter is intentionally restricted to the frozen Panda/OSC environment.
"""
import copy
import numpy as np


def plain(value):
    if value is None or isinstance(value, (str, bytes, bool, int, float, np.generic, np.ndarray)):
        return True
    if isinstance(value, (tuple, list)):
        return all(plain(v) for v in value)
    if isinstance(value, dict):
        return all(plain(k) and plain(v) for k, v in value.items())
    return False


def objects(env):
    result = [env, *env._observables.values()]
    for robot in env.robots:
        result.extend([robot, robot.composite_controller])
        result.extend(robot.part_controllers.values())
        result.extend(robot.gripper.values())
        for value in vars(robot).values():
            children = value.values() if isinstance(value, dict) else [value]
            for child in children:
                if type(child).__module__ == 'robosuite.utils.buffers':
                    result.append(child)
    seen = set()
    return [o for o in result if id(o) not in seen and not seen.add(id(o))]


class Snapshot:
    def __init__(self, env):
        self.env = env
        self.data = copy.copy(env.sim.data._data)
        self.fields = [(obj, {k: copy.deepcopy(v) for k, v in vars(obj).items() if plain(v)})
                       for obj in objects(env)]
        self.rng = copy.deepcopy(env.rng.bit_generator.state)

    def restore(self):
        # No mj_forward here: it would change the exact cached integration state.
        self.env.sim.data._data = copy.copy(self.data)
        for obj, fields in self.fields:
            for key, value in fields.items():
                setattr(obj, key, copy.deepcopy(value))
        self.env.rng.bit_generator.state = copy.deepcopy(self.rng)


def true_branches(env, queue, commands, horizon, order=None):
    from common import pack_obs
    from collect_branches import future_labels
    from collections import deque
    saved = Snapshot(env)
    initial_grasp = bool(env.staged_rewards()[1] > .3)
    ys, labels = [None] * len(commands), [None] * len(commands)
    try:
        for k in range(len(commands)) if order is None else order:
            saved.restore()
            pending = deque(a.copy() for a in queue)
            states, ll = [], []
            for _ in range(horizon):
                pending.append(commands[k].copy())
                obs, *_ = env.step(np.clip(pending.popleft(), -1, 1))
                states.append(pack_obs(obs))
                ll.append(future_labels(env, initial_grasp))
            ys[k], labels[k] = states, ll
    finally:
        saved.restore()
    return np.asarray(ys, np.float32), np.asarray(labels, np.float32)
