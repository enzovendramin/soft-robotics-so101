# Lessons learned

Things that cost me time, written down so the next person does not hit them
again.

---

## The cable comes off the winch unless you knot it

Stiff line does not stay wrapped on a smooth shaft. When the tension drops it
springs off, the wrap goes loose, and the next time the motor pulls it takes up
that slack before it does anything useful. So the same motor angle stops giving
you the same bend.

The fix is the tuner. `Tuner` has a hole through its shaft, the nylon goes
through that hole, and **you tie a knot on the other side**.

The knot is not optional. Without it the line is only held by friction, and it
will not come back out when the motor turns the other way. The tentacle bends
in fine and then never straightens. If that happens to you, check the knot
first.

### Cables I tried

- **Guitar string.** Hard to wind and too springy. It fights the tuner.
- **Twine.** Winds on the tuner really well, and I used it to check the winch
  worked at all, by tying an object to it and lifting it. The problem is that it
  is floppy, so you cannot push it through the small holes in the tentacle. A
  cable you can push is worth more here than a strong one.
- **Nylon fishing line, 0.5 mm.** What I ended up using:
  <https://www.amazon.fr/dp/B0B8N7151L> (100 m, sold as ~21 kg). Goes through
  the tentacle easily and winds fine with the knot. Shoggoth Mini uses 0.5 mm
  too.

Using the twine first was useful because it split the problem in two: does the
winch work, and does the cable fit. One question at a time.

One thing I would still do if I carried on: stop the software ever leaving the
cable completely slack, and keep a little tension on it at rest. Nothing in the
code does that today, and how much tension it needs was never measured.

---

## The motor only counts one turn

The STS3215 encoder goes 0–4095 over one turn and does not count how many turns
you have done. I checked, and there is no multi-turn mode in `scservo_sdk` or in
LeRobot's Feetech table. For a winch that needs several turns, that is a
problem.

Two things follow:

- You cannot use `Goal_Position`, because it cannot describe a target more than
  one turn away. The winch has to run in **velocity mode**.
- You have to count the turns yourself in software, by adding up the
  *differences* between readings. If you convert to an absolute position and
  send that instead, you get a big jump every time the encoder passes 4095 → 0,
  and the motor jerks.

[`software/robot_tools.py`](../software/robot_tools.py) already does this.
`multiturn` keeps a running total and drives the motor by velocity, while the
other five joints work normally. `spool` lets you wind an exact number of
turns, counted on the encoder instead of by timing.

**What I actually ended up using is simpler.** Recording and replay
(`record_winch.py`, `replay_winch.py`) do not track turns at all. They use
bang-bang zone control: past the high threshold wind one way, past the low one
wind the other, stop in between. Counting turns matters if you want to command a
position; for driving the winch by hand and recording what you did, the zones
are enough. `multiturn` is still there if you need the count.

---

## The bus drops commands when the motor is loaded

You get `RuntimeError` / "Input voltage error" while the winch is pulling.

LeRobot's own `num_retry` retries immediately, one after another, so all the
tries can land in the same voltage dip and all fail. Waiting a few tens of
milliseconds between tries works much better.

The dangerous case is when the failed command is `Goal_Velocity = 0`. If that
one gets dropped, the motor keeps spinning. `robot_tools.py` retries the stop
several times and prints a warning telling you to cut the power by hand if it
cannot confirm the motor stopped. Keep that if you rewrite it.

---

## Building and mounting the parts

- **Leave room for the screwdriver.** Partway through I had to cut extra space
  into the support and into the camera mount, because there was no room to get
  a screw in. Check that before printing, not after.
- **Getting the motor into the support** works well but takes a few tries to
  get the feel for it. Use the lower pressure hole.
- **Watch the weight and the torque** if you change the design. Everything you
  add sits at the end of the arm, and the motors have to hold it.
- **Round off anything you push with a finger.** Motor 6 has to be turned by
  hand to its neutral position fairly often, and the first tuner attachment had
  a sharp corner right where you push. V2 rounds it. Small change, and you
  notice it every time.

---

## Windows and LeRobot

- **Ports are `COMx`.** Find them with `lerobot-find-port`. The number can
  change if you plug into a different USB port or through a dock, so they live
  in [`software/config.py`](../software/config.py) instead of in every script.
- **`so_follower` vs `so101_follower`.** Both are right, in different places:

  ```python
  from lerobot.robots.so_follower import SO101Follower, SO101FollowerConfig   # works
  from lerobot.robots.so101_follower import SO101Follower                     # fails
  ```
  ```powershell
  lerobot-calibrate --robot.type=so101_follower --robot.port=COM3 --robot.id=my_arm
  ```

  The import path is `so_follower`, but `so101_follower` is still the right
  name for `--robot.type` on the command line. The module used to be called
  `so101_follower` and was renamed, which is why `s0101code_simo/` does not
  import: it pins lerobot 0.4.1 and `robot_tools.py` runs on 0.6.0. Check your
  version before copying an import from the internet.
- **Redo the calibration, do not reuse it.** Type `c` at the prompt. An old
  calibration file gives you joint values that look fine but are shifted.
- **PowerShell uses a backtick** to continue a line, not a backslash. Linux
  docs will give you the wrong one.
- **`--display_data` needs an extra you may not have.** The Rerun viewer comes
  from `rerun-sdk`, which lerobot only pulls in with its `viz` extra. Install
  `lerobot[feetech,viz]`, or the flag fails on a clean environment.
- **Stop with ESC, not Ctrl+C**, in the commands that open a Rerun window. The
  viewer takes the focus, and Ctrl+C only reaches the program while the terminal
  has it.
