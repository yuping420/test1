import os
import sys
import time
import threading
import subprocess
import signal
from copy import deepcopy
from const_def import *
from gh_tools import *


class GhRunBase:
    def __init__(self):
        self.gh_env = None
        self.run_ctl = None
        self.parrel_cnt = None
        self.run_one_mins = None
        # self.add_paras
        #
        self.run_trd = None
        self.datas = dict()
        self.streams = dict()
        self.stream_run_datas = dict()

    def init(self, in_args):
        self.gh_env = in_args["gh_env"]  # .datas
        self.run_ctl = in_args["run_ctl"]
        self.parrel_cnt = in_args["parrel_cnt"]
        self.run_one_mins = in_args["run_one_mins"]
        return RET_OK

    def init_datas(self):
        raise NotImplementedError("init_datas() is not implemented.")

    def init_streams(self):
        raise NotImplementedError("init_streams() is not implemented.")

    def init_stream_run_datas(self):
        run_datas = {
            "result": None,
            "start_time": None,
            "end_time": None,
            "run_time": None,
        }
        for stm in self.streams:
            self.stream_run_datas[stm] = deepcopy(run_datas)
            self.stream_run_datas[stm]["stdout"] = self.streams[stm]["stdout"]
            self.stream_run_datas[stm]["stderr"] = self.streams[stm]["stderr"]
        return

    # todo 应该不需要考虑trd_run_ctl
    def get_last_result(self, trd_run_ctl=None):
        lst_res = []
        for stm in self.stream_run_datas.keys():
            if stm == "datas":
                continue
            lst_res.append(self.stream_run_datas[stm]["result"])

        cnt = len(lst_res)
        if lst_res.count(EXE_PASS) == cnt:
            res = EXE_PASS
        elif EXE_FAIL in lst_res:
            res = EXE_FAIL
        elif EXE_ERROR in lst_res:
            res = EXE_ERROR
        elif EXE_STOP in lst_res:
            res = EXE_STOP
        elif EXE_GTIMEOUT in lst_res:
            res = EXE_GTIMEOUT
        elif EXE_STIMEOUT in lst_res:
            res = EXE_STIMEOUT
        elif None in lst_res:
            if trd_run_ctl == RUN_CTL_GTIMEOUT:
                res = EXE_GTIMEOUT
            elif trd_run_ctl == RUN_CTL_STIMEOUT:
                res = EXE_STIMEOUT
            elif trd_run_ctl == RUN_CTL_STOP:
                res = EXE_STOP
            elif trd_run_ctl == RUN_CTL_ERROR:
                res = EXE_ERROR
            else:
                if lst_res.count(None) == cnt:
                    res = None  # EXE_INIT
                else:
                    mylog.output("get_last_result() error, lst_res: %s, trd_run_ctl: %s" \
                    "" % (str(lst_res), RUN_CTL_MAP_R.get(trd_run_ctl, "unknown")))
                    res = EXE_ERROR
        else:
            mylog.output("get_last_result() error lst_res: %s" % str(lst_res))
            res = EXE_ERROR
        
        mylog.output("get_last_result: {}".format(RES_MAP_R.get(res, "unknown")))
        return res

    def run(self):
        self.run_trd = threading.Thread(target=self.run_dispatcher, args=(self.run_ctl, ))
        self.run_trd.start()

    def wait_run_over(self):
        if self.run_trd is None:
            return

        while True:
            if self.run_trd.is_alive() is False:
                self.run_trd.join()
                self.run_trd = None
                break
            time.sleep(0.05)
        return

    def run_dispatcher(self, run_ctl):
        mylog.output("run_dispatcher start... ...")
        ret = self.on_dispatcher_begin()
        if ret != RET_OK:
            self.on_dispatcher_end()
            mylog.output("run_dispatcher end... 1 ...")
            return

        stream_cnt = len(self.streams)
        if stream_cnt == 0:
            self.on_dispatcher_end()
            mylog.output("run_dispatcher end... 2 ...")
            return

        bg_time = time.time()
        prt_time = 0
        start_pos = 0
        get_no_running_time = 0
        dic_trds = dict()
        my_run_ctl = RUN_CTL_RUNNING
        while my_run_ctl == RUN_CTL_RUNNING:
            if start_pos >= stream_cnt:
                my_run_ctl = RUN_CTL_FINISH
                continue

            run_cnt = self.out_over(dic_trds)
            if run_cnt >= self.parrel_cnt:
                time.sleep(0.01)
            else:
                trd = threading.Thread(target=self.run_thread, args=(start_pos, run_ctl))
                trd.start()
                #
                dic_trds[start_pos] = trd
                start_pos = start_pos + 1

            # 每隔一段时间输出
            cur_time = int(time.time())
            if (cur_time % 30 == 0) and (cur_time != prt_time):
                self.on_dispatcher_timed_print()
                prt_time = cur_time

            # 更新全局控制
            my_run_ctl = run_ctl.get_run_ctl()
            if my_run_ctl != RUN_CTL_RUNNING:
                get_no_running_time = time.time()
                mylog.output("Dispatcher get NoRunning ctl: %s" \
                             "" % RUN_CTL_MAP_R.get(my_run_ctl, "unknown"))

        # 等待执行完成
        my_run_ctl = RUN_CTL_RUNNING
        while my_run_ctl == RUN_CTL_RUNNING:
            run_cnt = self.out_over(dic_trds)
            if run_cnt == 0:
                my_run_ctl = RUN_CTL_FINISH
                continue

            # 每隔一段时间输出
            cur_time = int(time.time())
            if (cur_time % 30 == 0) and (cur_time != prt_time):
                self.on_dispatcher_timed_print()
                prt_time = cur_time
            time.sleep(0.1)

        if get_no_running_time != 0:
            quit_time = int(time.time() - get_no_running_time)
            mylog.output("get no-running-ctl, quit_time = %ds" % quit_time)

        self.on_dispatcher_end()
        mylog.output("run_dispatcher end... 3 ...")
        return
        
    def out_over(self, trds):
        dels = []
        for mpos in trds.keys():
            if not trds[mpos].is_alive():
                trds[mpos].join()
                dels.append(mpos)

        for adel in dels:
            del trds[adel]

        return len(trds)

    def on_dispatcher_begin(self):
        return RET_OK

    def on_dispatcher_end(self):
        return

    def on_dispatcher_timed_print(self):
        return

    # github蓝区不考虑多机并发
    def run_thread(self, pos, run_ctl):
        stream_name = list(self.streams.keys())[pos]
        # mylog.output("stream: %s thread begin ... ..." % stream_name)

        start_time = time.time()
        exe_infos = {
            "start_time": start_time
        }
        ret = self.on_stream_begin(exe_infos, stream_name)
        if ret != RET_OK:
            self.on_stream_end(exe_infos, stream_name, None)
            # mylog.output("stream: %s thread end ... 1 ..." % stream_name)
            return
        
        ofile = self.streams[stream_name]["stdout"]
        efile = self.streams[stream_name]["stderr"]
        fo, eo = self.open_cmd_oef(ofile, efile)
        cur_cmd = self.streams[stream_name]["cmd"]
        proc = subprocess.Popen(cur_cmd, shell=True, stdout=fo, stderr=eo,
                                start_new_session=True , preexec_fn=self.subproc_preexec)
        exe_infos["proc"] = proc
        exe_infos["result"] = EXE_INIT
        exe_infos["ofile"] = ofile
        exe_infos["fo"] = fo
        exe_infos["efile"] = efile
        exe_infos["eo"] = eo
        self.on_stream_cmd_start_ok(exe_infos, stream_name)

        # 等待执行完成
        exit_flag = -1
        my_run_ctl = RUN_CTL_RUNNING
        while my_run_ctl == RUN_CTL_RUNNING:
            pret = proc.poll()
            if pret is not None:
                proc.wait()
                self.close_cmd_oef(fo, eo)
                if pret == 0:
                    exe_infos["result"] = EXE_PASS
                else:
                    exe_infos["result"] = EXE_FAIL

                exit_flag = 0  # 0表示正常跑完
                my_run_ctl = RUN_CTL_FINISH
                continue
            
            # 超时检查
            if self.run_one_mins > 0:
                run_time = int(time.time() - start_time)
                if run_time > (self.run_one_mins * 60):
                    exit_flag = 1
                    exe_infos["result"] = EXE_STIMEOUT
                    my_run_ctl = RUN_CTL_STIMEOUT
                    continue

            # 更新全局控制
            my_run_ctl = run_ctl.get_run_ctl()
            if my_run_ctl != RUN_CTL_RUNNING:
                # 此时只可能为stop
                exit_flag = 2
                exe_infos["result"] = EXE_STOP
                continue

            ret = self.on_stream_running(exe_infos, stream_name)
            if ret != RET_OK:
                # 执行监测发现异常，直接退出
                exit_flag = 3
                exe_infos["result"] = EXE_FAIL
                my_run_ctl = RUN_CTL_ERROR
                continue
            time.sleep(0.01)

        # kill处理
        if exit_flag > 0:
            out_msg = "Unkown, "
            if exit_flag == 1:
                out_msg = "Timeout, "
            elif exit_flag == 2:
                out_msg = "Stop, "
            elif exit_flag == 3:
                out_msg = "Running, "
            
            try:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(timeout=10)
                out_msg = out_msg + "Kill OK!"
            except Exception as ex:
                out_msg = out_msg + "kill exception: %s" % str(ex)
            
            self.close_cmd_oef(fo, eo)
            mylog.output("stream: %s %s" % (stream_name, out_msg))
        
        self.on_stream_end(exe_infos, stream_name, my_run_ctl)
        # mylog.output("stream: %s thread end ... 2 ..." % stream_name)
        return

    def on_stream_begin(self, paras, stream_name):
        return RET_OK

    def on_stream_cmd_start_ok(self, paras, stream_name):
        return

    def on_stream_running(self, paras, stream_name):
        return RET_OK

    def on_stream_end(self, paras, stream_name, trd_run_ctl):
        return

    # actions会先发SIGTERM，屏蔽之自己处理退出
    def subproc_preexec(self):
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        return

    def open_cmd_oef(self, ofile, efile):
        try:
            if ofile is None:
                # 将输出执行机stdout
                fo = None
            elif ofile == "/dev/null":
                fo = subprocess.DEVNULL
            else:
                fo = open(ofile, "a")  # w

            if efile == ofile:
                eo = fo
            else:
                if efile is None:
                    eo = None
                elif efile == "/dev/null":
                    eo = subprocess.DEVNULL
                else:
                    eo = open(efile, "a")
        except Exception as ex:
            mylog.output("open_cmd_feo exception: %s" % str(ex))
            fo = subprocess.DEVNULL
            eo = fo
        return fo, eo

    def close_cmd_oef(self, fo, eo, need_flush=True):
        if fo is None:
            pass
        elif fo == subprocess.DEVNULL:
            pass
        else:
            try:
                if need_flush:
                    fo.flush()
                fo.close()
            except (ValueError, OSError):
                pass

        if eo is fo:
            pass
        else:
            if eo is None:
                pass
            elif eo == subprocess.DEVNULL:
                pass
            else:
                try:
                    if need_flush:
                        eo.flush()
                    eo.close()
                except (ValueError, OSError):
                    pass
        return


if __name__ == "__main__":
    pass
