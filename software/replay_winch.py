"""
Replays a recorded episode on the follower, using the same bang-bang winch
control (see robot_tools.py's `trigger`) for the gripper instead of
lerobot-replay's stock robot.send_action() -- which would send the recorded
gripper.pos (the leader's raw 0-100% trigger reading at record time) as a
Goal_Position, moving the winch in single-turn position mode instead of
reproducing the actual continuous winding that happened during recording.

Usage:
  python replay_winch.py --repo-id enzo/tentacle_pickplace --episode 0
"""

import argparse
import time

from config import FOLLOWER_ID, FOLLOWER_PORT
from robot_tools import read_hot, retry_call, safe_stop

MOTOR = "gripper"


def main():
    parser = argparse.ArgumentParser(description="Replay a recorded episode using winch (trigger) control.")
    parser.add_argument("--repo-id", required=True)
    parser.add_argument("--episode", type=int, default=0)
    parser.add_argument("--root", default=None, help="Local dataset dir; default is the HF cache")
    parser.add_argument("--fps", type=int, default=None, help="Defaults to the dataset's own fps")
    parser.add_argument("--high", type=float, default=80.0)
    parser.add_argument("--low", type=float, default=20.0)
    parser.add_argument("--speed", type=int, default=800)
    parser.add_argument("--torque", type=int, default=1000)
    parser.add_argument("--port", default=FOLLOWER_PORT)
    parser.add_argument("--id", default=FOLLOWER_ID)
    args = parser.parse_args()

    import keyboard

    from lerobot.datasets import LeRobotDataset
    from lerobot.motors.feetech import OperatingMode
    from lerobot.robots.so_follower import SO101Follower, SO101FollowerConfig
    from lerobot.utils.constants import ACTION
    from lerobot.utils.robot_utils import precise_sleep

    dataset = LeRobotDataset(args.repo_id, root=args.root, episodes=[args.episode])
    actions = dataset.select_columns(ACTION)
    action_names = dataset.features[ACTION]["names"]
    fps = args.fps or dataset.fps

    robot = SO101Follower(SO101FollowerConfig(port=args.port, id=args.id))
    robot.connect()

    bus = robot.bus
    bus.disable_torque(MOTOR)
    bus.write("Operating_Mode", MOTOR, OperatingMode.VELOCITY.value)
    bus.write("Torque_Limit", MOTOR, args.torque)
    bus.enable_torque(MOTOR)

    print(
        f"\nReplaying '{args.repo_id}' episode {args.episode}: {dataset.num_frames} frames @ {fps}Hz.\n"
        f"Winch: leader% >= {args.high} -> CW @ {args.speed}, <= {args.low} -> CCW @ {args.speed}, "
        f"in between -> stop.  ESC to stop early.\n"
    )

    last_print = 0.0
    try:
        for idx in range(dataset.num_frames):
            if keyboard.is_pressed("esc"):
                print("\nstopped (ESC)")
                break

            loop_start = time.perf_counter()
            action_array = actions[idx][ACTION]
            action = {name: action_array[i] for i, name in enumerate(action_names)}

            # Other 5 joints: normal position replay.
            other_action = {k: v for k, v in action.items() if not k.startswith(f"{MOTOR}.")}
            robot.send_action(other_action)

            # Gripper/winch: same bang-bang zone control as recording time,
            # driven by the recorded leader trigger % instead of a live leader.
            leader_pct = action[f"{MOTOR}.pos"]
            if leader_pct >= args.high:
                speed_cmd = args.speed
            elif leader_pct <= args.low:
                speed_cmd = -args.speed
            else:
                speed_cmd = 0
            ok, _ = retry_call(lambda: bus.write("Goal_Velocity", MOTOR, speed_cmd))
            if not ok:
                safe_stop(bus, MOTOR)
                raise RuntimeError("winch write failed repeatedly -- stopped for safety")

            if time.time() - last_print > 0.2:
                zone = "CW" if speed_cmd > 0 else ("CCW" if speed_cmd < 0 else "stop")
                status = read_hot(bus, MOTOR)
                telemetry = (
                    f"load={status[0] / 10:5.1f}%  current={status[1]:4.2f}A  temp={status[2]:2d}C"
                    if status is not None
                    else "load=  ??%  current=??A  temp=??C"
                )
                print(
                    f"  frame={idx:5d}/{dataset.num_frames}  leader={leader_pct:5.1f}%  zone={zone:4s}  {telemetry}",
                    end="\r",
                )
                last_print = time.time()

            dt_s = time.perf_counter() - loop_start
            precise_sleep(max(1 / fps - dt_s, 0.0))
    finally:
        safe_stop(bus, MOTOR)
        bus.disable_torque(MOTOR)
        bus.write("Operating_Mode", MOTOR, OperatingMode.POSITION.value)
        robot.disconnect()
        print("\ndisconnected (gripper reset back to position mode).")


if __name__ == "__main__":
    main()
