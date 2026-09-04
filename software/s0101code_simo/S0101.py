from lerobot.robots.so101_follower import SO101Follower
from lerobot.teleoperators.so101_leader import SO101Leader

from S0101_hardware import build_follower_robot_config, build_leader_config

robot_config = build_follower_robot_config()
teleop_config = build_leader_config()

robot = SO101Follower(robot_config)
teleop_device = SO101Leader(teleop_config)
robot.connect()
teleop_device.connect()

while True:
    action = teleop_device.get_action()
    robot.send_action(action)
