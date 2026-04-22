#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import deeplabcut
import yaml


DEFAULT_KEYPOINTS = [
    "Lpupil",
    "LDpupil",
    "Dpupil",
    "DRpupil",
    "Rpupil",
    "RVpupil",
    "Vpupil",
    "VLpupil",
]


def _as_str_path(path: Path) -> str:
    return str(path.resolve())


def cmd_init_project(args: argparse.Namespace) -> Path:
    videos = [str(Path(v).resolve()) for v in args.videos]
    if not videos:
        raise SystemExit("--videos is required for init-project")

    config_path = deeplabcut.create_new_project(
        project=args.project,
        experimenter=args.experimenter,
        videos=videos,
        copy_videos=args.copy_videos,
        multianimal=False,
        working_directory=str(args.working_directory.resolve()) if args.working_directory else None,
    )

    config = deeplabcut.auxiliaryfunctions.read_config(config_path)
    config["bodyparts"] = list(args.keypoints)
    if args.skeleton:
        config["skeleton"] = [pair.split(":", 1) for pair in args.skeleton]
    config["dotsize"] = int(args.dot_size)
    config["batch_size"] = int(args.batch_size)
    deeplabcut.auxiliaryfunctions.write_config(config_path, config)

    out = Path(config_path)
    print(f"[ok] created project config: {out}")
    return out


def cmd_extract_frames(args: argparse.Namespace) -> None:
    deeplabcut.extract_frames(
        config=_as_str_path(args.config),
        mode=args.frame_mode,
        algo=args.frame_algo,
        userfeedback=False,
    )
    print("[ok] frame extraction complete")


def cmd_create_dataset(args: argparse.Namespace) -> None:
    deeplabcut.create_training_dataset(
        config=_as_str_path(args.config),
        num_shuffles=int(args.shuffle_count),
        net_type=args.net_type,
        augmenter_type=args.augmenter,
    )
    print("[ok] training dataset created")


def cmd_train(args: argparse.Namespace) -> None:
    deeplabcut.train_network(
        config=_as_str_path(args.config),
        shuffle=int(args.shuffle),
        displayiters=int(args.displayiters),
        saveiters=int(args.saveiters),
        maxiters=int(args.maxiters),
        gputouse=int(args.gpu) if args.gpu is not None else None,
    )
    print("[ok] training complete")


def cmd_evaluate(args: argparse.Namespace) -> None:
    deeplabcut.evaluate_network(
        config=_as_str_path(args.config),
        shuffle=[int(args.shuffle)],
        plotting=bool(args.plotting),
    )
    print("[ok] evaluation complete")


def _read_pose_cfg(config: dict[str, Any], train_fraction: float, shuffle: int) -> Path:
    project_path = Path(config["project_path"])
    iteration = int(config.get("iteration", 0))
    trainset_pct = int(round(float(train_fraction) * 100))
    model_folder = (
        project_path
        / "dlc-models"
        / "iteration-{}".format(iteration)
        / f"{config['Task']}{config['date']}-trainset{trainset_pct}shuffle{shuffle}"
        / "train"
    )
    pose_cfg = model_folder / "pose_cfg.yaml"
    if not pose_cfg.exists():
        raise FileNotFoundError(f"Could not find pose_cfg.yaml at {pose_cfg}")
    return pose_cfg


