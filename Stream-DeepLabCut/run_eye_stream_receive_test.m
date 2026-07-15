function result = run_eye_stream_receive_test(options)
% RUN_EYE_STREAM_RECEIVE_TEST Verify MATLAB can import the deferred eye stream.
%
% Start the external eye receiver first, then run this from MATLAB or through
% run_matlab_eye_receive_test.py. The test uses BehaviorBoxEyeTrack, which is
% the same receiver client used by BehaviorBoxWheel.

arguments
    options.Address string = "tcp://127.0.0.1:5555"
    options.ReceiverUrl string = "http://127.0.0.1:8765"
    options.BehaviorBoxRoot string = ""
    options.DurationSeconds double = 10
    options.MinSamples double = 5
    options.MinValidSamples double = 1
    options.TransportOnly logical = false
    options.OutputMat string = ""
    options.PollIntervalSeconds double = 0.05
end

thisDir = string(fileparts(mfilename("fullpath")));
eyeTrackDir = string(fileparts(thisDir));
behaviorBoxRoot = strtrim(options.BehaviorBoxRoot);
if strlength(behaviorBoxRoot) == 0
    behaviorBoxRoot = string(fileparts(eyeTrackDir));
end
behaviorBoxClass = fullfile(behaviorBoxRoot, "BehaviorBoxEyeTrack.m");
if ~isfile(behaviorBoxClass)
    error("run_eye_stream_receive_test:BehaviorBoxRootNotFound", ...
        "BehaviorBoxRoot does not contain BehaviorBoxEyeTrack.m: %s", behaviorBoxRoot);
end
if options.MinSamples < 0 || options.MinValidSamples < 0
    error("run_eye_stream_receive_test:InvalidMinimum", ...
        "MinSamples and MinValidSamples must be nonnegative.");
end
if ~options.TransportOnly && options.MinValidSamples < 1
    error("run_eye_stream_receive_test:InvalidMinimum", ...
        "MinValidSamples must be at least 1 for the full receive test.");
end

addpath(char(behaviorBoxRoot), '-begin');
startupFile = fullfile(behaviorBoxRoot, "startup.m");
if isfile(startupFile)
    run(startupFile);
end

if strlength(strtrim(options.OutputMat)) == 0
    stamp = string(datetime("now", "Format", "yyyyMMdd_HHmmss"));
    options.OutputMat = fullfile(tempdir, "eye_stream_matlab_receive_" + stamp + ".mat");
end

fprintf("MATLAB eye-stream receive test\n");
fprintf("BehaviorBox root: %s\n", behaviorBoxRoot);
fprintf("Address: %s\n", options.Address);
fprintf("Receiver URL: %s\n", options.ReceiverUrl);
fprintf("Duration: %.1f seconds\n", options.DurationSeconds);
fprintf("Transport only: %d\n", options.TransportOnly);
fprintf("Output MAT: %s\n", options.OutputMat);

eyeTrackArgs = { ...
    'Address', options.Address, ...
    'ReceiverUrl', options.ReceiverUrl};

eyeTrack = BehaviorBoxEyeTrack(eyeTrackArgs{:});
cleanupObj = onCleanup(@() cleanupEyeTrack_(eyeTrack));

eyeTrack.setSessionClock(tic, datetime("now"));
eyeTrack.configureSession( ...
    "SessionId", "receive_test_session", ...
    "SessionKind", "receive_test", ...
    "SessionLabel", "receive-test", ...
    "OutputDir", fullfile(tempdir, "behaviorbox_receive_test_eye_raw"));

if ~eyeTrack.start()
    error("run_eye_stream_receive_test:ConnectFailed", ...
        "BehaviorBoxEyeTrack could not connect to the eye receiver: %s", eyeTrack.LastErrorMessage);
end

assert(eyeTrack.beginSegment("SegmentId", "receive_test_segment", "SegmentKind", "receive_test", ...
    "TrialNumber", 0, "Mode", "receive_test", "ScanImageFile", 1), ...
    'BehaviorBoxEyeTrack could not open the receive-test segment.');

fprintf("Receiver session opened. Waiting for finalized samples...\n");
nextProgress = tic;
testTimer = tic;
while toc(testTimer) < options.DurationSeconds
    if toc(nextProgress) >= 1
        printProgress_(eyeTrack);
        nextProgress = tic;
    end
    pause(options.PollIntervalSeconds);
end

eyeTrack.closeSegment();
eyeTrack.finalizeSession();
record = eyeTrack.getRecord();
meta = eyeTrack.getMeta();
save(options.OutputMat, "record", "meta");

