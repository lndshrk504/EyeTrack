---
name: deeplabcut-matlab-bridge
description: Use this skill when a task changes the EyeTrack Python/MATLAB boundary, including ZMQ payloads, matlab_zmq_bridge.py, run_matlab_eye_receive_test.py, receive_eye_stream_demo.m, run_eye_stream_receive_test.m, or MATLAB-visible eye-stream schema.
---

# DeepLabCut MATLAB bridge

## Goal

Avoid silent bugs at the Python/MATLAB boundary.

## Required workflow

1. Identify the boundary path.
   Name:
   - producer side
   - bridge helper
   - consumer side
   - transport or file format
   - validation entrypoints on both sides

2. Build a contract table before changing code.
   For each boundary object or field, list:
   - name
   - owner side
   - type or MATLAB class
   - units
   - indexing or coordinate-frame convention
   - whether it is dynamic sample data or static metadata
   - file or function carrying it

3. Preserve the current documented default contract unless the task explicitly changes it.
   Current MATLAB-consumed live fields are:
   - `frame_id`
   - `capture_time_unix_s`
   - `publish_time_unix_s`
   - `center_x`
   - `center_y`
   - `diameter_px`
   - `confidence_mean`
   - `latency_ms`

4. Prefer changing one side of the boundary at a time.
   If both sides must change, state why and describe the before/after contract.

5. Check the common failure modes explicitly.
   - missing or renamed JSON keys
   - sample vs metadata confusion
   - dtype or MATLAB class drift
   - units drift
   - coordinate-frame drift
   - indexing or shape changes

6. Choose the narrowest relevant validation.
   Typical checks:
   - CLI surface: `python3 DeepLabCut/ToMatlab/run_matlab_eye_receive_test.py --help`
   - live receive smoke with streamer running: `python3 DeepLabCut/ToMatlab/run_matlab_eye_receive_test.py --duration 10`
   - MATLAB-side receive path: `matlab -batch "cd('/Users/willsnyder/Desktop/EyeTrack'); run('DeepLabCut/ToMatlab/receive_eye_stream_demo.m');"`

7. In the handoff, report:
   - contract before and after
   - exact files changed on each side
   - validation commands
   - remaining compatibility risk

## Do not

- do not blindly transpose, squeeze, rename, or recast fields without proving the contract
- do not change sample-vs-metadata split silently
- do not change MATLAB-visible schema without calling it out explicitly
