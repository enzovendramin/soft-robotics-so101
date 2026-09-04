# Next steps

## Where I stopped

The build is finished and works. The tentacle is mounted, the winch pulls it,
and the whole thing is driveable by teleoperation with both cameras running.

I started recording a dataset with `record_winch.py`, and wrote
`replay_winch.py` to play an episode back on the arm. Replaying a recorded
episode, the tentacle **picked the toroid ring off its stand and dropped it in
a bowl**. That is the task working end to end: teleoperate, record, replay.

The dataset so far is one episode, `enzo/tentacle_pickplace2`, 797 frames at
30 fps.

---

## 1. More episodes

One episode is enough to prove the pipeline, not to train anything. The next
job is to record a lot more of them, with the object starting in different
places so a policy sees more than one approach.

```powershell
python record_winch.py --repo-id enzo/tentacle_pickplace2 --num-episodes 20 `
    --single-task "Pick up the toroid with the tentacle and drop it elsewhere" --resume
```

Worth deciding early: whether every episode uses the same ring, or whether
other shapes go in too. Mixing them makes a harder dataset but a more useful
policy.

---

## 2. Reinforcement learning

The plan after the dataset is RL rather than imitation alone.

The reward is the easy part. The top camera already sees the bowl, so whether
the ring ended up in it is straightforward to read off.

The decision worth making early is the action space: whether the policy outputs
the trigger value directly, the way the dataset is recorded (see
[`design_decisions.md`](design_decisions.md)), or something closer to cable
length.

Two practical warnings for anyone running the arm unattended:

- The winch can wind itself to destruction if a stop command gets dropped. Keep
  `safe_stop()` in the loop.
- Never let the cable go fully slack, or it unwraps from the tuner.

---

## 3. Three cables

The mechanical follow-up: three cables instead of one, so the tentacle can bend
in any direction without turning motor 5.

The tentacle side is already solved: the OpenSpiRobs tool generates 2- and
3-cable bodies. The work is in where the two extra motors go. Stacking them at
joint 5 is the obvious option, and worth checking the arm still handles the
added weight at the wrist before committing to it. Mounting them lower down
with the cables routed up is the alternative if it does not.

This is a trade, not a straight upgrade: the single-cable design twists less
under load (see [`design_decisions.md`](design_decisions.md)).

---

## 4. Better winch control

- Tension feedback instead of position alone, so the residual tension is
  measured rather than guessed.
- Measure tip angle against winch turns, so a controller can be asked for a
  curvature rather than a number of turns.
