"""
Records a LeRobotDataset via teleoperation, using the gripper/winch's
bang-bang trigger control (see robot_tools.py's `trigger` command) instead
of the standard position-mode gripper that lerobot-record assumes -- the
STS3215 has no native multi-turn mode, so a plain position-controlled
gripper can't drive the tentacle winch (see robot_tools.py for the full
diagnosis).

The recorded action for the gripper is the leader's raw 0-100% trigger
reading -- same schema as a normal position-controlled joint -- so a future
trained policy's predicted gripper value can be fed back through the same
zone logic (>=high -> CW, <=low -> CCW, else stop) at rollout time, instead
of being sent as a Goal_Position.

Episode controls (same as lerobot-record): -> / N ends the current episode
early, <- / R re-records the last one, ESC / Q stops recording entirely.

Usage:
  python record_winch.py --repo-id enzo/tentacle_pickplace --num-episodes 10 \
      --single-task "Pick up the toroid with the tentacle and drop it elsewhere" \
      --episode-time-s 20 --reset-time-s 10 --display_data

  # Add more episodes to the same dataset in a later session:
  python record_winch.py --repo-id enzo/tentacle_pickplace --num-episodes 5 \
      --single-task "Pick up the toroid with the tentacle and drop it elsewhere" \
      --resume
"""

import argparse
import time

from config import CAMERA_TOP_INDEX, CAMERA_WRIST_INDEX, FOLLOWER_ID, FOLLOWER_PORT, LEADER_ID, LEADER_PORT
from robot_tools import read_hot, retry_call, safe_stop

MOTOR = "gripper"


def build_configs(args):
    from lerobot.cameras.opencv import OpenCVCameraConfig
    from lerobot.robots.so_follower import SO101FollowerConfig
    from lerobot.teleoperators.so_leader import SOLeaderTeleopConfig

    cameras = {
        "wrist": OpenCVCameraConfig(index_or_path=CAMERA_WRIST_INDEX, width=640, height=360, fps=args.fps),
        "top": OpenCVCameraConfig(index_or_path=CAMERA_TOP_INDEX, width=640, height=480, fps=args.fps),
    }
    robot_config = SO101FollowerConfig(port=FOLLOWER_PORT, id=FOLLOWER_ID, cameras=cameras)
    teleop_config = SOLeaderTeleopConfig(port=LEADER_PORT, id=LEADER_ID)
    return robot_config, teleop_config


def run_segment(robot, teleop, bus, dataset, events, args, control_time_s, record):
    """One episode's worth of control, optionally writing frames to `dataset`
    (pass dataset=None for the reset segment, which still teleoperates but
    doesn't record)."""
    from lerobot.utils.constants import ACTION, OBS_STR
    from lerobot.utils.feature_utils import build_dataset_frame
    from lerobot.utils.visualization_utils import log_visualization_data

    control_interval = 1.0 / args.fps
    last_print = 0.0
    timestamp = 0.0
    start = time.perf_counter()
    while timestamp < control_time_s:
        loop_start = time.perf_counter()

        if events["exit_early"]:
            events["exit_early"] = False
            break

        obs = robot.get_observation()
        action = teleop.get_action()

        # Other 5 joints: normal position teleop.
        other_action = {k: v for k, v in action.items() if not k.startswith(f"{MOTOR}.")}
        robot.send_action(other_action)

        # Gripper/winch: bang-bang zone control off the leader's raw trigger %.
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

        if record and dataset is not None:
            observation_frame = build_dataset_frame(dataset.features, obs, prefix=OBS_STR)
            action_frame = build_dataset_frame(dataset.features, action, prefix=ACTION)
            dataset.add_frame({**observation_frame, **action_frame, "task": args.single_task})

        if args.display_data:
            log_visualization_data("rerun", observation=obs, action=action)

        if time.time() - last_print > 0.2:
            zone = "CW" if speed_cmd > 0 else ("CCW" if speed_cmd < 0 else "stop")
            status = read_hot(bus, MOTOR)
            telemetry = (
                f"load={status[0] / 10:5.1f}%  current={status[1]:4.2f}A  temp={status[2]:2d}C"
                if status is not None
                else "load=  ??%  current=??A  temp=??C"
            )
            tag = "REC " if record else "reset"
            print(f"  [{tag}] t={timestamp:5.1f}/{control_time_s:.0f}s  leader={leader_pct:5.1f}%  zone={zone:4s}  {telemetry}", end="\r")
            last_print = time.time()

        dt_s = time.perf_counter() - loop_start
        time.sleep(max(0.0, control_interval - dt_s))
        timestamp = time.perf_counter() - start


