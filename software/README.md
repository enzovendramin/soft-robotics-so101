# Software

Windows 11, LeRobot 0.6.0. Nothing here is Windows-only by design, but the
gotchas at the bottom are.

| File | What it is |
|---|---|
| [`robot_tools.py`](robot_tools.py) | Diagnostics and teleoperation. The tool used to bring the arm up and drive the winch |
| [`record_winch.py`](record_winch.py) | Records a dataset by teleoperation, with winch control instead of a normal gripper |
| [`replay_winch.py`](replay_winch.py) | Replays a recorded episode on the arm |
| [`config.py`](config.py) | COM ports, arm IDs and camera indices. **Edit this first** |
| [`s0101code_simo/`](s0101code_simo/) | Simo Alami's pipeline for the rigid claw. See the bottom |

---

## Setup

```powershell
cd path\to\soft-robotics-so101\software
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If PowerShell refuses to run the activation script:
`Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`

**Plug the power supply into the bus adapter.** USB alone talks to the motors
but will not move them. If everything connects and nothing moves, that is why.

Find the ports and cameras, and put the numbers in `config.py`:

```powershell
lerobot-find-port
lerobot-find-cameras opencv
```

Then calibrate. **Type `c` at the prompt** for a fresh calibration. An old
file gives joint values that look fine but are shifted.

```powershell
lerobot-calibrate --robot.type=so101_follower --robot.port=COM3 --robot.id=my_arm
```

Check it moves: `python robot_tools.py move shoulder_pan --step 10`

---

## `robot_tools.py`

| Command | What it does |
|---|---|
| `move <joint> [--step 10]` | Nudge one joint and read it back |
| `read-leader [--seconds 20]` | Print the leader's positions. The follower does not move |
| `spool` | REPL for the winch: `dir cw/ccw`, `speed`, `torque`, `roll <turns>`, `status` |
| `multiturn [--turns 1]` | Teleop where the leader trigger drives N full turns of the winch |
| `trigger [--high 80] [--low 20]` | Bang-bang winch: trigger past the thresholds spins it one way or the other. `--display_data` opens a Rerun window with both cameras |
| `keyboard [--step 3]` | Keyboard teleoperation |

Defaults come from `config.py`. `--port` and `--id` override them.

**Start with `spool`.** It drives the winch straight from the follower, with no
leader arm in the loop, so you can wind an exact number of turns and watch the
load while it happens. That makes it the quickest way to check the tuner, the
knot and the cable routing before anything depends on teleoperation:

```powershell
python robot_tools.py spool
```

```
dir cw
speed 300
roll 0.5
```

Stop `trigger` and `read-leader` with **ESC**. Ctrl+C only works when the
terminal has focus, and the Rerun window takes it.

The winch commands run the motor in **velocity mode**, because the STS3215
cannot represent a target more than one turn away. If you build on them, add up
the differences between encoder readings. Do not send an absolute position, or
the motor jerks every time it crosses 4095 → 0. See
[`../docs/lessons_learned.md`](../docs/lessons_learned.md#the-motor-only-counts-one-turn).

`safe_stop()` retries a dropped stop command several times and shouts at you to
cut the power if it cannot confirm the motor stopped. Keep that if you
refactor, because a dropped stop leaves the winch winding.

---

## Recording and replaying

`record_winch.py` records a `LeRobotDataset` by teleoperation. It exists
because `lerobot-record` assumes a position-controlled gripper, which cannot
drive the winch.

```powershell
python record_winch.py --repo-id enzo/tentacle_pickplace2 `
    --num-episodes 10 `
    --single-task "Pick up the toroid with the tentacle and drop it elsewhere" `
    --episode-time-s 20 --reset-time-s 10 --display_data

# add more episodes to the same dataset later
python record_winch.py --repo-id enzo/tentacle_pickplace2 --num-episodes 5 `
    --single-task "Pick up the toroid with the tentacle and drop it elsewhere" --resume
```

While recording: **→** ends the episode, **←** re-records the last one,
**ESC** stops.

`replay_winch.py` plays an episode back on the arm, using the same winch
control it was recorded with:

```powershell
python replay_winch.py --repo-id enzo/tentacle_pickplace2 --episode 0
```

The gripper action is recorded as the leader trigger's raw 0–100% value, not a
motor position, so a trained policy can output the same thing and have it run
through the same zone logic. See
[`../docs/design_decisions.md`](../docs/design_decisions.md).

---

## `s0101code_simo/`

Simo Alami's LeRobot pipeline: dataset recording, ACT training, evaluation,
replay, multi-camera teleoperation. I used it as the starting point for the
winch scripts, and it works as-is for the **rigid claw**, not the tentacle.

Two things to know before running it:

- It pins **lerobot 0.4.1** on Python 3.10 in a conda environment
  (`lerobot.yml`), so it does not import under the 0.6.0 install used by
  `robot_tools.py`. Keep the two environments separate.
- `S0101_evaluate.py` imports `S0101_policy_utils`, which is not in the folder.
