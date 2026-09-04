from pathlib import Path

from lerobot.scripts.lerobot_record import DatasetRecordConfig, RecordConfig, record

from S0101_hardware import CAMERA_FPS, build_follower_robot_config, build_leader_config


# -----------------------------
# User params
# -----------------------------
NUM_EPISODES = 10
FPS = CAMERA_FPS
EPISODE_TIME_SEC = 30
RESET_TIME_SEC = 4
TASK_DESCRIPTION = "Put the yellow ball in the white bowl"

REPO_ID = "Simo-a/S0101_test"

# Toggle this:
# - First time: RESUME = False  (creates dataset if needed)
# - Next sessions: RESUME = True (appends new episodes)
RESUME = True

# Optional: set a local dataset directory (keeps a stable local cache across runs)
# If you leave this as None, LeRobot will use its default location.
DATASET_ROOT = None  # e.g. Path("./lerobot_datasets")


# -----------------------------
# Robot + teleop configs
# -----------------------------
robot_config = build_follower_robot_config()
teleop_config = build_leader_config()

# -----------------------------
# Build record config and run
# -----------------------------
dataset_cfg = DatasetRecordConfig(
    repo_id=REPO_ID,
    single_task=TASK_DESCRIPTION,
    root=DATASET_ROOT,
    fps=FPS,
    episode_time_s=EPISODE_TIME_SEC,
    reset_time_s=RESET_TIME_SEC,
    num_episodes=NUM_EPISODES,
    video=True,
    push_to_hub=False,   # set False if you don't want to push every session
    private=False,
    tags=None,
    num_image_writer_processes=0,
    num_image_writer_threads_per_camera=4,
    video_encoding_batch_size=1,
)

cfg = RecordConfig(
    robot=robot_config,
    teleop=teleop_config,   # teleop-controlled recording
    policy=None,            # no policy
    dataset=dataset_cfg,
    display_data=True,
    play_sounds=True,
    resume=RESUME,
)

# record() handles:
# - dataset creation or resume
# - episodes + reset loops
# - saving episodes
# - video encoding
# - optional push_to_hub
record(cfg)