def main():
    parser = argparse.ArgumentParser(description="Record a dataset using winch (trigger) control for the gripper.")
    parser.add_argument("--repo-id", required=True, help="e.g. enzo/tentacle_pickplace")
    parser.add_argument("--single-task", required=True, help="Short task description")
    parser.add_argument("--num-episodes", type=int, default=10)
    parser.add_argument("--episode-time-s", type=float, default=30.0)
    parser.add_argument("--reset-time-s", type=float, default=10.0)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--root", default=None, help="Local dataset dir; default is the HF cache")
    parser.add_argument("--resume", action="store_true", help="Append episodes to an existing dataset")
    parser.add_argument("--push-to-hub", action="store_true")
    parser.add_argument("--display_data", action="store_true", help="Live Rerun window with both cameras")
    # Winch control params (same meaning/defaults as robot_tools.py's `trigger`).
    parser.add_argument("--high", type=float, default=80.0)
    parser.add_argument("--low", type=float, default=20.0)
    parser.add_argument("--speed", type=int, default=800)
    parser.add_argument("--torque", type=int, default=1000)
    args = parser.parse_args()

    from lerobot.datasets.lerobot_dataset import LeRobotDataset
    from lerobot.motors.feetech import OperatingMode
    from lerobot.robots.so_follower import SO101Follower
    from lerobot.teleoperators.so_leader import SO101Leader
    from lerobot.utils.feature_utils import hw_to_dataset_features
    from lerobot.utils.keyboard_input import init_keyboard_listener
    from lerobot.utils.utils import log_say
    from lerobot.utils.visualization_utils import init_visualization, shutdown_visualization

    robot_config, teleop_config = build_configs(args)
    robot = SO101Follower(robot_config)
    teleop = SO101Leader(teleop_config)
    robot.connect()
    teleop.connect()

    bus = robot.bus
    bus.disable_torque(MOTOR)
    bus.write("Operating_Mode", MOTOR, OperatingMode.VELOCITY.value)
    bus.write("Torque_Limit", MOTOR, args.torque)
    bus.enable_torque(MOTOR)

    if args.resume:
        dataset = LeRobotDataset.resume(args.repo_id, root=args.root)
    else:
        action_features = hw_to_dataset_features(robot.action_features, "action")
        obs_features = hw_to_dataset_features(robot.observation_features, "observation")
        dataset = LeRobotDataset.create(
            args.repo_id,
            args.fps,
            root=args.root,
            robot_type=robot.name,
            features={**action_features, **obs_features},
            use_videos=True,
            image_writer_threads=4,
        )

    _, events = init_keyboard_listener()
    if args.display_data:
        init_visualization("rerun", session_name="record_winch")

    print(
        f"\nRecording '{args.repo_id}': up to {args.num_episodes} episode(s), "
        f"{args.episode_time_s:.0f}s each, {args.reset_time_s:.0f}s reset between.\n"
        "-> / N: end episode early    <- / R: re-record last episode    ESC / Q: stop\n"
    )

    try:
        episode_idx = 0
        while episode_idx < args.num_episodes and not events["stop_recording"]:
            log_say(f"Recording episode {episode_idx + 1} of {args.num_episodes}", play_sounds=False)
            run_segment(robot, teleop, bus, dataset, events, args, args.episode_time_s, record=True)

            if not events["stop_recording"] and (
                episode_idx < args.num_episodes - 1 or events["rerecord_episode"]
            ):
                log_say("Reset the environment", play_sounds=False)
                run_segment(robot, teleop, bus, None, events, args, args.reset_time_s, record=False)

            if events["rerecord_episode"]:
                log_say("Re-recording episode", play_sounds=False)
                events["rerecord_episode"] = False
                events["exit_early"] = False
                dataset.clear_episode_buffer()
                continue

            dataset.save_episode()
            episode_idx += 1
    finally:
        log_say("Stop recording", play_sounds=False)
        safe_stop(bus, MOTOR)
        bus.disable_torque(MOTOR)
        bus.write("Operating_Mode", MOTOR, OperatingMode.POSITION.value)
        if dataset is not None:
            dataset.finalize()
        if args.display_data:
            shutdown_visualization("rerun")
        if robot.is_connected:
            robot.disconnect()
        if teleop.is_connected:
            teleop.disconnect()
        if args.push_to_hub and dataset is not None:
            dataset.push_to_hub()
        print("\ndone.")


if __name__ == "__main__":
    main()
