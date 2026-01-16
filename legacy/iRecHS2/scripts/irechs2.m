classdef irechs2 < handle
    % iRecHS2 TCP client for the iRecHS2 eye tracker

    properties (Access = private)
        HOST
        PORT
        State = "disconnect"
        RemainStr = ""
        Client = []
    end

    methods
        function obj = irechs2(host, port)
            if nargin < 1 || isempty(host)
                host = "192.168.1.50";
            end
            if nargin < 2 || isempty(port)
                port = 35358;
            end
            obj.HOST = host;
            obj.PORT = port;
            obj.connect();
        end

        function s = state(obj)
            s = char(obj.State);
        end

        function connect(obj)
            if obj.State ~= "disconnect"
                return;
            end
            obj.Client = [];
            obj.State = "connect";
            try
                obj.Client = tcpclient(obj.HOST, obj.PORT, "Timeout", 5);
            catch ME
                if ~isempty(obj.Client)
                    try
                        clear obj.Client;
                    catch
                    end
                end
                obj.State = "disconnect";
                disp("timeout 5sec");
                disp(ME.message);
                disp(obj.HOST + ":" + string(obj.PORT));
            end
        end

        function send(obj, h, v, s, cl)
            if obj.State ~= "connect" && obj.State ~= "receive"
                return;
            end
            gp = sprintf("calibration\n%10.4f,%6.2f,%6.2f,%6.2f\n", cl, h, v, s);
            write(obj.Client, uint8(gp), "uint8");
        end

        function start(obj)
            if obj.State ~= "connect"
                return;
            end
            obj.State = "receive";
            write(obj.Client, uint8("start"), "uint8");
        end

        function start_plus(obj)
            if obj.State ~= "connect"
                return;
            end
            obj.State = "receive";
            write(obj.Client, uint8("start+"), "uint8");
        end

        function stop(obj, forceFlush)
            if nargin < 2
                forceFlush = true;
            end
            if obj.State ~= "receive"
                return;
            end
            obj.RemainStr = "";
            write(obj.Client, uint8("stop"), "uint8");
            if forceFlush
                pause(0.1);
                obj.get();
            end
            obj.State = "connect";
        end

        function close(obj)
            obj.stop();
            if obj.State == "connect"
                pause(0.1);
                if ~isempty(obj.Client)
                    clear obj.Client;
                    obj.Client = [];
                end
                obj.State = "disconnect";
            end
            obj.RemainStr = "";
        end

        function df = get(obj)
            df = table([], [], [], [], [], ...
                "VariableNames", {"time", "h", "v", "s", "openness"});
            if obj.State ~= "receive"
                return;
            end
            try
                if obj.Client.NumBytesAvailable == 0
                    return;
                end
                data = read(obj.Client, obj.Client.NumBytesAvailable, "uint8");
            catch
                obj.State = "disconnect";
                if ~isempty(obj.Client)
                    clear obj.Client;
                    obj.Client = [];
                end
                return;
            end

            if isempty(data)
                obj.State = "disconnect";
                if ~isempty(obj.Client)
                    clear obj.Client;
                    obj.Client = [];
                end
                return;
            end

            s = obj.RemainStr + string(char(data(:)'));
            parts = split(s, newline);
            if ~endsWith(s, newline)
                obj.RemainStr = parts(end);
                parts(end) = [];
            else
                obj.RemainStr = "";
            end

            if isempty(parts)
                return;
            end

            rows = [];
            for i = 1:numel(parts)
                line = parts(i);
                if count(line, ",") ~= 4
                    continue;
                end
                vals = sscanf(line, "%f,%f,%f,%f,%f");
                if numel(vals) == 5
                    rows = [rows; vals']; %#ok<AGROW>
                end
            end

            if ~isempty(rows)
                df = array2table(rows, "VariableNames", ...
                    {"time", "h", "v", "s", "openness"});
            end
        end
    end
end
