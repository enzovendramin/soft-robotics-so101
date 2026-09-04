"""
Manual testing/diagnostic CLI for the SO-101 leader/follower pair.
Consolidates the one-off scripts used to validate hardware before running
lerobot-teleoperate / lerobot-record.

Usage:
  python robot_tools.py move shoulder_pan --step 10
  python robot_tools.py move wrist_flex --step 15 --wait 1.0
  python robot_tools.py read-leader --seconds 20
  python robot_tools.py spool
  python robot_tools.py multiturn --turns 1
  python robot_tools.py trigger --high 80 --low 20 --speed 800
  python robot_tools.py trigger --high 80 --low 20 --speed 800 --display_data
  python robot_tools.py keyboard
"""

import argparse
import time

from config import CAMERA_TOP_INDEX, CAMERA_WRIST_INDEX, FOLLOWER_ID, FOLLOWER_PORT, LEADER_ID, LEADER_PORT


def retry_call(fn, attempts=3, delay=0.05):
    """Call fn() up to `attempts` times, sleeping `delay` seconds between
    failures. The Feetech bus's own num_retry retries back-to-back with no
    pause, which doesn't help against a brief voltage sag (tens of ms) --
    all instant retries can land inside the same bad window. A short real
    delay gives the rail a chance to recover before the next attempt.
    Returns (True, result) on success, (False, None) if all attempts fail."""
    for i in range(attempts):
        try:
            return True, fn()
        except RuntimeError as e:
            if i == attempts - 1:
                print(f"\n  [failed after {attempts} attempts: {e}]")
            else:
                time.sleep(delay)
    return False, None


def safe_stop(bus, motor, attempts=5):
    """Best-effort emergency stop: a single failed 'Goal_Velocity=0' write
    (e.g. the transient 'Input voltage error' seen under load) must never be
    allowed to leave the motor spinning uncommanded, so this retries several
    times before giving up and loudly warning the user."""
    for i in range(attempts):
        try:
            bus.write("Goal_Velocity", motor, 0, num_retry=2)
            return True
        except RuntimeError as e:
            print(f"\n  [stop attempt {i + 1}/{attempts} failed: {e}]")
            time.sleep(0.1)
    print("\n  !!! COULD NOT CONFIRM THE MOTOR STOPPED -- CUT POWER MANUALLY IF IT'S STILL MOVING !!!")
    return False


def read_hot(bus, motor):
    """Load/current/temp (no voltage) -- cheap enough for tight control loops.
    Returns None on a transient bus/servo error (e.g. the Feetech 'Input
    voltage error' seen under load) instead of raising, so callers can stop
    the motor safely."""
    try:
        load = bus.read("Present_Load", motor, normalize=False)
        current_a = bus.read("Present_Current", motor, normalize=False) * 0.0065
        temp_c = bus.read("Present_Temperature", motor, normalize=False)
        return load, current_a, temp_c
    except RuntimeError as e:
        print(f"\n  [read error: {e}]")
        return None


def cmd_move(args):
    from lerobot.robots.so_follower import SO101Follower, SO101FollowerConfig

    config = SO101FollowerConfig(port=args.port, id=args.id)
    robot = SO101Follower(config)
    robot.connect()

    obs = robot.get_observation()
    print("\n--- initial positions ---")
    for name, value in obs.items():
        print(f"{name}: {value:.1f}")

    joint_key = f"{args.joint}.pos"
    if joint_key not in obs:
        robot.disconnect()
        raise SystemExit(f"Unknown joint '{args.joint}'. Options: {[k.removesuffix('.pos') for k in obs]}")
    start = obs[joint_key]

    input("\npress ENTER to start the routine (Ctrl+C to cancel)...")

    print(f"\nmoving {args.joint} by {args.step:+.1f} deg")
    robot.send_action({joint_key: start + args.step})
    time.sleep(args.wait)
    reached = robot.get_observation()[joint_key]
    print(f"  readback -> {reached:.1f}")

    print(f"\nreturning {args.joint} to start")
    robot.send_action({joint_key: start})
    time.sleep(args.wait)

    print("\n--- summary ---")
    print(f"{args.joint}: requested {start + args.step:.1f}, readback {reached:.1f} (start {start:.1f})")

    input("\nhold the arm and press ENTER to disconnect...")
    robot.disconnect()
    print("disconnected.")


