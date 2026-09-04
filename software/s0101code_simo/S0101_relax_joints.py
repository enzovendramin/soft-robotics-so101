"""Disable torque on all follower joints so they can be moved by hand."""
from lerobot.robots.so101_follower import SO101Follower
from S0101_hardware import build_follower_robot_config

robot = SO101Follower(build_follower_robot_config())
robot.connect()
robot.disconnect()  # disable_torque_on_disconnect=True releases all joints
print("Joints are now free to move by hand.")
