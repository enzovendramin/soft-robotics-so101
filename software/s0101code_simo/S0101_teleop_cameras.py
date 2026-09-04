import os
import shutil
import sys

import rerun as rr
from lerobot.processor import make_default_processors
from lerobot.robots.so101_follower import SO101Follower
from lerobot.teleoperators.so101_leader import SO101Leader
from lerobot.utils.visualization_utils import init_rerun, log_rerun_data

from S0101_hardware import build_follower_robot_config, build_leader_config

print("sys.executable:", sys.executable)
print("sys.prefix:", sys.prefix)
print("rerun python package:", rr.__file__)
print("rerun viewer on PATH:", shutil.which("rerun"))
print("PATH contains Scripts?:", os.path.join(sys.prefix, "Scripts") in os.environ.get("PATH", ""))

init_rerun(session_name="teleoperation")

robot_config = build_follower_robot_config()
teleop_config = build_leader_config()

robot = SO101Follower(robot_config)
teleop_device = SO101Leader(teleop_config)

teleop_action_processor, robot_action_processor, robot_observation_processor = make_default_processors()

robot.connect()
teleop_device.connect()

while True:
    obs = robot.get_observation()
    raw_action = teleop_device.get_action()

    # Process action & observation the right way
    teleop_action = teleop_action_processor((raw_action, obs))
    action_to_send = robot_action_processor((teleop_action, obs))
    robot.send_action(action_to_send)

    obs_processed = robot_observation_processor(obs)
    log_rerun_data(observation=obs_processed, action=teleop_action)

    # Log to rerun (exact logging keys depend on LeRobot utilities)
    # If lerobot_teleoperate uses helper functions, prefer those.
    # Minimal example:
    # if "front" in getattr(obs_processed, "images", {}):
    #     rr.log("camera/front", rr.Image(obs_processed.images["front"]))
