function result = run_eye_stream_receive_test(options)
% RUN_EYE_STREAM_RECEIVE_TEST Verify MATLAB can receive the DLC eye stream.
%
% Start the Python streamer first, then run this from MATLAB or through
% run_matlab_eye_receive_test.py. The test uses BehaviorBoxEyeTrack, which is
% the same receiver class used by BehaviorBoxWheel.

arguments
    options.Address string = "tcp://127.0.0.1:5555"
    options.DurationSeconds double = 10
    options.MinSamples double = 5
    options.OutputMat string = ""
    options.PythonExecutable string = ""
    options.PollIntervalSeconds double = 0.05
end

thisDir = string(fileparts(mfilename("fullpath")));
deepLabCutDir = string(fileparts(thisDir));
eyeTrackDir = string(fileparts(deepLabCutDir));
behaviorBoxRoot = string(fileparts(eyeTrackDir));

addpath(char(behaviorBoxRoot));
startupFile = fullfile(behaviorBoxRoot, "startup.m");
if isfile(startupFile)
    run(startupFile);
end

if strlength(strtrim(options.PythonExecutable)) == 0
    options.PythonExecutable = string(getenv("BB_EYETRACK_PYTHON"));
end

if strlength(strtrim(options.OutputMat)) == 0
    stamp = string(datetime("now", "Format", "yyyyMMdd_HHmmss"));
    options.OutputMat = fullfile(tempdir, "eye_stream_matlab_receive_" + stamp + ".mat");
end

fprintf("MATLAB eye-stream receive test\n");
fprintf("Address: %s\n", options.Address);
fprintf("Duration: %.1f seconds\n", options.DurationSeconds);
fprintf("Output MAT: %s\n", options.OutputMat);
if strlength(strtrim(options.PythonExecutable)) > 0
    fprintf("Python for MATLAB bridge: %s\n", options.PythonExecutable);
else
    fprintf("Python for MATLAB bridge: auto-detect\n");
end

eyeTrackArgs = { ...
    'Address', options.Address, ...
    'SourceMode', "localhost", ...
    'BridgeDir', thisDir, ...
    'StartTimerOnStart', false, ...
    'WaitForReadySeconds', 2, ...
    'PollTimeoutMs', 50};
if strlength(strtrim(options.PythonExecutable)) > 0
    eyeTrackArgs = [eyeTrackArgs, {'PythonExecutable', options.PythonExecutable}];
end

eyeTrack = BehaviorBoxEyeTrack(eyeTrackArgs{:});
cleanupObj = onCleanup(@() cleanupEyeTrack_(eyeTrack));

eyeTrack.setSessionClock(tic, datetime("now"));
eyeTrack.markTrial(0);

if ~eyeTrack.start()
    error("run_eye_stream_receive_test:ConnectFailed", ...
        "BehaviorBoxEyeTrack could not open a subscriber: %s", eyeTrack.LastErrorMessage);
end

fprintf("Subscriber opened. Waiting for ready samples...\n");
nextProgress = tic;
testTimer = tic;
while toc(testTimer) < options.DurationSeconds
    eyeTrack.pollAvailable();
    if toc(nextProgress) >= 1
        printProgress_(eyeTrack);
        nextProgress = tic;
    end
    pause(options.PollIntervalSeconds);
end

eyeTrack.finalDrain();
record = eyeTrack.getRecord();
meta = eyeTrack.getMeta();
save(options.OutputMat, "record", "meta");

requiredColumns = ["Lpupil_x", "LDpupil_y", "Dpupil_likelihood", "RVpupil_x", "VLpupil_likelihood"];
recordColumns = string(record.Properties.VariableNames);
missingColumns = setdiff(requiredColumns, recordColumns);

result = struct();
result.ok = meta.IsReady && height(record) >= options.MinSamples && isempty(missingColumns);
result.sample_count = height(record);
result.is_ready = meta.IsReady;
result.output_mat = options.OutputMat;
result.missing_columns = missingColumns;
result.csv_path = meta.CsvPath;
result.metadata_path = meta.MetadataPath;
result.latest_sample_status = meta.LatestSampleStatus;

fprintf("\nReceive summary\n");
fprintf("Samples received by MATLAB: %d\n", height(record));
fprintf("Messages received by MATLAB: %d\n", meta.MessagesReceived);
fprintf("Metadata messages received: %d\n", meta.MetadataMessagesReceived);
fprintf("Ready: %d\n", meta.IsReady);
fprintf("Latest sample status: %s\n", meta.LatestSampleStatus);
fprintf("CSV path advertised by streamer: %s\n", meta.CsvPath);
fprintf("Metadata path advertised by streamer: %s\n", meta.MetadataPath);
fprintf("Saved MATLAB receive record: %s\n", options.OutputMat);
if height(record) > 0
    fprintf("First frame_id: %.0f\n", record.frame_id(1));
    fprintf("Last frame_id: %.0f\n", record.frame_id(end));
    fprintf("Latest center: x=%.1f y=%.1f confidence=%.3f valid_points=%.0f\n", ...
        record.center_x(end), record.center_y(end), ...
        record.confidence_mean(end), record.valid_points(end));
end

if ~isempty(missingColumns)
    fprintf("Missing required point columns: %s\n", strjoin(missingColumns, ", "));
end

if ~result.ok
    error("run_eye_stream_receive_test:ReceiveFailed", ...
        "MATLAB did not receive a ready eye stream with at least %.0f samples.", options.MinSamples);
end

fprintf("MATLAB_EYE_STREAM_RECEIVE_OK\n");
end

function printProgress_(eyeTrack)
record = eyeTrack.getRecord();
if height(record) == 0
    fprintf("samples=0 ready=%d\n", eyeTrack.IsReady);
    return
end
latest = record(end, :);
fprintf("samples=%d ready=%d frame=%.0f status=%s center=(%.1f, %.1f) confidence=%.3f\n", ...
    height(record), eyeTrack.IsReady, latest.frame_id, latest.sample_status, ...
    latest.center_x, latest.center_y, latest.confidence_mean);
end

function cleanupEyeTrack_(eyeTrack)
try
    if ~isempty(eyeTrack) && isvalid(eyeTrack)
        eyeTrack.stop();
    end
catch
end
end
