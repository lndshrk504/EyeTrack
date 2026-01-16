% iRecHS2 + Psychtoolbox sample (MATLAB)
% Run on same machine: Server = 'localhost'
% Run on different machine: Server = 'xxx.xxx.xxx.xxx' (iRecHS2 IP)

Server = 'localhost';
magnify = 5;
circle_radius = 10;

try
    % Open window
    Screen('Preference', 'SkipSyncTests', 1);
    [win, winRect] = PsychImaging('OpenWindow', 0, 0);
    [xCenter, yCenter] = RectCenter(winRect);

    msg = 'Hit escape key to quit.';
    Screen('TextSize', win, 24);

    DrawFormattedText(win, 'Hit any key to start !', 'center', 'center', 255);
    Screen('Flip', win);
    KbWait;

    eye = iRecHS2(Server);
    if strcmp(eye.state(), 'connect')
        eye.start();
        while true
            [~, ~, keyCode] = KbCheck;
            if keyCode(KbName('ESCAPE'))
                break;
            end

            df = eye.get();
            if ~isempty(df)
                h = mean(df.h) * magnify;
                v = mean(df.v) * magnify;
                rect = [xCenter - circle_radius + h, ...
                        yCenter - circle_radius + v, ...
                        xCenter + circle_radius + h, ...
                        yCenter + circle_radius + v];
            else
                rect = [xCenter - circle_radius, ...
                        yCenter - circle_radius, ...
                        xCenter + circle_radius, ...
                        yCenter + circle_radius];
            end

            Screen('FillRect', win, 0);
            Screen('FillOval', win, 255, rect);
            DrawFormattedText(win, msg, 'center', 'center', 255);
            Screen('Flip', win);
        end
        eye.close();
    end
catch ME
    Screen('CloseAll');
    rethrow(ME);
end

Screen('CloseAll');
