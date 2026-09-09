#！/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import signal
import time
from const_def import *
from gh_tools import *
from mds_paras import ModelsParas
from super_scalar_model_compile import SuperScalarModelCompile
from run_ssm_testcases import RunSsmTestcases
from gh_test import GhTest


# 用于本地测试
class LocalTest(GhTest):
    # 本地可修改的执行配置
    LOCAL_EVENT = "local_run"  # 或 "workflow_dispatch"
    GLOB_TIMEOUT = 40  # 整体超时，单位：分钟
    SELF_TIMEOUT = 20  # 单个测例执行超时，单位：分钟
    PARREL_CNT = 12     # 执行并发量
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
        GhTest.__init__(self)

    def set_test_env(self):
        os.environ["GITHUB_WORKSPACE"] = os.path.dirname(os.path.dirname(__file__))
        os.environ["GITHUB_RUN_NUMBER"] = time.strftime("%Y%m%d%H%M%S", time.localtime(time.time()))
        os.environ["GITHUB_EVENT_NAME"] = self.LOCAL_EVENT
        os.environ["GLOB_TIMEOUT"] = str(self.GLOB_TIMEOUT)
        os.environ["SELF_TIMEOUT"] = str(self.SELF_TIMEOUT)
        os.environ["PARREL_CNT"] = str(self.PARREL_CNT)
        return

    def init(self):
        self.env = GhEnv()
        ret = self.env.init()
        if ret != RET_OK:
            return ret
    
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


if __name__ == "__main__":
    try:
        lc_test = LocalTest()
        lc_test.set_test_env()
        ret = lc_test.init()
        if ret != RET_OK:
            sys.exit(ret)

        ret = lc_test.run()
        lc_test.last_outputs()
        lc_test.run_ctl.end_trd()
        sys.exit(ret)
    except KeyboardInterrupt:
        mylog.output("WARNING: get ctrl-c... ...")
        if lc_test.run_ctl is not None:
            # 如果已经跑起来了，需要等他们正常退出
            lc_test.run_ctl.set_run_ctl(RUN_CTL_STOP)
            if lc_test.rstc is not None:
                lc_test.rstc.wait_run_over()
                lc_test.rstc.save_datas(TESTCASE_LOG_JSON)
                # sum_lines = ToolFuncs.summary_to_enhanced_table(lc_test.rstc.datas["info"]["summary"])
                # mylog.output("Summary: \n" + sum_lines)
            elif lc_test.ssmct is not None:
                lc_test.ssmct.wait_run_over()
                lc_test.ssmct.save_datas(SUPER_SCALAR_MODEL_CTESTS_JSON)
            elif lc_test.ssmc is not None:
                lc_test.ssmc.wait_run_over()
                lc_test.ssmc.save_datas(SUPER_SCALAR_MODEL_COMPILE_JSON)

            lc_test.last_outputs()
            lc_test.run_ctl.end_trd()
        sys.exit(EXE_STOP)
