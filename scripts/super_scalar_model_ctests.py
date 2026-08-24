import os
import sys
import time
import re
from const_def import *
from gh_tools import *
from gh_run_common import GhRunCommon
from mds_paras import ModelsParas


class SuperScalarModelCtests(GhRunCommon):
    def __init__(self):
        GhRunCommon.__init__(self)
        #
        self.workspace = None
        self.model_path = None
        self.build_path = None
        self.gcc_ctests_build_path = None
        self.clang_ctests_build_path = None
        #
        self.cpl_pcnt = None
        self.compile_mins = 20

    def init(self, in_args):
        ret = GhRunCommon.init(self, in_args)
        if ret != RET_OK:
            return ret
        self.workspace = self.gh_env.datas["workspace"]
        self.model_path = os.path.join(self.workspace, SUPER_SCALAR_MODEL_PATH_NAME)
        self.build_path = self.gh_env.datas["build_path"]
        self.gcc_ctests_build_path = os.path.join(self.build_path, GCC_CTESTS_BUILD_DIR)
        os.makedirs(self.gcc_ctests_build_path)
        self.clang_ctests_build_path = os.path.join(self.build_path, CLANG_CTESTS_BUILD_DIR)
        os.makedirs(self.clang_ctests_build_path)
        self.cpl_pcnt = self.parrel_cnt
        self.parrel_cnt = 1  # 共用源码，gcc&clang只能串行

        ret = self.init_datas()
        if ret != RET_OK:
            return ret
        return self.init_streams()

    def init_datas(self):
        self.datas = {
            "info": {
                "ver": 2,
                "root_path": self.model_path,
                "result": None,
                "start_time": None,
                "end_time": None,
                "run_time": None,
            },
            "gcc_ctests": {
                "result": None,
                "start_time": None,
                "end_time": None,
                "run_time": None,
                "dir": os.path.join(self.build_path, GCC_CTESTS_BUILD_DIR),
                "log": os.path.join(self.build_path, GCC_CTESTS_LOG),
            },
            "clang_ctests": {
                "result": None,
                "start_time": None,
                "end_time": None,
                "run_time": None,
                "dir": os.path.join(self.build_path, CLANG_CTESTS_BUILD_DIR),
                "log": os.path.join(self.build_path, CLANG_CTESTS_LOG),
            },
        }
        return RET_OK

    def init_streams(self):
        self.streams = dict()
        for one in self.datas.keys():
            if one == "info":
                continue

            self.streams[one] = {
                "cmd": self.get_cmd_str(one),
                'stdout': self.datas[one]["log"],
                'stderr': self.datas[one]["log"],
                "args": self.datas[one],
            }

        self.init_stream_run_datas()
        return RET_OK

    def get_cmd_str(self, stream_name):
        build_type = "release"
        cur_dir = self.datas[stream_name]["dir"]
        if "gcc" in stream_name:
            cxx = "g++"
            cc = "gcc"
        else:
            cxx = "clang++"
            cc = "clang"
        config_cmd = "cmake -B {} " \
                     "-DCMAKE_CXX_COMPILER={} " \
                     "-DCMAKE_C_COMPILER={} " \
                     "-DCMAKE_BUILD_TYPE={} " \
                     "-DBUILD_TESTS=ON " \
                     "-S {}".format(cur_dir, cxx, cc, build_type, self.model_path)
        compile_cmd = "cmake --build {} --config {} --parallel {}".format(cur_dir, build_type, self.cpl_pcnt)
        ct_cmd = "cd {} && ctest --build-config {} --output-on-failure" \
                 " -E 'vec_(pmu|pipeview|swimlane)|isa_test' -j {}".format(cur_dir, build_type, self.cpl_pcnt)
        scmd = "{} && {} && {}".format(config_cmd, compile_cmd, ct_cmd)
        return scmd

    def on_stream_begin(self, paras, stream_name):
        GhRunCommon.on_stream_begin(self, paras, stream_name)
        mylog.output(">>>>>>>{} start..., please wait... ...".format(stream_name))
        return RET_OK

    def on_stream_end(self, paras, stream_name, trd_run_ctl):
        # 执行目录较大，故每次跑完就删除
        scmd = "cd {} && rm -rf {} {}".format(self.build_path, GCC_CTESTS_BUILD_DIR, CLANG_CTESTS_BUILD_DIR)
        ToolFuncs.get_cmd_output(scmd)

        GhRunCommon.on_stream_end(self, paras, stream_name, trd_run_ctl)
        self.stream_run_datas2datas(stream_name)
        mylog.output("%s execution completed: %s" % (stream_name, RES_MAP_R[paras["result"]]))
        return
        

if __name__ == "__main__":
    env = GhEnv()
    ToolFuncs.init_env_for_debug()
    ret = env.init()
    if ret != RET_OK:
        print("GhEnv init failed.")
        sys.exit(1)

    rc_args = {
        "gTimeout": env.datas["g_timeout"],
    }
    run_ctl = RunCtl(rc_args)
    run_ctl.start_trd()

    ss_args = {
        "gh_env": env,
        "run_ctl": run_ctl,
        "parrel_cnt": env.datas["parrel_cnt"],  # 1,
        "run_one_mins": env.datas["s_timeout"],  # 20,
    }
    ssmc = SuperScalarModelCtests()
    ret = ssmc.init(ss_args)
    if ret != RET_OK:
        mylog.output("SuperScalarModelCtests init failed.")
        sys.exit(1)

    ssmc.run()
    ssmc.wait_run_over()
    ssmc.save_datas(SUPER_SCALAR_MODEL_CTESTS_JSON)
    print(ssmc.datas)
    print(ssmc.streams)
    
    run_ctl.end_trd()
    sys.exit(0)
