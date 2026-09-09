#！/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
from const_def import *
from gh_tools import *
from mds_paras import ModelsParas
from super_scalar_model_main_compile import SuperScalarModelMainCompile
from run_ssm_testcases_perf_compare import RunSsmTestcasesPerfCompare
from gh_test import GhTest


# 与main分支进行性能对比的自动化测试类
class GhTestPerfCompare(GhTest):
    # 要跑的模型及各模型要跑的参数
    MODELS_PARAS = {
        "gfrun": {
            "": "nosoc",
        },
        "gfsim": {
            "-s core.simtEnable=true": "nosoc",
        },
        "main_gfrun": {
            "": "nosoc",
        },
        "main_gfsim": {
            "-s core.simtEnable=true": "nosoc",
        },
    }
    # schedule和dispatch不需要跑main分支
    MODELS_PARAS_SCHEDULE = {
        "gfrun": {
            "": "nosoc",
        },
        "gfsim": {
            "-s core.simtEnable=true": "nosoc",
        },
    }

    def __init__(self):
        GhTest.__init__(self)
        #
        self.ssmmc = None

    def init(self):
        ret = GhTest.init(self)
        if ret != RET_OK:
            return ret

        # 要根据任务类型处理，故要重新解析要跑的模型及参数
        mp_args = {
            "build_path": self.env.build_path,
            "mds_paras": self.MODELS_PARAS,
        }
        if self.env.datas["event"] in [EVENT_MAP_R[EVENT_SCHEDULE], EVENT_MAP_R[EVENT_WORKFLOW_DISPATCH]]:
            mp_args["mds_paras"] = self.MODELS_PARAS_SCHEDULE
        self.mds_paras = ModelsParas()
        ret = self.mds_paras.init_lr(mp_args)
        if ret != RET_OK:
            return ret
        return RET_OK

    # 性能对比增加main分支编译
    def main_model_compile(self):
        ss_args = {
            "gh_env": self.env,
            "run_ctl": self.run_ctl,
            "parrel_cnt": self.env.datas["parrel_cnt"],
            "run_one_mins": 20,
        }
        self.ssmmc = SuperScalarModelMainCompile()
        ret = self.ssmmc.init(ss_args)
        if ret != RET_OK:
            return ret

        if not self.ssmmc.need_run_main:
            return RET_OK

        self.ssmmc.run()
        self.ssmmc.wait_run_over()
        self.ssmmc.save_datas(SUPER_SCALAR_MODEL_MAIN_COMPILE_JSON)
        if self.ssmmc.datas["info"]["result"] != EXE_PASS:
            mylog.output("Main Compile Failed: ")
            with open(self.ssmmc.datas["info"]["log"], "r") as f:
                lines = f.readlines()
                for one_line in lines:
                    mylog.output(one_line.strip())
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
        self.rstc = RunSsmTestcasesPerfCompare()
        ret = self.rstc.init(rs_args)
        if ret != RET_OK:
            return ret
        
        self.rstc.run()
        self.rstc.wait_run_over()
        self.rstc.save_datas(TESTCASE_LOG_JSON)
        if self.rstc.datas["info"]["result"] != EXE_PASS:
            return RET_ERR
        return RET_OK

    def run(self):
        ret = self.model_compile()
        if ret != RET_OK:
            return ret
        
        if not self.needs:
            return RET_OK

        ret = self.main_model_compile()
        if ret != RET_OK:
            return ret

        ctests_ret = self.run_ctests()
        tc_ret = self.run_testcases()
        if ctests_ret != RET_OK:
            return ctests_ret
        if tc_ret != RET_OK:
            return tc_ret
        return RET_OK

    # 最后汇总输出，方便用户统一查看结果
    def last_outputs(self):
        if self.ssmc is None:
            return
        if not self.ssmc.need_test:
            return

        split_line_len = 90
        mylog.output("-" * split_line_len)
        mylog.output("-" * split_line_len)
        if self.ssmc.datas["info"]["result"] != EXE_PASS:
            mylog.output("Compile Result: %s" % RES_MAP_R[self.ssmc.datas["info"]["result"]])
            return
        mylog.output("Compile Result: PASS")

        if self.ssmmc is not None:
            if self.ssmmc.need_run_main:
                if self.ssmmc.datas["info"]["result"] != EXE_PASS:
                    if self.ssmmc.datas["info"]["result"] is None:
                        mylog.output("Compile(main) Result: None")
                    else:
                        mylog.output("Compile(main) Result: %s" % RES_MAP_R[self.ssmmc.datas["info"]["result"]])
                    return
                mylog.output("Compile(main) Result: PASS")

        if self.ssmct is not None:
            if self.ssmct.datas["gcc_ctests"]["result"] is not None:
                mylog.output("ctests(GCC) Result: %s" % RES_MAP_R[self.ssmct.datas["gcc_ctests"]["result"]])
            if self.ssmct.datas["clang_ctests"]["result"] is not None:
                mylog.output("ctests(CLANG) Result: %s" % RES_MAP_R[self.ssmct.datas["clang_ctests"]["result"]])

        if self.rstc is not None:
            mylog.output("RunTestcases Result: %s" % RES_MAP_R[self.rstc.datas["info"]["result"]])
            sum_lines = ToolFuncs.summary_to_enhanced_table(self.rstc.datas["info"]["summary"])
            mylog.output("RunTestcases: summary table: \n" + sum_lines)
            #
            if self.ssmmc is not None:
                if self.ssmmc.need_run_main:
                    perf_tbl = self.rstc.gen_perf_table()
                    mylog.output("RunTestcases: performance comparison details table: \n" + perf_tbl)
        return


if __name__ == "__main__":
    # ToolFuncs.init_env_for_debug()  # --------for debug
    gtpc = GhTestPerfCompare()
    ret = gtpc.init()
    if ret != RET_OK:
        sys.exit(ret)

    ret = gtpc.run()
    gtpc.last_outputs()
    gtpc.run_ctl.end_trd()
    sys.exit(ret)
