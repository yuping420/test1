import os
import sys
import time
import threading
import subprocess
import signal
from copy import deepcopy
from const_def import *
from gh_tools import *
from gh_run_base import GhRunBase


class GhRunCommon(GhRunBase):
    def __init__(self):
        GhRunBase.__init__(self)

    def load_datas(self, json_name):
        jfile = os.path.join(self.build_path, json_name)
        if not os.path.exists(jfile):
            mylog.output("ERROR: json not exists: %s" % jfile)
            return RET_ERR
        
        self.datas = ToolFuncs.load_datas(jfile)
        return RET_OK

    def save_datas(self, json_name):
        jfile = os.path.join(self.build_path, json_name)
        ToolFuncs.save_datas(self.datas, jfile)

    def get_logfile(self, stream_name):
        return self.streams[stream_name]["stdout"]

    def on_dispatcher_begin(self):
        self.datas["info"]["start_time"] = int(time.time())
        return RET_OK

    def on_dispatcher_end(self):
        current_time = int(time.time())
        self.datas["info"]["end_time"] = current_time
        self.datas["info"]["run_time"] = current_time - self.datas["info"]["start_time"]
        # 计算result
        self.datas["info"]["result"] = self.get_last_result()
        return

    def on_dispatcher_timed_print(self):
        lst_running = []
        lst_wait_rsrc = []
        lst_over = []
        for stm in self.streams.keys():
            if self.stream_run_datas[stm]["start_time"] is None:
                lst_wait_rsrc.append(stm)
            elif self.stream_run_datas[stm]["end_time"] is None:
                lst_running.append(stm)
            else:
                lst_over.append(stm)

        slog = "over: %s, wait_rsrc: %s, running: %s" % (len(lst_over), len(lst_wait_rsrc), len(lst_running))
        mylog.output(slog)
        return

    def on_stream_begin(self, paras, stream_name):
        logfile = self.get_logfile(stream_name)
        st_time = paras.get("start_time", int(time.time()))
        self.stream_run_datas[stream_name]["start_time"] = int(st_time)
        # 在执行日志中写入相关信息
        slog = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(st_time)) + ": EXE_begin"
        ToolFuncs.out_log(logfile, slog)
        ToolFuncs.out_log(logfile, "Command: " + self.streams[stream_name]["cmd"])
        return RET_OK

    def on_stream_end(self, paras, stream_name, trd_run_ctl):
        logfile = self.get_logfile(stream_name)
        end_time = int(time.time())
        run_time = end_time - self.stream_run_datas[stream_name]["start_time"]
        self.stream_run_datas[stream_name]["end_time"] = end_time
        self.stream_run_datas[stream_name]["run_time"] = run_time
        self.stream_run_datas[stream_name]["result"] = paras["result"]  # 退出码决定的结果
        # 在执行日志中写入相关信息
        slog = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time())) + ": "
        slog = slog + "EXE_end: {}, run_time: {} hours {} minutes {} seconds" \
                      "".format(RES_MAP_R[paras["result"]], 
                                int(run_time // 3600), int((run_time % 3600) // 60), 
                                int(run_time % 60))
        ToolFuncs.out_log(logfile, slog)
        return

    # 带args的流，将stream_run_datas的数据写入
    def stream_run_datas2datas(self, stream_name):
        if "args" not in self.streams[stream_name].keys():
            return
        
        st = self.stream_run_datas[stream_name]["start_time"]
        self.streams[stream_name]["args"]["start_time"] = st
        et = self.stream_run_datas[stream_name]["end_time"]
        self.streams[stream_name]["args"]["end_time"] = et
        rt = self.stream_run_datas[stream_name]["run_time"]
        self.streams[stream_name]["args"]["run_time"] = rt
        res = self.stream_run_datas[stream_name]["result"]
        self.streams[stream_name]["args"]["result"] = res
        return


if __name__ == "__main__":
    pass
