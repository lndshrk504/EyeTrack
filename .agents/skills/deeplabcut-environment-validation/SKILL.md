---
name: deeplabcut-environment-validation
description: Use this skill when a task changes or diagnoses the EyeTrack runtime environment, camera/backend validation scripts, dependency checks, environment.yaml, check_pyspin_camera.py, DeepLabCut/Tests/*, or SSH/X11 setup for the eye-tracking stack.
---

# DeepLabCut environment validation

## Goal

Diagnose environment and hardware issues without confusing missing dependencies, missing hardware, and real code regressions.

## Required workflow

1. Identify the failing or changed surface.
   Choose one or more of:
   - Python executable or environment selection
   - OpenCV / cv2
   - TensorFlow / DLCLive
   - PySpin camera access
   - GStreamer / Aravis / USB backend
   - MATLAB pyzmq bridge prerequisites
   - SSH/X11 forwarding or remote display

2. State the exact environment assumptions up front.
   Report:
   - Python executable used
   - required modules or hardware
   - OS and host context
   - whether the check is local, remote, or two-machine

3. Choose the narrowest relevant validation.
   Typical checks:
   - package inventory: `python3 DeepLabCut/Tests/VerCheck.py --strict`
   - TensorFlow build metadata: `python3 DeepLabCut/Tests/CheckReqs.py`
   - PySpin camera enumeration: `python3 DeepLabCut/ToMatlab/check_pyspin_camera.py`
   - FLIR smoke: `python3 DeepLabCut/Tests/TestSpin.py --camera-index 0 --sensor-roi 0 0 640 480 --frames 120`
   - OpenCV backend smoke: `python3 DeepLabCut/Tests/GSTOCV.py --backend usb --source 0 --width 640 --height 480 --fps 30 --frames 120`
   - FLIR preview: `python3 DeepLabCut/Tests/FLIRCam.py --camera-index 0 --frames 120`
   - FLIR + DLCLive timing: `python3 DeepLabCut/Tests/smoke_dlc_flir_inference.py --model-path <exported_model_dir> --model-preset yanglab-pupil8 --model-type base --camera-index 0 --sensor-roi 0 0 640 480 --frames 120`

4. Interpret failures conservatively.
   Separate:
   - missing module
   - missing hardware
   - permission or display issue
   - actual behavioral regression

5. For SSH/X11 or two-machine issues, identify where the failure occurs.
   Distinguish:
   - local environment problem
   - remote environment problem
   - camera-access problem
   - GUI forwarding problem

6. In the handoff, report:
   - exact command(s)
   - exact failure mode or success signal
   - what remains unverified
   - any hardware or environment dependency the user must provide

## Do not

- do not install packages or rewrite the environment unless explicitly asked
- do not claim a runtime regression when the failure is only a missing local dependency
- do not treat SSH/X11 display failures as camera or DLCLive failures without evidence
