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
from gh_test_perf_compare import GhTestPerfCompare


# 与main分支性能对比的本地测试
class LocalTestPerfCompare(GhTestPerfCompare):
    # 本地可修改的执行配置
    LOCAL_EVENT = "local_run"  # 或 "workflow_dispatch"
    GLOB_TIMEOUT = 40  # 整体超时，单位：分钟
    SELF_TIMEOUT = 20  # 单个测例执行超时，单位：分钟
    PARREL_CNT = 12    # 执行并发量
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
    # workflow_dispatch不跑main分支
    MODELS_PARAS_SCHEDULE = {
        "gfrun": {
            "": "nosoc",
        },
        "gfsim": {
            "-s core.soc_random=false": "nosoc",
        },
    }

    def __init__(self):
        GhTestPerfCompare.__init__(self)

    def set_test_env(self):
        os.environ["GITHUB_WORKSPACE"] = os.path.dirname(os.path.dirname(__file__))
        os.environ["GITHUB_RUN_NUMBER"] = time.strftime("%Y%m%d%H%M%S", time.localtime(time.time()))
        os.environ["GITHUB_EVENT_NAME"] = self.LOCAL_EVENT
        os.environ["GLOB_TIMEOUT"] = str(self.GLOB_TIMEOUT)
        os.environ["SELF_TIMEOUT"] = str(self.SELF_TIMEOUT)
        os.environ["PARREL_CNT"] = str(self.PARREL_CNT)
        return


if __name__ == "__main__":
    try:
        lc_test = LocalTestPerfCompare()
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
            elif lc_test.ssmct is not None:
                lc_test.ssmct.wait_run_over()
                lc_test.ssmct.save_datas(SUPER_SCALAR_MODEL_CTESTS_JSON)
            elif lc_test.ssmmc is not None:
                lc_test.ssmmc.wait_run_over()
                lc_test.ssmmc.save_datas(SUPER_SCALAR_MODEL_MAIN_COMPILE_JSON)
            elif lc_test.ssmc is not None:
                lc_test.ssmc.wait_run_over()
                lc_test.ssmc.save_datas(SUPER_SCALAR_MODEL_COMPILE_JSON)

            lc_test.last_outputs()
            lc_test.run_ctl.end_trd()
        sys.exit(EXE_STOP)
