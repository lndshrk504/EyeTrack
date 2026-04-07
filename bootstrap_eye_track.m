function addedPaths = bootstrap_eye_track()
% BOOTSTRAP_EYE_TRACK Add explicit MATLAB paths for the standalone EyeTrack repo.
% This keeps MATLAB path setup narrow and reproducible.

repoRoot = fileparts(mfilename("fullpath"));
activeBridgeDir = fullfile(repoRoot, "DeepLabCut", "ToMatlab");
if ~isfolder(activeBridgeDir)
    activeBridgeDir = fullfile(repoRoot, "EyeTrack", "ToMatlab");
end

candidatePaths = { ...
    activeBridgeDir, ...
    fullfile(repoRoot, "legacy", "iRecHS2", "scripts"), ...
    fullfile(repoRoot, "legacy", "iRecHS2", "iRecTests") ...
    };

currentPaths = string(strsplit(path, pathsep));
addedPaths = strings(0, 1);

for idx = 1:numel(candidatePaths)
    candidate = string(candidatePaths{idx});
    if isfolder(candidate) && ~any(strcmp(currentPaths, candidate))
        addpath(candidatePaths{idx});
        currentPaths(end + 1) = candidate; %#ok<AGROW>
        addedPaths(end + 1, 1) = candidate; %#ok<AGROW>
    end
end

if nargout == 0
    fprintf("bootstrap_eye_track added %d path(s).\n", numel(addedPaths));
    if ~isempty(addedPaths)
        disp(addedPaths);
    end
    clear addedPaths
end
end