def cmd_export(args: argparse.Namespace) -> None:
    deeplabcut.export_model(
        config=_as_str_path(args.config),
        shuffle=int(args.shuffle),
        trainingsetindex=int(args.trainingsetindex),
        snapshotindex=int(args.snapshotindex),
        TFGPUinference=bool(args.tf_gpu_inference),
        overwrite=bool(args.overwrite),
        make_tar=bool(args.make_tar),
    )

    config = deeplabcut.auxiliaryfunctions.read_config(_as_str_path(args.config))
    train_fraction = config["TrainingFraction"][int(args.trainingsetindex)]
    pose_cfg = _read_pose_cfg(config, float(train_fraction), int(args.shuffle))
    with pose_cfg.open("r", encoding="utf-8") as f:
        pose = yaml.safe_load(f)

    summary = {
        "config": _as_str_path(args.config),
        "shuffle": int(args.shuffle),
        "trainingsetindex": int(args.trainingsetindex),
        "snapshotindex": int(args.snapshotindex),
        "all_joints_names": pose.get("all_joints_names", []),
    }
    print("[ok] export complete")
    print(json.dumps(summary, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Train and export a TensorFlow DeepLabCut eye model for EyeTrack."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init-project", help="Create a new DLC project and set keypoints")
    p_init.add_argument("--project", required=True, help="Project/task name")
    p_init.add_argument("--experimenter", required=True, help="Experimenter name")
    p_init.add_argument(
        "--videos",
        nargs="+",
        default=[],
        help="One or more calibration/training videos from your real setup",
    )
    p_init.add_argument(
        "--working-directory",
        type=Path,
        default=None,
        help="Directory where the DLC project folder should be created",
    )
    p_init.add_argument("--copy-videos", action="store_true", help="Copy videos into project")
    p_init.add_argument("--keypoints", nargs="+", default=DEFAULT_KEYPOINTS)
    p_init.add_argument(
        "--skeleton",
        nargs="*",
        default=[],
        help="Optional skeleton edges, format: pointA:pointB",
    )
    p_init.add_argument("--dot-size", type=int, default=8)
    p_init.add_argument("--batch-size", type=int, default=8)
    p_init.set_defaults(func=cmd_init_project)

    p_extract = sub.add_parser("extract-frames", help="Extract frames to label")
    p_extract.add_argument("--config", type=Path, required=True)
    p_extract.add_argument("--frame-mode", choices=["automatic", "manual"], default="automatic")
    p_extract.add_argument("--frame-algo", choices=["kmeans", "uniform"], default="kmeans")
    p_extract.set_defaults(func=cmd_extract_frames)

    p_dataset = sub.add_parser("create-dataset", help="Create the DLC training dataset")
    p_dataset.add_argument("--config", type=Path, required=True)
    p_dataset.add_argument("--shuffle-count", type=int, default=1)
    p_dataset.add_argument("--net-type", default="resnet_50")
    p_dataset.add_argument("--augmenter", default="default")
    p_dataset.set_defaults(func=cmd_create_dataset)

    p_train = sub.add_parser("train", help="Train the DLC network")
    p_train.add_argument("--config", type=Path, required=True)
    p_train.add_argument("--shuffle", type=int, default=1)
    p_train.add_argument("--displayiters", type=int, default=100)
    p_train.add_argument("--saveiters", type=int, default=10000)
    p_train.add_argument("--maxiters", type=int, default=200000)
    p_train.add_argument("--gpu", type=int, default=None, help="GPU index (for TensorFlow)")
    p_train.set_defaults(func=cmd_train)

    p_eval = sub.add_parser("evaluate", help="Evaluate model performance")
    p_eval.add_argument("--config", type=Path, required=True)
    p_eval.add_argument("--shuffle", type=int, default=1)
    p_eval.add_argument("--plotting", action="store_true")
    p_eval.set_defaults(func=cmd_evaluate)

    p_export = sub.add_parser("export", help="Export model for DLCLive runtime")
    p_export.add_argument("--config", type=Path, required=True)
    p_export.add_argument("--shuffle", type=int, default=1)
    p_export.add_argument("--trainingsetindex", type=int, default=0)
    p_export.add_argument("--snapshotindex", type=int, default=-1)
    p_export.add_argument("--tf-gpu-inference", action="store_true")
    p_export.add_argument("--overwrite", action="store_true")
    p_export.add_argument("--make-tar", action="store_true")
    p_export.set_defaults(func=cmd_export)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
