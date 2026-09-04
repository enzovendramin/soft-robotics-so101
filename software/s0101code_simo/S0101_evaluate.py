"""
Record evaluation rollouts on the real S0101 (SO101 follower) robot using a trained policy,
using the same backend as the `lerobot-record` CLI.

Edit the "User params" section in your IDE.
"""

from __future__ import annotations

from pathlib import Path

from lerobot.scripts.lerobot_record import DatasetRecordConfig, RecordConfig, record

from S0101_hardware import CAMERA_FPS, DEFAULT_POLICY_PATH, build_follower_robot_config
from S0101_policy_utils import install_action_debug_hook, install_action_noise_hook, load_saved_act_config


# --- Robot config ---
robot_config = build_follower_robot_config()

# --- Display ---
DISPLAY_DATA = True
PLAY_SOUNDS = True

# --- Dataset that will be CREATED by record() (your eval dataset) ---
EVAL_DATASET_REPO_ID = "Simo-a/eval_S0101"
NUM_EPISODES = 1
SINGLE_TASK = "Put the yellow ball in the white bowl"
DATASET_ROOT: Path | None = None  # e.g. Path("./eval_datasets") or None

# --- Policy checkpoint (ACT policy path / repo) ---
# Default to the latest saved checkpoint from the shared robot setup file.
POLICY_PATH = str(DEFAULT_POLICY_PATH)
POLICY_DEVICE = "cuda"  # "cpu" if needed
POLICY_DTYPE = None     # e.g. "float16", "bfloat16", "float32", or None

# --- Debug options ---
# Set ACTION_NOISE_STD > 0 to add Gaussian noise (degrees) to every action.
# Useful to verify the robot physically responds to larger commands.
# Set to 0 to disable. WARNING: robot will move erratically when enabled.
ACTION_NOISE_STD: float = 0.0


def main() -> None:
    install_action_debug_hook()
    if ACTION_NOISE_STD > 0:
        install_action_noise_hook(std=ACTION_NOISE_STD)

    policy_path = Path(POLICY_PATH)
    if not policy_path.exists():
        raise FileNotFoundError(
            f"Policy checkpoint not found: {policy_path}. "
            "Update S0101_hardware.py or POLICY_PATH before running evaluation."
        )

    dataset_cfg = DatasetRecordConfig(
        repo_id=EVAL_DATASET_REPO_ID,
        num_episodes=NUM_EPISODES,
        single_task=SINGLE_TASK,
        root=DATASET_ROOT,
        fps=CAMERA_FPS,
    )

    # Load the exact saved ACT config from the checkpoint, then only override
    # inference-time options like device / AMP in this script.
    policy_cfg = load_saved_act_config(policy_path)
    policy_cfg.pretrained_path = str(policy_path)
    policy_cfg.device = POLICY_DEVICE
    policy_cfg.use_amp = False
    # Execute the full predicted chunk before re-querying (chunk_size=50).
    # With n_action_steps=10 (the trained default) the robot re-queries every
    # 0.33 s from nearly the same position, causing it to stay stuck.
    # Setting this to chunk_size gives 1.67 s of committed motion per query.
    policy_cfg.n_action_steps = 50

    cfg = RecordConfig(
        robot=robot_config,
        dataset=dataset_cfg,
        policy=policy_cfg,
        display_data=DISPLAY_DATA,
        play_sounds=PLAY_SOUNDS,
        teleop=None,  # leave None to run policy-only evaluation
    )

    record(cfg)


if __name__ == "__main__":
    main()
