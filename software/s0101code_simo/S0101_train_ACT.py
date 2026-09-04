from __future__ import annotations

import sys
from pathlib import Path

from lerobot.scripts.lerobot_train import train
from lerobot.configs.train import TrainPipelineConfig
from lerobot.configs.default import DatasetConfig, WandBConfig
from lerobot.datasets.transforms import ImageTransformsConfig
from lerobot.policies.act.configuration_act import ACTConfig


# -----------------------------
# User params (edit in your IDE)
# -----------------------------
DATASET_REPO_ID = "Simo-a/S0101_test"
DATASET_ROOT = None
DATASET_STREAMING = False

OUTPUT_DIR = Path("./outputs/train/act_so101_run2")

SEED = 42
STEPS = 100_000
BATCH_SIZE = 32
NUM_WORKERS = 4  # Windows needs __main__ guard when > 0

LOG_FREQ = 50
SAVE_FREQ = 2_000
SAVE_CHECKPOINT = True
EVAL_FREQ = 0

RESUME = False
RESUME_TRAIN_CONFIG_JSON = Path("./outputs/train/act_so101_run2/checkpoints/last/pretrained_model/train_config.json")

# ACT params
ACT_CHUNK_SIZE = 50
ACT_N_ACTION_STEPS = 10
ACT_USE_VAE = True
ACT_KL_WEIGHT = 10.0
ACT_TEMPORAL_ENSEMBLE_COEFF = None

ACT_OPT_LR = 1e-5
ACT_OPT_WD = 1e-4
ACT_OPT_LR_BACKBONE = 1e-5

PRETRAINED_POLICY_PATH = None

PUSH_TO_HUB = False
POLICY_REPO_ID = None


def main() -> None:

    if RESUME:
        # On Windows, symlink_to() fails if 'last/' already exists as an empty dir
        # (left behind by an interrupted run). Remove it so LeRobot can recreate it.
        last_dir = Path(__file__).parent / OUTPUT_DIR / "checkpoints" / "last"
        if last_dir.exists() and not last_dir.is_symlink() and not any(last_dir.iterdir()):
            last_dir.rmdir()

        # When resuming, load the full config (including optimizer/scheduler) from the
        # saved checkpoint. Building it manually would leave cfg.optimizer=None because
        # use_policy_training_preset is skipped when resume=True.
        config_path = Path(__file__).parent / RESUME_TRAIN_CONFIG_JSON
        sys.argv += [f"--config_path={config_path}"]
        cfg = TrainPipelineConfig.from_pretrained(str(config_path))
        cfg.resume = True
    else:
        dataset_cfg = DatasetConfig(
            repo_id=DATASET_REPO_ID,
            root=DATASET_ROOT,
            streaming=DATASET_STREAMING,
            image_transforms=ImageTransformsConfig(enable=True),
        )

        policy_cfg = ACTConfig(
            device="cuda",
            use_amp=True,
            pretrained_path=PRETRAINED_POLICY_PATH,
            push_to_hub=PUSH_TO_HUB,
            repo_id=POLICY_REPO_ID,

            chunk_size=ACT_CHUNK_SIZE,
            n_action_steps=ACT_N_ACTION_STEPS,
            use_vae=ACT_USE_VAE,
            kl_weight=ACT_KL_WEIGHT,
            temporal_ensemble_coeff=ACT_TEMPORAL_ENSEMBLE_COEFF,

            optimizer_lr=ACT_OPT_LR,
            optimizer_weight_decay=ACT_OPT_WD,
            optimizer_lr_backbone=ACT_OPT_LR_BACKBONE,
        )

        cfg = TrainPipelineConfig(
            dataset=dataset_cfg,
            env=None,
            policy=policy_cfg,

            output_dir=OUTPUT_DIR,
            resume=False,

            seed=SEED,
            num_workers=NUM_WORKERS,
            batch_size=BATCH_SIZE,
            steps=STEPS,

            eval_freq=EVAL_FREQ,
            log_freq=LOG_FREQ,
            save_checkpoint=SAVE_CHECKPOINT,
            save_freq=SAVE_FREQ,

            use_policy_training_preset=True,
            wandb=WandBConfig(enable=False),
        )

    train(cfg)


if __name__ == "__main__":
    # Optional on Windows; harmless otherwise.
    # from multiprocessing import freeze_support
    # freeze_support()
    main()
