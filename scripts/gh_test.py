#！/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import signal
from const_def import *
from gh_tools import *
from mds_paras import ModelsParas
from super_scalar_model_ctests import SuperScalarModelCtests
from super_scalar_model_compile import SuperScalarModelCompile
from run_ssm_testcases import RunSsmTestcases


class GhTest:
    # 要跑的模型及各模型要跑的参数
    MODELS_PARAS = {
        "gfrun": {
            "": "nosoc"
        },
        "gfsim": {
            "-s core.simtEnable=true": "nosoc"
        }
    }

    def __init__(self):
        self.env = None
        self.mds_paras = None
        self.run_ctl = None
        self.ssmct = None
        self.ssmc = None
        self.rstc = None
        self.needs = None

    def init(self):
        # ToolFuncs.init_env_for_debug()  # --------for debug
        self.env = GhEnv()
        ret = self.env.init()
        if ret != RET_OK:
            return ret
    
        # mp_args = {
        #     "build_path": self.env.build_path,
        #     "cfg_file": self.env.datas["mrp_json"],
        # }
        # self.mds_paras = ModelsParas()
        # ret = self.mds_paras.init(mp_args)
        # if ret != RET_OK:
        #     return ret
        # 2台self-hosted的runner，无法集中配置，改为代码配置
        mp_args = {
            "build_path": self.env.build_path,
            "mds_paras": self.MODELS_PARAS,
        }
        self.mds_paras = ModelsParas()
        ret = self.mds_paras.init_lr(mp_args)
        if ret != RET_OK:
            return ret

        rc_args = {
            "gTimeout": self.env.datas["g_timeout"],
        }
        self.run_ctl = RunCtl(rc_args)
        self.run_ctl.start_trd()
        signal.signal(signal.SIGTERM, self.sig_terminate_handler)
        return RET_OK

    # 模型编译
    def model_compile(self):
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

        ret, self.needs = self.ssmc.need_test()
        if ret != RET_OK:
            return ret

        if not self.needs:
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
        return RET_OK

    def run_ctests(self):
        ss_args = {
            "gh_env": self.env,
            "run_ctl": self.run_ctl,
            "parrel_cnt": self.env.datas["parrel_cnt"],  # os.cpu_count()//2 - 1
            "run_one_mins": 20,
        }
        self.ssmct = SuperScalarModelCtests()
        ret = self.ssmct.init(ss_args)
        if ret != RET_OK:
            return ret

        self.ssmct.run()
        self.ssmct.wait_run_over()
        self.ssmct.save_datas(SUPER_SCALAR_MODEL_CTESTS_JSON)
        if self.ssmct.datas["info"]["result"] != EXE_PASS:
            # 把执行日志输出到github页面
            for one in self.ssmct.datas.keys():
                if one == "info":
                    continue

                if self.ssmct.datas[one]["result"] != EXE_PASS:
                    log = self.ssmct.datas[one]["log"]
                    if os.path.exists(log):
                        mylog.output("-" * 80)
                        mylog.output("{} Failed: ".format(one))
                        with open(log, "r") as f:
                            lines = f.readlines()
                            for one_line in lines:
                                mylog.output(one_line.strip())
                        mylog.output("-" * 80)
            return RET_ERR
        return RET_OK

    # 测例执行
    def run_testcases(self):
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

    def run(self):
        ret = self.model_compile()
        if ret != RET_OK:
            return ret
        
        if not self.needs:
            return RET_OK

        ctests_ret = self.run_ctests()
        tc_ret = self.run_testcases()
        if ctests_ret != RET_OK:
            return ctests_ret
        if tc_ret != RET_OK:
            return tc_ret
        return RET_OK

    def sig_terminate_handler(self, signum, frame):
            # github actions runner会多次下发
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            mylog.output("======>>>Get abort signal: %d" % signum)
            if self.run_ctl is not None:
                self.run_ctl.set_run_ctl(RUN_CTL_STOP)
            return


if __name__ == "__main__":
    gh_test = GhTest()
    ret = gh_test.init()
    if ret != RET_OK:
        sys.exit(ret)

    ret = gh_test.run()
    gh_test.run_ctl.end_trd()
    sys.exit(ret)
