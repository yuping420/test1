#！/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import signal
from const_def import *
from gh_tools import *
from mds_paras import ModelsParas
from super_scalar_model_compile import SuperScalarModelCompile
from run_ssm_testcases import RunSsmTestcases


class GhTest:
    def __init__(self):
        self.env = None
        self.mds_paras = None
        self.run_ctl = None
        self.ssmc = None
        self.rstc = None
    
    def sig_terminate_handler(self, signum, frame):
        # github actions runner会多次下发
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        mylog.output("======>>>Get abort signal: %d" % signum)
        # 要启动run_ctl后再截信号
        self.run_ctl.set_run_ctl(RUN_CTL_STOP)
        return

    def init(self):
        # ToolFuncs.init_env_for_debug()  # --------for debug
        self.env = GhEnv()
        ret = self.env.init()
        if ret != RET_OK:
            return ret
    
        mp_args = {
            "build_path": self.env.build_path,
            "cfg_file": self.env.datas["mrp_json"],
        }
        self.mds_paras = ModelsParas()
        ret = self.mds_paras.init(mp_args)
        if ret != RET_OK:
            return ret

        rc_args = {
            "gTimeout": self.env.datas["g_timeout"],
        }
        self.run_ctl = RunCtl(rc_args)
        self.run_ctl.start_trd()
        signal.signal(signal.SIGTERM, self.sig_terminate_handler)
        return RET_OK

    def run(self):
        # 模型编译
        ss_args = {
            "gh_env": self.env,
            "run_ctl": self.run_ctl,
            "parrel_cnt": self.env.datas["parrel_cnt"],  # os.cpu_count()//2 - 1
            "run_one_mins": 20,
        }
        self.ssmc = SuperScalarModelCompile()
        ret = self.ssmc.init(ss_args)
        if ret != RET_OK:
            return ret

        ret, needs = self.ssmc.need_test()
        if ret != RET_OK:
            return ret

        if not needs:
            return RET_OK

        self.ssmc.run()
        self.ssmc.wait_run_over()
        self.ssmc.save_datas(SUPER_SCALAR_MODEL_COMPILE_JSON)
        if self.ssmc.datas["info"]["result"] != EXE_PASS:
            mylog.output("Compile Failed: ")
            with open(self.ssmc.datas["info"]["log"], "r") as f:
                lines = f.readlines()
                for one_line in lines:
                    mylog.output(one_line.strip())
            return RET_ERR

        # 测例执行
        rs_args = {
            "gh_env": self.env,
            "run_ctl": self.run_ctl,
            "parrel_cnt": self.env.datas["parrel_cnt"],
            "run_one_mins": self.env.datas["s_timeout"],
        }
        self.rstc = RunSsmTestcases()
        ret = self.rstc.init(rs_args)
        if ret != RET_OK:
            return ret
        
        self.rstc.run()
        self.rstc.wait_run_over()
        self.rstc.save_datas(TESTCASE_LOG_JSON)
        sum_lines = ToolFuncs.summary_to_enhanced_table(self.rstc.datas["info"]["summary"])
        mylog.output("Summary: \n" + sum_lines)
        if self.rstc.datas["info"]["result"] != EXE_PASS:
            return RET_ERR
        return RET_OK


if __name__ == "__main__":
    gh_test = GhTest()
    ret = gh_test.init()
    if ret != RET_OK:
        sys.exit(ret)

    ret = gh_test.run()
    gh_test.run_ctl.end_trd()
    sys.exit(ret)