def cmd_read_leader(args):
    from lerobot.teleoperators.so_leader import SO101Leader, SOLeaderTeleopConfig

    config = SOLeaderTeleopConfig(port=args.port, id=args.id)
    teleop = SO101Leader(config)
    teleop.connect()

    print(f"\nMove the leader by hand. Printing for ~{args.seconds:.0f}s. Ctrl+C to stop early.\n")
    try:
        start = time.time()
        while time.time() - start < args.seconds:
            action = teleop.get_action()
            line = "  ".join(f"{k}={v:6.1f}" for k, v in action.items())
            print(line, end="\r")
            time.sleep(0.2)
    except KeyboardInterrupt:
        pass

    print("\n\ndisconnecting...")
    teleop.disconnect()
    print("disconnected.")


def cmd_spool(args):
    """Interactive REPL to test the gripper motor as a cable winch/spool.
    Keeps the connection open and switches Operating_Mode to VELOCITY, so
    each 'roll' is fast to issue without reconnecting every time.

    Commands:
      dir cw | dir ccw   set direction
      speed <value>      set Goal_Velocity magnitude
      torque <0-1000>    set Torque_Limit
      roll <turns>       spin exactly N full spool turns (tracked via the
                          encoder, not a time guess), streaming telemetry
      status             print one telemetry snapshot
      quit               stop and disconnect
    """
    from lerobot.motors.feetech import OperatingMode
    from lerobot.robots.so_follower import SO101Follower, SO101FollowerConfig

    config = SO101FollowerConfig(port=args.port, id=args.id)
    robot = SO101Follower(config)
    robot.connect()

    bus = robot.bus
    motor = "gripper"
    resolution = bus.model_resolution_table[bus.motors[motor].model]

    bus.disable_torque(motor)
    bus.write("Operating_Mode", motor, OperatingMode.VELOCITY.value)
    bus.enable_torque(motor)

    direction = 1
    speed = 300

    # Raw-unit conversions per Feetech STS/SMS datasheet convention
    # (not independently verified against this exact firmware revision):
    # Present_Current: 6.5 mA/unit, Present_Voltage: 0.1 V/unit,
    # Present_Load: signed, magnitude/1000 = fraction of rated torque.

    def read_status():
        """Full telemetry incl. voltage and the configured torque limit. Used only for the
        low-frequency 'status' command."""
        load = bus.read("Present_Load", motor, normalize=False)
        current_a = bus.read("Present_Current", motor, normalize=False) * 0.0065
        voltage_v = bus.read("Present_Voltage", motor, normalize=False) * 0.1
        temp_c = bus.read("Present_Temperature", motor, normalize=False)
        torque_limit = bus.read("Torque_Limit", motor, normalize=False)
        return load, current_a, voltage_v, temp_c, torque_limit

    def roll(turns):
        target_ticks = turns * resolution
        prev_pos = bus.read("Present_Position", motor, normalize=False)
        traveled = 0.0
        peak_load, peak_current, peak_temp = 0, 0.0, 0
        ok, _ = retry_call(lambda: bus.write("Goal_Velocity", motor, direction * speed))
        if not ok:
            print("  [failed to start]")
            return
        print(f"\nrolling {turns} turn(s), direction={'CW' if direction > 0 else 'CCW'}, speed={speed}")
        try:
            while traveled < target_ticks:
                ok, pos = retry_call(lambda: bus.read("Present_Position", motor, normalize=False))
                if not ok:
                    break
                delta = pos - prev_pos
                if delta > resolution / 2:
                    delta -= resolution
                elif delta < -resolution / 2:
                    delta += resolution
                traveled += abs(delta)
                prev_pos = pos

                status = read_hot(bus, motor)
                if status is None:
                    break
                load, current_a, temp_c = status
                peak_load = max(peak_load, abs(load))
                peak_current = max(peak_current, current_a)
                peak_temp = max(peak_temp, temp_c)
                print(
                    f"  turns={traveled / resolution:5.2f}/{turns}  load={load / 10:6.1f}%  "
                    f"current={current_a:5.2f}A  temp={temp_c:3d}C",
                    end="\r",
                )
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n  interrupted")
        finally:
            safe_stop(bus, motor)
        print(f"\n  done. peak load={peak_load / 10:.1f}%  peak current={peak_current:.2f}A  peak temp={peak_temp}C")

    def live_keys():
        import keyboard

        print("\nHold D (or Right arrow) to spin CW, A (or Left arrow) to spin CCW. Release to stop. ESC to exit.\n")
        prev_pos = bus.read("Present_Position", motor, normalize=False)
        net_turns = 0.0
        while True:
            if keyboard.is_pressed("esc"):
                break
            if keyboard.is_pressed("d") or keyboard.is_pressed("right"):
                cmd_speed = speed
            elif keyboard.is_pressed("a") or keyboard.is_pressed("left"):
                cmd_speed = -speed
            else:
                cmd_speed = 0
            ok, _ = retry_call(lambda: bus.write("Goal_Velocity", motor, cmd_speed))
            if not ok:
                safe_stop(bus, motor)
                break

            ok, pos = retry_call(lambda: bus.read("Present_Position", motor, normalize=False))
            if not ok:
                break
            delta = pos - prev_pos
            if delta > resolution / 2:
                delta -= resolution
            elif delta < -resolution / 2:
                delta += resolution
            net_turns += delta / resolution
            prev_pos = pos

            status = read_hot(bus, motor)
            if status is None:
                break
            load, current_a, temp_c = status
            print(
                f"  turns={net_turns:6.2f}  cmd_speed={cmd_speed:5d}  load={load / 10:6.1f}%  "
                f"current={current_a:5.2f}A  temp={temp_c:3d}C",
                end="\r",
            )
            time.sleep(0.05)

        safe_stop(bus, motor)
        print(f"\n  exited keys mode. net turns={net_turns:.2f}")

    print("\nSpool test REPL. Commands:")
    print("  dir cw | dir ccw    set direction (used by 'roll')")
    print("  speed <value>       set Goal_Velocity magnitude (e.g. 500)")
    print("  torque <0-1000>     set Torque_Limit")
    print("  roll <turns>        spin N full turns in the current direction, streaming telemetry")
    print("  keys                live control: hold D/Right = CW, A/Left = CCW, ESC = exit")
    print("  status              print a single telemetry snapshot")
    print("  quit                stop and disconnect\n")

    while True:
        try:
            raw = input("> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            break
        if not raw:
            continue
        parts = raw.split()
        cmd = parts[0]

        if cmd in ("quit", "exit", "q"):
            break
        elif cmd == "dir" and len(parts) == 2:
            direction = 1 if parts[1] in ("cw", "1", "+") else -1
            print(f"direction set to {'CW' if direction > 0 else 'CCW'}")
        elif cmd == "speed" and len(parts) == 2:
            speed = int(parts[1])
            print(f"speed set to {speed}")
        elif cmd == "torque" and len(parts) == 2:
            value = max(0, min(1000, int(parts[1])))
            bus.write("Torque_Limit", motor, value)
            print(f"Torque_Limit set to {value}")
        elif cmd == "roll" and len(parts) == 2:
            try:
                turns = float(parts[1])
            except ValueError:
                print("usage: roll <turns>")
                continue
            roll(turns)
        elif cmd == "keys":
            live_keys()
        elif cmd == "status":
            try:
                load, current_a, voltage_v, temp_c, torque_limit = read_status()
                print(
                    f"load={load / 10:.1f}%  current={current_a:.2f}A  voltage={voltage_v:.1f}V  "
                    f"temp={temp_c}C  torque_limit={torque_limit}/1000"
                )
            except RuntimeError as e:
                print(f"[read error: {e}]")
        else:
            print("unknown command")

    safe_stop(bus, motor)
    bus.disable_torque(motor)
    bus.write("Operating_Mode", motor, OperatingMode.POSITION.value)
    robot.disconnect()
    print("disconnected (gripper reset back to position mode).")


def cmd_multiturn(args):
    """Custom teleop loop: the leader's gripper trigger (proportional, single
    turn) drives N full turns of the follower's gripper/winch motor.

    The STS3215 has no native multi-turn mode (confirmed: absent from both
    scservo_sdk and lerobot's Feetech control table), so this tracks the
    follower's "unwrapped" cumulative position in software by integrating
    wrap-corrected deltas of Present_Position, and closes a velocity
    P-controller around the error against a target derived from the leader's
    0-100% reading. Goal_Position can't represent multi-turn targets, so the
    gripper is driven in VELOCITY mode throughout, not POSITION mode. The
    other 5 joints teleoperate normally (position mode) in the same loop.

    Stop with ESC (works regardless of which window has focus -- Ctrl+C only
    works if the terminal itself is focused).
    """
    import keyboard

    from lerobot.motors.feetech import OperatingMode
    from lerobot.robots.so_follower import SO101Follower, SO101FollowerConfig
    from lerobot.teleoperators.so_leader import SO101Leader, SOLeaderTeleopConfig

    teleop = SO101Leader(SOLeaderTeleopConfig(port=args.leader_port, id=args.leader_id))
    robot = SO101Follower(SO101FollowerConfig(port=args.port, id=args.id))
    teleop.connect()
    robot.connect()

    bus = robot.bus
    motor = "gripper"
    resolution = bus.model_resolution_table[bus.motors[motor].model]
    turn_ticks = args.turns * resolution

    bus.disable_torque(motor)
    bus.write("Operating_Mode", motor, OperatingMode.VELOCITY.value)
    bus.write("Torque_Limit", motor, args.torque)
    bus.enable_torque(motor)

    # Sync the unwrapped estimate to the leader's current reading so the
    # follower doesn't jump on the first iteration.
    leader_pct = teleop.get_action()[f"{motor}.pos"]
    prev_leader_pct = leader_pct
    est_ticks = (leader_pct / 100.0) * turn_ticks
    prev_raw = bus.read("Present_Position", motor, normalize=False)
    still_count = 0

    period = 1.0 / args.hz
    print(
        f"\nMulti-turn teleop: leader gripper -> {args.turns} follower turn(s). "
        f"Kp={args.kp}  max_speed={args.max_speed}  torque_limit={args.torque}/1000  "
        f"deadband={args.deadband} ticks  @ {args.hz}Hz.\n"
        f"Hold-on-release: leader still for {args.still_iters} ticks (delta<{args.still_delta}%) -> force stop.\n"
        "ESC (or Ctrl+C) to stop.\n"
    )

    last_print = 0.0
    try:
        while True:
            if keyboard.is_pressed("esc"):
                print("\nstopped (ESC)")
                break

            loop_start = time.time()
            action = teleop.get_action()

            # Other 5 joints: normal position teleop.
            other_action = {k: v for k, v in action.items() if not k.startswith(f"{motor}.")}
            robot.send_action(other_action)

            # Gripper: unwrap the follower's actual position and close a
            # velocity loop around the leader-driven multi-turn target.
            ok, raw = retry_call(lambda: bus.read("Present_Position", motor, normalize=False))
            if not ok:
                safe_stop(bus, motor)
                break
            delta = raw - prev_raw
            if delta > resolution / 2:
                delta -= resolution
            elif delta < -resolution / 2:
                delta += resolution
            est_ticks += delta
            prev_raw = raw

            leader_pct = action[f"{motor}.pos"]
            target_ticks = (leader_pct / 100.0) * turn_ticks

            # Hold-on-release: once the leader stops changing for a few
            # ticks in a row, snap the estimate to the target and force a
            # hard stop instead of chasing a possibly drifted error forever.
            # This is what makes releasing the leader immediately responsive.
            if abs(leader_pct - prev_leader_pct) < args.still_delta:
                still_count += 1
            else:
                still_count = 0
            prev_leader_pct = leader_pct

            held = still_count >= args.still_iters
            if held:
                est_ticks = target_ticks

            error = target_ticks - est_ticks
            if held or abs(error) < args.deadband:
                speed_cmd = 0.0
            else:
                speed_cmd = max(-args.max_speed, min(args.max_speed, args.kp * error))
            ok, _ = retry_call(lambda: bus.write("Goal_Velocity", motor, int(speed_cmd)))
            if not ok:
                safe_stop(bus, motor)
                break

            if time.time() - last_print > 0.2:
                status = read_hot(bus, motor)
                telemetry = (
                    f"load={status[0] / 10:5.1f}%  current={status[1]:4.2f}A  temp={status[2]:2d}C"
                    if status is not None
                    else "load=  ??%  current=??A  temp=??C"
                )
                print(
                    f"  leader={action[f'{motor}.pos']:5.1f}%  target={target_ticks / resolution:5.2f}t  "
                    f"actual={est_ticks / resolution:5.2f}t  error={error / resolution:6.2f}t  "
                    f"speed_cmd={int(speed_cmd):5d}  {'HOLD' if held else '    '}  {telemetry}",
                    end="\r",
                )
                last_print = time.time()

            time.sleep(max(0.0, period - (time.time() - loop_start)))
    except KeyboardInterrupt:
        print("\nstopped by user")
    finally:
        safe_stop(bus, motor)
        bus.disable_torque(motor)
        bus.write("Operating_Mode", motor, OperatingMode.POSITION.value)
        teleop.disconnect()
        robot.disconnect()
        print("disconnected (gripper reset back to position mode).")


def cmd_trigger(args):
    """Simple bang-bang winch control: no position mapping, no P-controller.
    The leader's gripper reading (0-100%) is split into three zones -- near
    max drives the follower continuously CW, near min drives it continuously
    CCW, and the middle band is a dead zone (motor stopped). The other 5
    joints teleoperate normally (position mode) in the same loop.

    Pass --display_data to also stream both cameras + joint state to a live
    Rerun viewer window, same as lerobot-teleoperate's --display_data.

    Stop with ESC (works regardless of which window has focus -- Ctrl+C only
    works if the terminal itself is focused, which the Rerun window steals).
    """
    import keyboard

    from lerobot.motors.feetech import OperatingMode
    from lerobot.robots.so_follower import SO101Follower, SO101FollowerConfig
    from lerobot.teleoperators.so_leader import SO101Leader, SOLeaderTeleopConfig

    cameras = {}
    log_visualization_data = None
    if args.display_data:
        from lerobot.cameras.opencv import OpenCVCameraConfig
        from lerobot.utils.visualization_utils import (
            init_visualization,
            log_visualization_data,
            shutdown_visualization,
        )

        cameras = {
            "wrist": OpenCVCameraConfig(index_or_path=CAMERA_WRIST_INDEX, width=640, height=360, fps=30),
            "top": OpenCVCameraConfig(index_or_path=CAMERA_TOP_INDEX, width=640, height=480, fps=30),
        }

    teleop = SO101Leader(SOLeaderTeleopConfig(port=args.leader_port, id=args.leader_id))
    robot = SO101Follower(SO101FollowerConfig(port=args.port, id=args.id, cameras=cameras))
    teleop.connect()
    robot.connect()

    if args.display_data:
        init_visualization("rerun", session_name="trigger")

    bus = robot.bus
    motor = "gripper"

    bus.disable_torque(motor)
    bus.write("Operating_Mode", motor, OperatingMode.VELOCITY.value)
    bus.write("Torque_Limit", motor, args.torque)
    bus.enable_torque(motor)

    period = 1.0 / args.hz
    print(
        f"\nTrigger winch: leader% >= {args.high} -> CW @ {args.speed}, "
        f"<= {args.low} -> CCW @ {args.speed}, in between -> stop.\n"
        f"torque_limit={args.torque}/1000  @ {args.hz}Hz.  ESC (or Ctrl+C) to stop.\n"
    )

    last_print = 0.0
    try:
        while True:
            if keyboard.is_pressed("esc"):
                print("\nstopped (ESC)")
                break

            loop_start = time.time()
            action = teleop.get_action()

            # Only fetch camera frames + joint readback when actually visualizing --
            # this is a full 6-motor read plus 2 camera reads, skip it otherwise.
            obs = robot.get_observation() if args.display_data else None

            # Other 5 joints: normal position teleop.
            other_action = {k: v for k, v in action.items() if not k.startswith(f"{motor}.")}
            robot.send_action(other_action)

            leader_pct = action[f"{motor}.pos"]
            if leader_pct >= args.high:
                speed_cmd = args.speed
            elif leader_pct <= args.low:
                speed_cmd = -args.speed
            else:
                speed_cmd = 0
            ok, _ = retry_call(lambda: bus.write("Goal_Velocity", motor, speed_cmd))
            if not ok:
                safe_stop(bus, motor)
                break

            if args.display_data:
                log_visualization_data("rerun", observation=obs, action=action)

            if time.time() - last_print > 0.2:
                zone = "CW" if speed_cmd > 0 else ("CCW" if speed_cmd < 0 else "stop")
                status = read_hot(bus, motor)
                telemetry = (
                    f"load={status[0] / 10:5.1f}%  current={status[1]:4.2f}A  temp={status[2]:2d}C"
                    if status is not None
                    else "load=  ??%  current=??A  temp=??C"
                )
                print(
                    f"  leader={leader_pct:5.1f}%  zone={zone:4s}  speed_cmd={speed_cmd:5d}  {telemetry}",
                    end="\r",
                )
                last_print = time.time()

            time.sleep(max(0.0, period - (time.time() - loop_start)))
    except KeyboardInterrupt:
        print("\nstopped by user")
    finally:
        safe_stop(bus, motor)
        bus.disable_torque(motor)
        bus.write("Operating_Mode", motor, OperatingMode.POSITION.value)
        if args.display_data:
            shutdown_visualization("rerun")
        teleop.disconnect()
        robot.disconnect()
        print("disconnected (gripper reset back to position mode).")


def cmd_keyboard(args):
    import keyboard

    from lerobot.robots.so_follower import SO101Follower, SO101FollowerConfig

    config = SO101FollowerConfig(port=args.port, id=args.id)
    robot = SO101Follower(config)
    robot.connect()

    targets = dict(robot.get_observation())

    print("\nControls:")
    print("  wrist_roll  : A / D")
    print("  wrist_flex  : W / S")
    print("  gripper     : Q (open) / E (close)")
    print("  ESC to quit and disconnect\n")

    running = True
    while running:
        moved = False

        if keyboard.is_pressed("a"):
            targets["wrist_roll.pos"] -= args.step
            moved = True
        if keyboard.is_pressed("d"):
            targets["wrist_roll.pos"] += args.step
            moved = True
        if keyboard.is_pressed("w"):
            targets["wrist_flex.pos"] += args.step
            moved = True
        if keyboard.is_pressed("s"):
            targets["wrist_flex.pos"] -= args.step
            moved = True
        if keyboard.is_pressed("q"):
            targets["gripper.pos"] += args.step
            moved = True
        if keyboard.is_pressed("e"):
            targets["gripper.pos"] -= args.step
            moved = True
        if keyboard.is_pressed("esc"):
            running = False
            break

        if moved:
            robot.send_action(
                {
                    "wrist_roll.pos": targets["wrist_roll.pos"],
                    "wrist_flex.pos": targets["wrist_flex.pos"],
                    "gripper.pos": targets["gripper.pos"],
                }
            )
            print(
                f"roll={targets['wrist_roll.pos']:.1f}  "
                f"flex={targets['wrist_flex.pos']:.1f}  "
                f"gripper={targets['gripper.pos']:.1f}",
                end="\r",
            )

        time.sleep(0.05)

    input("\n\nhold the arm and press ENTER to disconnect...")
    robot.disconnect()
    print("disconnected.")


def main():
    parser = argparse.ArgumentParser(description="Manual testing/diagnostic tools for the SO-101 arms.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_move = sub.add_parser("move", help="Move a single follower joint and read back the result.")
    p_move.add_argument(
        "joint",
        help="shoulder_pan, shoulder_lift, elbow_flex, wrist_flex, wrist_roll, or gripper",
    )
    p_move.add_argument("--step", type=float, default=10.0, help="Relative move in degrees (default: 10)")
    p_move.add_argument("--wait", type=float, default=1.5, help="Seconds to wait after each move")
    p_move.add_argument("--port", default=FOLLOWER_PORT)
    p_move.add_argument("--id", default=FOLLOWER_ID)
    p_move.set_defaults(func=cmd_move)

    p_leader = sub.add_parser("read-leader", help="Continuously print the leader's raw joint positions.")
    p_leader.add_argument("--seconds", type=float, default=20.0)
    p_leader.add_argument("--port", default=LEADER_PORT)
    p_leader.add_argument("--id", default=LEADER_ID)
    p_leader.set_defaults(func=cmd_read_leader)

    p_spool = sub.add_parser(
        "spool", help="Interactive REPL to test the gripper as a cable winch (dir/speed/torque/roll)."
    )
    p_spool.add_argument("--port", default=FOLLOWER_PORT)
    p_spool.add_argument("--id", default=FOLLOWER_ID)
    p_spool.set_defaults(func=cmd_spool)

    p_mt = sub.add_parser(
        "multiturn",
        help="Teleop where the leader's gripper drives N full turns of the follower's winch motor.",
    )
    p_mt.add_argument("--turns", type=float, default=1.0, help="Follower turns spanning the leader's full range")
    p_mt.add_argument("--kp", type=float, default=0.3, help="Proportional gain, speed units per tick of error")
    p_mt.add_argument("--max-speed", type=int, default=400, help="Velocity clamp (raw Goal_Velocity units)")
    p_mt.add_argument("--torque", type=int, default=1000, help="Torque_Limit written at startup (0-1000)")
    p_mt.add_argument("--deadband", type=float, default=20.0, help="Error (ticks) below which speed is forced to 0")
    p_mt.add_argument("--hz", type=float, default=25.0, help="Control loop rate")
    p_mt.add_argument(
        "--still-delta", type=float, default=0.3, help="Leader %% change below which a tick counts as 'still'"
    )
    p_mt.add_argument(
        "--still-iters", type=int, default=3, help="Consecutive still ticks before forcing a hard stop"
    )
    p_mt.add_argument("--port", default=FOLLOWER_PORT)
    p_mt.add_argument("--id", default=FOLLOWER_ID)
    p_mt.add_argument("--leader-port", default=LEADER_PORT)
    p_mt.add_argument("--leader-id", default=LEADER_ID)
    p_mt.set_defaults(func=cmd_multiturn)

    p_tr = sub.add_parser(
        "trigger",
        help="Bang-bang winch control: leader gripper near max/min spins the follower CW/CCW continuously.",
    )
    p_tr.add_argument("--high", type=float, default=80.0, help="Leader %% at/above which -> spin CW")
    p_tr.add_argument("--low", type=float, default=20.0, help="Leader %% at/below which -> spin CCW")
    p_tr.add_argument("--speed", type=int, default=800, help="Constant speed used in either zone")
    p_tr.add_argument("--torque", type=int, default=1000, help="Torque_Limit written at startup (0-1000)")
    p_tr.add_argument("--hz", type=float, default=25.0, help="Control loop rate")
    p_tr.add_argument(
        "--display_data", action="store_true", help="Stream both cameras + joint state to a live Rerun window"
    )
    p_tr.add_argument("--port", default=FOLLOWER_PORT)
    p_tr.add_argument("--id", default=FOLLOWER_ID)
    p_tr.add_argument("--leader-port", default=LEADER_PORT)
    p_tr.add_argument("--leader-id", default=LEADER_ID)
    p_tr.set_defaults(func=cmd_trigger)

    p_kb = sub.add_parser("keyboard", help="Interactive keyboard teleoperation of the follower.")
    p_kb.add_argument("--step", type=float, default=3.0, help="Degrees per key press")
    p_kb.add_argument("--port", default=FOLLOWER_PORT)
    p_kb.add_argument("--id", default=FOLLOWER_ID)
    p_kb.set_defaults(func=cmd_keyboard)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
