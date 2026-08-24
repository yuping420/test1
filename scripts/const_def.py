#！/usr/bin/env python3
# -*- coding: utf-8 -*-


RET_OK = 0
RET_ERR = 111

EXE_INIT = 1
EXE_PASS = 10
EXE_FAIL = 20
EXE_ERROR = 21
EXE_TIMEOUT = 30
EXE_GTIMEOUT = 31
EXE_STIMEOUT = 32
EXE_STOP = 40  # 外部终止
RES_MAP = {
    "INIT": EXE_INIT,
    "PASS": EXE_PASS,
    "FAIL": EXE_FAIL,
    "ERROR": EXE_ERROR,
    "TIMEOUT": EXE_TIMEOUT,
    "GLOB_TIMEOUT": EXE_GTIMEOUT,
    "SELF_TIMEOUT": EXE_STIMEOUT,
    "STOP": EXE_STOP,
}
RES_MAP_R = {v: k for k, v in RES_MAP.items()}

RUN_CTL_RUNNING = 1
RUN_CTL_PAUSE = 2
RUN_CTL_STOP = 3
RUN_CTL_GTIMEOUT = 4
RUN_CTL_STIMEOUT = 5
RUN_CTL_ERROR = 6
RUN_CTL_FINISH = 7
RUN_CTL_MAP = {
    "RUNNING": RUN_CTL_RUNNING,
    "PAUSE": RUN_CTL_PAUSE,
    "STOP": RUN_CTL_STOP,
    "GLOB_TIMEOUT": RUN_CTL_GTIMEOUT,
    "SELF_TIMEOUT": RUN_CTL_STIMEOUT,
    "ERROR": RUN_CTL_ERROR,
    "FINISH": RUN_CTL_FINISH,
}
RUN_CTL_MAP_R = {v: k for k, v in RUN_CTL_MAP.items()}

GFRUN = 101
GFSIM = 103
# DV121_GFSIM = 103
MODEL_MAP = {
    "gfrun": GFRUN,
    "gfsim": GFSIM,
}
MODEL_MAP_R = {v: k for k, v in MODEL_MAP.items()}
ALL_MODEL = [GFRUN, GFSIM]
ALL_MODEL_S = [MODEL_MAP_R.get(model) for model in ALL_MODEL]

# github event
EVENT_PUSH = 220
EVENT_PULL_REQUEST = 230
EVENT_SCHEDULE = 240
EVENT_WORKFLOW_DISPATCH = 250
EVENT_LOCAL_RUN = 290  # 用户本地运行
EVENT_MAP = {
    "push": EVENT_PUSH,
    "pull_request": EVENT_PULL_REQUEST,
    "schedule": EVENT_SCHEDULE,
    "workflow_dispatch": EVENT_WORKFLOW_DISPATCH,
    "local_run": EVENT_LOCAL_RUN,
}
EVENT_MAP_R = {v: k for k, v in EVENT_MAP.items()}
ALL_EVENT = [
    EVENT_PUSH,
    EVENT_PULL_REQUEST,
    EVENT_SCHEDULE,
    EVENT_WORKFLOW_DISPATCH,
    EVENT_LOCAL_RUN,
]
ALL_EVENT_S = [EVENT_MAP_R.get(evt) for evt in ALL_EVENT]

# path, file, ...
LOG_FILE = "run.log"
# ACTIONS_ROOT = "/home/yuping/github_runner"
# FILES_ROOT = ACTIONS_ROOT + "/files_root"
# MODELS_PARAS_ROOT = FILES_ROOT + "/models_run_paras"
# TESTCASES_ROOT = FILES_ROOT + "/testcases"
# NPU_BENCH_ROOT = TESTCASES_ROOT + "/npu_bench"

MODELS_RUN_PARAS_JSON = "models_run_paras.json"
SUPER_SCALAR_MODEL_PATH_NAME = "SuperScalarModel"
# SUPER_SCALAR_MODEL_DV121_PATH_NAME = "SuperScalarModel_dv121"
SUPER_SCALAR_MODEL_COMPILE_JSON = "super_scalar_model_compile.json"
SUPER_SCALAR_MODEL_COMPILE_LOG = "super_scalar_model_compile.log"
SUPER_SCALAR_MODEL_BIN_BUILD_DIR = "super_scalar_model_models"
TESTCASE_LOG_DIR = "testcase_logs"
TESTCASE_LOG_JSON = "testcase_logs.json"

# ctests
SUPER_SCALAR_MODEL_CTESTS_JSON = "super_scalar_model_ctests.json"
GCC_CTESTS_BUILD_DIR = "gcc_ctests"
GCC_CTESTS_LOG = "gcc_ctests.log"
CLANG_CTESTS_BUILD_DIR = "clang_ctests"
CLANG_CTESTS_LOG = "clang_ctests.log"