requiredColumns = [ ...
    "is_valid", "sample_status", "center_x", "center_y", "valid_points", ...
    "Lpupil_x", "LDpupil_y", "Dpupil_likelihood", "RVpupil_x", "VLpupil_likelihood"];
recordColumns = string(record.Properties.VariableNames);
missingColumns = setdiff(requiredColumns, recordColumns);

persistedValid = false(height(record), 1);
derivedValid = false(height(record), 1);
if isempty(setdiff(["is_valid", "sample_status", "center_x", "center_y", "valid_points"], recordColumns))
    persistedValid = logical(record.is_valid);
    sampleStatus = lower(strtrim(string(record.sample_status)));
    derivedValid = ismember(sampleStatus, ["ok", "partial_points"]) & ...
        isfinite(double(record.center_x)) & isfinite(double(record.center_y)) & ...
        double(record.valid_points) > 0;
end
validRows = persistedValid & derivedValid;
validityMismatchRows = find(persistedValid ~= derivedValid);
transportOk = meta.IsReady && height(record) >= options.MinSamples && isempty(missingColumns);
fullOk = transportOk && sum(validRows) >= options.MinValidSamples && isempty(validityMismatchRows);

result = struct();
result.ok = fullOk;
if options.TransportOnly
    result.ok = transportOk;
end
result.transport_ok = transportOk;
result.full_ok = fullOk;
result.sample_count = height(record);
result.valid_sample_count = sum(validRows);
result.validity_consistent = isempty(validityMismatchRows);
result.validity_mismatch_rows = validityMismatchRows;
result.is_ready = meta.IsReady;
result.output_mat = options.OutputMat;
result.missing_columns = missingColumns;
result.csv_path = meta.CsvPath;
result.metadata_path = meta.MetadataPath;
result.streamer_csv_path = structStringField_(meta.StreamMetadata, "csv_path");
result.streamer_metadata_path = structStringField_(meta.StreamMetadata, "metadata_path");
result.latest_sample_status = meta.LatestSampleStatus;

fprintf("\nReceive summary\n");
fprintf("Samples received by MATLAB: %d\n", height(record));
fprintf("Messages received by MATLAB: %d\n", meta.MessagesReceived);
fprintf("Metadata messages received: %d\n", meta.MetadataMessagesReceived);
fprintf("Transport/sample ready: %d\n", meta.IsReady);
fprintf("Transport criteria passed: %d\n", transportOk);
fprintf("Valid samples received: %d\n", result.valid_sample_count);
fprintf("Validity fields internally consistent: %d\n", result.validity_consistent);
fprintf("Latest sample status: %s\n", meta.LatestSampleStatus);
fprintf("Configured source address: %s\n", meta.ConfiguredAddress);
fprintf("Receiver source address: %s\n", meta.ReceiverAddress);
fprintf("Effective source address: %s\n", meta.Address);
fprintf("Receiver chunk CSV path: %s\n", meta.CsvPath);
fprintf("Receiver chunk metadata path: %s\n", meta.MetadataPath);
fprintf("Streamer CSV path: %s\n", result.streamer_csv_path);
fprintf("Streamer metadata path: %s\n", result.streamer_metadata_path);
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
if ~isempty(validityMismatchRows)
    fprintf("Rows with inconsistent is_valid/status/center/valid_points fields: %s\n", ...
        strjoin(string(validityMismatchRows), ", "));
end

if options.TransportOnly && ~transportOk
    error("run_eye_stream_receive_test:TransportFailed", ...
        "MATLAB did not receive a ready eye stream with at least %.0f samples.", options.MinSamples);
elseif ~options.TransportOnly && ~fullOk
    error("run_eye_stream_receive_test:ReceiveFailed", ...
        ["MATLAB received %.0f samples and %.0f valid samples; the full smoke test requires " ...
        "at least %.0f samples and %.0f internally consistent valid samples."], ...
        height(record), result.valid_sample_count, options.MinSamples, options.MinValidSamples);
end

if options.TransportOnly
    fprintf("MATLAB_EYE_STREAM_TRANSPORT_OK\n");
else
    fprintf("MATLAB_EYE_STREAM_RECEIVE_OK\n");
end
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

function value = structStringField_(payload, fieldName)
value = "";
if ~isstruct(payload) || ~isfield(payload, fieldName)
    return
end
raw = payload.(char(fieldName));
if isempty(raw)
    return
end
value = string(raw);
value = value(1);
end
