from pathlib import Path
import argparse

from dlclive import DLCLive, Processor
import PySpin


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model-path",
        type=Path,
        default=None,
        help=(
            "Path to an exported DLCLive model. "
            "Defaults to the single directory under models/ or models/active/."
        ),
    )
    return parser.parse_args()


def default_model_path():
    repo_root = Path(__file__).resolve().parents[2]
    model_roots = [
        repo_root / "models" / "active",
        repo_root / "models",
    ]

    for model_root in model_roots:
        if not model_root.is_dir():
            continue

        child_dirs = sorted(path for path in model_root.iterdir() if path.is_dir())
        if len(child_dirs) == 1:
            return child_dirs[0]
        if child_dirs:
            raise FileNotFoundError(
                f"Found multiple candidate models under {model_root}. "
                "Pass --model-path to choose one."
            )

    raise FileNotFoundError(
        "Missing exported model. Copy a single model under models/<model-name> "
        "or models/active/<model-name>, or pass --model-path."
    )


args = parse_args()

dlc_proc = Processor()
# load exported DLC model
model_path = args.model_path or default_model_path()
dlc = DLCLive(
    str(model_path),
    processor=dlc_proc,
    display=True,
)

# initialize camera
system = PySpin.System.GetInstance()
cam = system.GetCameras()[0]
cam.Init()
cam.BeginAcquisition()

# get first frame
img = cam.GetNextImage().GetNDArray()

dlc.init_inference(img)

while True:
    img = cam.GetNextImage().GetNDArray()
    
    pose = dlc.get_pose(img)

    print(pose)
