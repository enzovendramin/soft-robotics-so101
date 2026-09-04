# Design decisions

Each section is a problem and what I did about it.

---

## 1. Driving the tentacle without adding motors

**Problem.** A tendon-driven tentacle needs something to pull its cable, and the
arm already has all six of its motors doing a job.

**What I did.** Motor 6 used to open and close the gripper. Now it winds a
single cable that bends the tentacle. Only two stock parts come off,
`Moving_Jaw_SO101` and `Wrist_Roll_Follower_SO101`, so the change is reversible:
reprint those and the normal gripper goes back on.

Why one cable:

- **Nothing new to add.** Same 6 motors, same bus, same power supply. Extra
  motors would also put extra weight right at the end of the arm, which is the
  worst place for it.
- **The other motors do the aiming.** Motor 5 rotates the plane the tentacle
  bends in, and joints 1 to 4 move the whole wrist. Between them you can put
  that plane wherever the task needs it, so one bending direction is not the
  limit it sounds like.
- **It is a known design, not a shortcut.** The HTDCR paper (Huertas Niño et
  al., 2025) builds a continuum robot the same way, one tendon to bend and a
  rotating base to aim, and shows it twists *less* under load than versions with
  several tendons.
- **Less to go wrong.** With several cables you have to keep the tension matched
  across all of them. With one there is a single thing to control.

**The cost.** The tentacle bends in one plane at a time, so you aim first and
bend second instead of commanding a direction directly. Bending any way at once
needs three cables. See [`next_steps.md`](next_steps.md).

---

## 2. Aiming the camera: the arc mounts

**Problem.** The camera has to keep the tentacle tip and the work area in frame,
and the angle that does that depends on the object and where it sits. Bolting it
on at a fixed angle means a reprint every time the setup changes.

**What I did.** A GoPro-style arc interface, which you set by hand and clamp.
The point is not to save prints, it is to keep the option open: whatever angle
you pick, you can change it later without touching the design.

No motor for this, on purpose. It would add a servo and its weight at the end
of the arm for something you set and leave alone.

The bracket went through three versions getting there:

- **V3**: the three arcs are part of the bracket, all the same thickness.
- **V4**: same idea, outer arc thicker to take the load, inner one thinner since
  it was not bending anyway.
- **V5**: the arcs come off the bracket completely. In their place a pocket for a
  heat-set insert, so a separate arc plate bolts on. That adds a second
  adjustable axis, and the arc part can be changed without reprinting the piece
  that holds the motor.

The camera mount clips onto this interface and you aim it by hand. The arcs
live on their own plate (`Rotation_Plate`), and that plate also glues onto an
adapted rigid claw (`Rotation_Claw`), which means the camera mounts identically
whether the arm has the tentacle or the normal jaws on it.

---

## 3. The tentacle, and hanging it clear of the table

**Problem.** The tentacle has to bend far, hold its shape under its own weight,
and actually grip something. And once it is mounted, the wrist sits low enough
that it touches the table.

**What I did.** Generated the tentacle with the **OpenSpiRobs** tool, which
makes the log-spiral shape, using dimensions close to an existing SpiRob that
was already known to work rather than guessing my own. The cable hole is bigger
than the reference so the line is easier to thread. Printed in TPU 95A with the
printer's default profile.

The spiral is what makes it grip. The tip curls first and the rest follows, so
it wraps around an object instead of shoving it away.

For the clearance, the base was extended to lift the whole arm off the table.

---

## 4. What the dataset records for the winch

**Problem.** A normal gripper has a position you can record. The winch does not.
It runs in velocity mode and can turn several times, so no single number means
"the gripper is here".

**What I did.** Record what the operator did instead: the leader trigger's raw
0 to 100% value. That maps onto the zone logic the winch already uses, which is
wind one way past the high threshold, the other way past the low one, stop in
between.

Two things this buys:

- The dataset keeps its normal shape, one number per joint including the
  gripper, so nothing downstream needs special-casing.
- A trained policy can output that same number and have it run through the same
  zones, instead of a `Goal_Position` the winch cannot use.

It is also why replaying needs `replay_winch.py` and not `lerobot-replay`. The
stock replay would send that 0 to 100% value as a position, and the winch would
move a fraction of a turn instead of winding.

---

## Open questions

None of these are answered, and all three need more use than I gave them:

- **How much tension the cable needs at rest.** Not tested.
- **Whether the clamped arcs hold long term.** They held their angle over
  repeated use, but not enough use to say for certain.
- **How much the tentacle can lift.** Same answer. It carried the test object
  fine, but I never loaded it far enough to find the limit.
