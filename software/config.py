"""
Central configuration for the SO-101 leader/follower + camera setup.
Imported by robot_tools.py and future scripts, instead of each one
hardcoding/duplicating the same values.

Update these whenever hardware is replugged -- USB-serial COM port
assignments on Windows are tied to the physical USB path, so moving a
device to a different port (e.g. through the Dell dock) can change its
COM number. Re-run `lerobot-find-port` / `lerobot-find-cameras opencv`
after any rewiring instead of assuming these are still correct.
"""

# Confirmed via lerobot-find-port after moving to the Dell dock: unchanged.
FOLLOWER_PORT = "COM3"
FOLLOWER_ID = "my_arm"

# Confirmed by elimination via lerobot-find-port (only COM3/COM4 present,
# COM3 = follower): unchanged.
LEADER_PORT = "COM4"
LEADER_ID = "my_arm_leader"

# Confirmed via `lerobot-find-cameras opencv` + checking the saved
# snapshots in outputs/captured_images/. Index 2 (laptop's built-in
# webcam) is not used.
CAMERA_WRIST_INDEX = 1  # mounted on the follower arm
CAMERA_TOP_INDEX = 0  # overhead, monitoring the environment
