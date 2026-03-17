from dlclive import DLCLive, Processor
import PySpin
import argparse
import time
from collections import deque

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--crop-size",
        type=int,
        default=200,
        help="Square crop size (pixels) for inference input, default: 200",
    )
    parser.add_argument(
        "--display",
        action="store_true",
        help="Enable DLCLive display window",
    )
    return parser.parse_args()

args = parse_args()

DLCLIVE_DISPLAY = args.display
INFERENCE_SIZE = args.crop_size

dlc_proc = Processor()
# load exported DLC model
dlc = DLCLive("/home/wbs/DLC/DLC_PupilTracking_YangLab_resnet_50_iteration-0_shuffle-1",
        processor=dlc_proc, display=DLCLIVE_DISPLAY)


def crop_for_inference(frame, size):
    h, w = frame.shape[:2]
    if h < size or w < size:
        return frame
    y0 = (h - size) // 2
    x0 = (w - size) // 2
    return frame[y0:y0 + size, x0:x0 + size]

# initialize camera
system = PySpin.System.GetInstance()
cam = system.GetCameras()[0]
cam.Init()
cam.BeginAcquisition()

# get first frame
img = cam.GetNextImage()
img_data = img.GetNDArray()
img.Release()
img_data = crop_for_inference(img_data, INFERENCE_SIZE)

dlc.init_inference(img_data)

fps_window = deque(maxlen=120)

frame_counter = 0

while True:
    loop_start = time.perf_counter()

    acq_start = time.perf_counter()
    image = cam.GetNextImage()
    frame = image.GetNDArray()
    frame_time = time.perf_counter()
    image.Release()
    release_time = time.perf_counter()
    frame = crop_for_inference(frame, INFERENCE_SIZE)

    infer_start = time.perf_counter()
    pose = dlc.get_pose(frame)
    infer_end = time.perf_counter()

    loop_end = time.perf_counter()

    fps_window.append(loop_end)
    frame_counter += 1

    if len(fps_window) > 1:
        fps = (len(fps_window) - 1) / (fps_window[-1] - fps_window[0])
    else:
        fps = 0.0

    capture_ms = (frame_time - acq_start) * 1000.0
    release_ms = (release_time - frame_time) * 1000.0
    infer_ms = (infer_end - infer_start) * 1000.0
    total_ms = (loop_end - loop_start) * 1000.0
    overhead_ms = total_ms - (capture_ms + release_ms + infer_ms)

    if frame_counter % 20 == 0:
        print(f"[{frame_counter}] FPS: {fps:.2f}")
        print(
            f"capture: {capture_ms:6.2f} ms | "
            f"release: {release_ms:6.2f} ms | "
            f"inference: {infer_ms:6.2f} ms | "
            f"overhead: {overhead_ms:6.2f} ms | "
            f"total: {total_ms:6.2f} ms"
        )

    #print(f"[{frame_counter}] {pose}")
