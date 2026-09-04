from __future__ import annotations

from pathlib import Path

from lerobot.cameras.opencv.configuration_opencv import OpenCVCameraConfig
from lerobot.robots.so101_follower import SO101FollowerConfig
from lerobot.teleoperators.so101_leader.config_so101_leader import SO101LeaderConfig

# Edit this file if Windows reassigns COM ports or camera indices.
# Keeping the mapping in one place prevents train/record/replay/eval drift.
FOLLOWER_PORT = "COM3"
LEADER_PORT = "COM4"

WRIST_CAMERA_INDEX = 2
FRONT_CAMERA_INDEX = 0
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_FPS = 30

DEFAULT_TRAIN_RUN = "act_so101_run2"
DEFAULT_POLICY_PATH = (
    Path(__file__).parent
    / "outputs"
    / "train"
    / DEFAULT_TRAIN_RUN
    / "checkpoints"
    / "last"
    / "pretrained_model"
)


def build_camera_configs() -> dict[str, OpenCVCameraConfig]:
    return {
        "wrist": OpenCVCameraConfig(
            index_or_path=WRIST_CAMERA_INDEX,
            width=CAMERA_WIDTH,
            height=CAMERA_HEIGHT,
            fps=CAMERA_FPS,
        ),
        "front": OpenCVCameraConfig(
            index_or_path=FRONT_CAMERA_INDEX,
            width=CAMERA_WIDTH,
            height=CAMERA_HEIGHT,
            fps=CAMERA_FPS,
        ),
    }


def build_follower_robot_config() -> SO101FollowerConfig:
    return SO101FollowerConfig(
        id="follower",
        cameras=build_camera_configs(),
        port=FOLLOWER_PORT,
    )


def build_leader_config() -> SO101LeaderConfig:
    return SO101LeaderConfig(
        id="leader",
        port=LEADER_PORT,
    )
