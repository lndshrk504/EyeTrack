function result = receive_eye_stream_demo(varargin)
% RECEIVE_EYE_STREAM_DEMO Current-standard alias for the MATLAB receive test.
%
% Start the Python streamer first, then run:
%   receive_eye_stream_demo()
%
% This delegates to run_eye_stream_receive_test, which uses BehaviorBoxEyeTrack
% and verifies that MATLAB receives the full point-column eye-tracking record.

result = run_eye_stream_receive_test(varargin{:});
end
