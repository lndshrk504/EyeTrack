function receive_eye_stream_demo()
% RECEIVE_EYE_STREAM_DEMO
% Example MATLAB subscriber for the Python dlc_eye_streamer ZeroMQ publisher.
%
% Edit pythonExe so MATLAB uses the same Python environment that contains:
%   - pyzmq
%   - matlab_zmq_bridge.py (same folder as this m-file, or on Python path)
%
% The Python streamer publishes compact eye metrics continuously over:
%   tcp://127.0.0.1:5555
%
% This demo receives only the latest message to avoid backlog.

address = "tcp://127.0.0.1:5555";
pythonExe = "/ABSOLUTE/PATH/TO/YOUR/ENV/bin/python";  % <-- EDIT THIS

thisDir = fileparts(mfilename("fullpath"));

pe = pyenv;
if pe.Status == "Loaded"
    if pe.Executable ~= string(pythonExe)
        error([ ...
            "MATLAB already loaded a different Python interpreter: " + pe.Executable + newline + ...
            "Restart MATLAB, or use terminate(pyenv) first if you are running OutOfProcess, then set pyenv again." ...
        ]);
    end
else
    pyenv(Version=pythonExe, ExecutionMode="OutOfProcess");
end

pyPath = string(cell(py.sys.path));
if ~any(pyPath == string(thisDir))
    py.sys.path.insert(int32(0), thisDir);
end

bridge = py.importlib.import_module("matlab_zmq_bridge");
py.importlib.reload(bridge);
sub = bridge.open_subscriber(address, int32(1));
cleaner = onCleanup(@() bridge.close_socket(sub)); %#ok<NASGU>

fprintf("Connected to %s\n", address);
fprintf("Waiting for eye stream... press Ctrl+C to stop.\n");

while true
    tup = bridge.recv_latest(sub, int32(50));

    frame_id = int64(tup{1});
    if frame_id < 0
        drawnow limitrate;
        continue;
    end

    eye.frame_id = frame_id;
    eye.capture_time_s = double(tup{2});
    eye.publish_time_s = double(tup{3});
    eye.x = double(tup{4});
    eye.y = double(tup{5});
    eye.diameter_px = double(tup{6});
    eye.confidence = double(tup{7});
    eye.latency_ms = double(tup{8});

    % Example: expose latest metrics to the base workspace for other code.
    assignin("base", "eye", eye);

    % Example: your experiment logic can run here.
    % if ~isnan(eye.diameter_px) && eye.diameter_px > 35
    %     disp("Pupil threshold crossed.");
    % end

    fprintf("frame=%d x=%.1f y=%.1f d=%.1f conf=%.3f latency=%.2f ms\n", ...
        eye.frame_id, eye.x, eye.y, eye.diameter_px, eye.confidence, eye.latency_ms);

    drawnow limitrate;
end
end
