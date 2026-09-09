import os
import sys
import re
from copy import deepcopy
from const_def import *
from gh_tools import *
from gh_run_common import GhRunCommon
from mds_paras import ModelsParas
from gh_testcases import GhTestcases
from md_log_parser import ModelLogParser


# 跑super_scalar_model仓里的testcase
class RunSsmTestcases(GhRunCommon):
    def __init__(self):
        GhRunCommon.__init__(self)
        #
        self.build_path = None
        self.model_compile_datas = None
        self.run_models = None
        self.models_paras_datas = None
        self.gtc = None

    def init(self, in_args):
        ret = GhRunCommon.init(self, in_args)
        if ret != RET_OK:
            return ret

        self.build_path = self.gh_env.build_path
        jfile = os.path.join(self.build_path, SUPER_SCALAR_MODEL_COMPILE_JSON)
        if not os.path.exists(jfile):
            mylog.output("ERROR: compile.json not exist!")
            return RET_ERR
        self.model_compile_datas = ToolFuncs.load_datas(jfile)

        mp = ModelsParas()
        ret = mp.init_from_json_of_build(self.build_path)
        if ret != RET_OK:
            return ret
        self.run_models = mp.get_run_model_names()
        self.models_paras_datas = mp.datas
        # print(self.models_paras_datas)

        self.gtc = GhTestcases()
        pass_args = {
            "gh_env": self.gh_env,
        }
        ret = self.gtc.init(pass_args)
        if ret != RET_OK:
            return ret

        ret = self.init_datas()
        if ret != RET_OK:
            return ret
        return self.init_streams()

    def init_datas(self):
        self.datas = {
            "info": {
                "ver": 1,
                "result": None,
                "start_time": None,
                "end_time": None,
                "run_time": None,
            },
        }
        case_run_datas = {
            "result": None,
            "start_time": None,
            "end_time": None,
            "run_time": None,
            "name": None,
            "log": None,
            "md": None,
            "orid": None,
            # "bm": None,
        }

        logpath = os.path.join(self.build_path, TESTCASE_LOG_DIR)
        os.makedirs(logpath)

        evt = self.gh_env.datas["event"]
        for md in self.run_models:
            cases = self.get_testcases(md, evt)
            if len(cases) == 0:
                mylog.output("WARNING: no testcases when: %s %s" % (md, evt))
                continue

            for one_case in cases:
                case_name = os.path.basename(one_case)
                case_relative_dir = os.path.dirname(one_case).replace(self.gh_env.code_path, "")
                case_log_path = os.path.join(logpath, case_relative_dir.strip("/"))
                if not os.path.exists(case_log_path):
                    os.makedirs(case_log_path)

                for paras_orid in self.models_paras_datas[md].keys():
                    paras_disp = self.models_paras_datas[md][paras_orid]
                    logfile = case_log_path + "/{}.{}.{}.log".format(case_name, md, paras_disp)
                    
                    case_run_datas["name"] = case_name
                    case_run_datas["log"] = logfile
                    case_run_datas["md"] = md
                    case_run_datas["orid"] = paras_orid

                    if one_case not in self.datas.keys():
                        self.datas[one_case] = {
                            md: {
                                paras_disp: deepcopy(case_run_datas)
                            }
                        }
                    elif md not in self.datas[one_case].keys():
                        self.datas[one_case][md] = {
                            paras_disp: deepcopy(case_run_datas)
                        }
                    elif paras_disp not in self.datas[one_case][md].keys():
                        self.datas[one_case][md][paras_disp] = deepcopy(case_run_datas)
                    else:
                        mylog.output("ERROR: RunSsmTestcases::init_datas!!!")
                        return RET_ERR
        # print(self.datas)
        return RET_OK

    def get_testcases(self, md, evt):
        return self.gtc.get_ssm_cases(md, evt)

    def init_streams(self):
        self.streams = dict()
        # name_prefix = "stream"
        stream_cnt = 0
        for one_case in self.datas.keys():
            if one_case == "info":
                continue

            for md in self.datas[one_case].keys():
                for paras_disp in self.datas[one_case][md].keys():
                    # stream_name = "{}{}".format(name_prefix, stream_cnt)
                    case_name = self.datas[one_case][md][paras_disp]["name"]
                    stream_name = "{}.{}.{}".format(case_name, md, paras_disp)
                    stream_cnt = stream_cnt + 1

                    paras_orid = self.datas[one_case][md][paras_disp]["orid"]
                    ret, cmd_str = self.get_cmd_str(one_case, md, paras_orid)
                    if ret != RET_OK:
                        return ret

                    logfile = self.datas[one_case][md][paras_disp]["log"]
                    self.streams[stream_name] = {
                        "cmd": cmd_str,
                        "stdout": logfile,
                        "stderr": logfile,
                        "args": self.datas[one_case][md][paras_disp],
                    }

        if stream_cnt == 0:
            mylog.output("ERROR: RunSsmTestcases::init_streams==0!!!")
            return RET_ERR
        
        self.sort_streams()
        self.init_stream_run_datas()
        return RET_OK

    def get_cmd_str(self, case, md, paras_orid):
        md_bin = self.get_model_bin_in_build(md)
        if md_bin is None:
            return RET_ERR, None

        md_dir = os.path.dirname(md_bin)
        md_name = os.path.basename(md_bin)
        case_name = os.path.basename(case)
        scmd = ""
        if case_name.startswith("kernel_multi"):
            if md_name == MODEL_MAP_R[GFRUN]:
                scmd = "cd {} && ./{} {} -s softcore.multiThreadNum=4 -f {}" \
                       "".format(md_dir, md_name, paras_orid, case)
            elif md_name == MODEL_MAP_R[GFSIM]:
                # add_paras = "--conf " + self.gh_env.code_path + "/configs/fourpe.conf"
                add_paras = "--conf " + self.model_compile_datas["info"]["root_path"] + "/configs/fourpe.conf"
                scmd = "cd {} && ./{} {} {} -f {}".format(md_dir, md_name, paras_orid, add_paras, case)

        if len(scmd) == 0:
            scmd = "cd {} && ./{} {} -f {}".format(md_dir, md_name, paras_orid, case)
        return RET_OK, scmd

    def get_model_bin_in_build(self, md):
        for one in self.model_compile_datas["bins_build"]:
            if os.path.basename(one) == md:
                return one

        mylog.output("ERROR: get_model_bin_in_build None!!!")
        return None

    def sort_streams(self):
        return RET_OK

    def on_dispatcher_begin(self):
        mylog.output(">>>>>>>RunTestcases begin..., please wait... ...")
        return GhRunCommon.on_dispatcher_begin(self)

    def on_dispatcher_end(self):
        GhRunCommon.on_dispatcher_end(self)

        # 生成统计数据
        summary = dict()
        for stm in self.streams.keys():
            md = self.streams[stm]["args"]["md"]
            orid = self.streams[stm]["args"]["orid"]
            disp = self.models_paras_datas[md][orid]
            res = self.streams[stm]["args"]["result"]

            if md not in summary.keys():
                summary[md] = dict()
            if disp not in summary[md].keys():
                summary[md][disp] = {
                    EXE_PASS: 0,
                    EXE_FAIL: 0,
                    EXE_TIMEOUT: 0,
                    EXE_INIT: 0,
                }

            if res == EXE_PASS:
                summary[md][disp][EXE_PASS] = summary[md][disp][EXE_PASS] + 1
            elif res in [EXE_FAIL, EXE_ERROR]:
                summary[md][disp][EXE_FAIL] = summary[md][disp][EXE_FAIL] + 1
            elif res in [EXE_GTIMEOUT, EXE_STIMEOUT, EXE_TIMEOUT]:
                summary[md][disp][EXE_TIMEOUT] = summary[md][disp][EXE_TIMEOUT] + 1
            else:
                summary[md][disp][EXE_INIT] = summary[md][disp][EXE_INIT] + 1
        self.datas["info"]["summary"] = summary
        return

    def on_stream_end(self, paras, stream_name, trd_run_ctl):
        res, infos = self.add_testcase_run_infos(paras, stream_name)
        # 在CI执行日志中写入信息
        md = self.streams[stream_name]["args"]["md"]
        if self.get_md_orid_name(md) == MODEL_MAP_R[GFRUN]:
            add_infos = "insts = {}".format(infos["inst_cnt"])
        elif self.get_md_orid_name(md) == MODEL_MAP_R[GFSIM]:
            add_infos = "cycles = {}".format(infos["cycle"])
        else:
            add_infos = None
        mylog.output("{}: {}({})".format(stream_name, RES_MAP_R[res], add_infos))

        GhRunCommon.on_stream_end(self, paras, stream_name, trd_run_ctl)
        self.stream_run_datas2datas(stream_name)
        return

    def add_testcase_run_infos(self, paras, stream_name):
        res = paras["result"]  # 退出码决定的结果
        logfile = self.get_logfile(stream_name)
        # 到日志文件中抓指定数据写入datas
        md = self.streams[stream_name]["args"]["md"]
        logfile = self.get_logfile(stream_name)
        log_parser = ModelLogParser(md, logfile)
        if self.get_md_orid_name(md) == MODEL_MAP_R[GFRUN]:
            infos = log_parser.get_gfrun_infos()
        elif self.get_md_orid_name(md) == MODEL_MAP_R[GFSIM]:
            infos = log_parser.get_gfsim_infos()
        else:
            infos = dict()

        self.streams[stream_name]["args"].update(infos)
        # 结果修正
        vals = list(infos.values())
        ncnt = vals.count(None)
        if ncnt > 0:
            if res == EXE_PASS:
                msg = "ERROR: get_xxx_infos fail: {}, change result to FAIL.".format(infos)
                ToolFuncs.out_log(logfile, msg)
                res = EXE_FAIL
                paras["result"] = EXE_FAIL
        else:
            # FAIL但数据全获取到了，也不改，因为退出码可能有问题
            pass
        return res, infos


if __name__ == "__main__":
    pass
