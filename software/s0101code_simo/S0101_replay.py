from pathlib import Path

from lerobot.scripts.lerobot_replay import DatasetReplayConfig, ReplayConfig, replay

from S0101_hardware import CAMERA_FPS, build_follower_robot_config


# -----------------------------
# User params (edit in your IDE)
# -----------------------------
REPO_ID = "Simo-a/S0101_test"
EPISODE_INDEX = 0

# Optional: keep dataset local cache somewhere stable
DATASET_ROOT = None  # e.g. Path("./lerobot_datasets")

FPS = CAMERA_FPS
PLAY_SOUNDS = True


# -----------------------------
# Robot config (edit S0101_hardware.py to match your setup)
# -----------------------------
robot_config = build_follower_robot_config()

dataset_cfg = DatasetReplayConfig(
    repo_id=REPO_ID,
    episode=EPISODE_INDEX,
    root=DATASET_ROOT,
    fps=FPS,
)

cfg = ReplayConfig(
    robot=robot_config,
    dataset=dataset_cfg,
    play_sounds=PLAY_SOUNDS,
)

# Run replay
replay(cfg)
