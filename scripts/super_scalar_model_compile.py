import os
import sys
import time
import re
from const_def import *
from gh_tools import *
from gh_run_common import GhRunCommon
from mds_paras import ModelsParas


class SuperScalarModelCompile(GhRunCommon):
    def __init__(self):
        GhRunCommon.__init__(self)
        #
        self.workspace = None
        self.model_path = None
        self.build_path = None
        self.models_build_path = None
        # self.dv121_model_path = None
        self.run_models = None
        #
        self.compile_mins = 20

    def init(self, in_args):
        ret = GhRunCommon.init(self, in_args)
        if ret != RET_OK:
            return ret
        self.workspace = self.gh_env.datas["workspace"]
        self.model_path = os.path.join(self.workspace, SUPER_SCALAR_MODEL_PATH_NAME)
        self.build_path = self.gh_env.datas["build_path"]
        self.models_build_path = os.path.join(self.build_path, SUPER_SCALAR_MODEL_BIN_BUILD_DIR)
        os.makedirs(self.models_build_path)
        # dv121目录准备 todo

        mp = ModelsParas()
        ret = mp.init_from_json_of_build(self.build_path)
        if ret != RET_OK:
            return ret
        self.run_models = mp.get_run_model_names()

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
                "log": os.path.join(self.build_path, SUPER_SCALAR_MODEL_COMPILE_LOG),
            },
            "bins": None,
            "bins_build": None,
            # "bins_zip_build": None,
        }
        return RET_OK

    def init_streams(self):
        self.streams = dict()
        self.streams["model_compile"] = {
            "cmd": self.get_cmd_str(),
            'stdout': self.datas["info"]["log"],
            'stderr': self.datas["info"]["log"],
        }
        # if DV121_GFSIM in self.run_models:

        self.init_stream_run_datas()
        return RET_OK

    def get_cmd_str(self):
        scmd = "cd {} && python3 build.py all --clean -j {}".format(self.model_path, self.parrel_cnt)
        return scmd

    def need_test(self):
        evt = self.gh_env.datas["event"]
        if evt in ["schedule", "workflow_dispatch", "local_run"]:
            return RET_OK, True

        if evt == "push":
            bf = self.gh_env.datas["before_commit_id"]
            if (len(bf) == 0) or (bf == "0" * 40):
                mylog.output("Maybe new branch, run testcase!")
                return RET_OK, True

            base = bf
            head = self.gh_env.datas["commit_id"]
        elif evt == "pull_request":
            base = self.gh_env.datas["tgt_commit_id"]
            head = self.gh_env.datas["src_commit_id"]
        else:
            mylog.output("ERROR: unknown github event: %s" % evt)
            return RET_ERR, False

        scmd = "cd {} && git fetch --all && git diff --name-only {}...{}" \
               "".format(self.model_path, base, head)
        ret_dic = ToolFuncs.get_cmd_output(scmd)
        if ret_dic["ret_code"] != RET_OK:
            mylog.output("ERROR: git diff stderr:")
            mylog.output("stderr={}".format(ret_dic["stderr"]))
            return RET_ERR, False

        output = ret_dic["stdout"]
        lines = output.split("\n")
        mylog.output("git diff stdout:")
        for one in lines:
            mylog.output(one)

        chg_files = []
        diss_folders = ["docs/", "archSpec/", "modelSpec/"]
        for one in lines:
            if len(one) == 0:
                continue
            
            finds = re.findall(r'^({})'.format("|".join(diss_folders)), one)
            if len(finds) > 0:
                continue

            chg_files.append(one)

        if len(chg_files) == 0:
            mylog.output("Only doc change, skipping this test!")
            return RET_OK, False

        mylog.output("Source code changed:")
        for one in chg_files:
            mylog.output(one)
        return RET_OK, True

    def on_dispatcher_begin(self):
        mylog.output(">>>>>>>SuperScalarModelCompile begin..., please wait... ...")
        return GhRunCommon.on_dispatcher_begin(self)

    def on_dispatcher_end(self):
        GhRunCommon.on_dispatcher_end(self)

        if self.datas["bins_build"] is None:
            return

        # 检查要跑的model是不是都编出来且拷贝过来了
        names = []
        for one in self.datas["bins_build"]:
            names.append(os.path.basename(one))

        no_bins = []
        for one in self.run_models:
            if one not in names:
                no_bins.append(one)

        if len(no_bins) > 0:
            if self.datas["info"]["result"] == EXE_PASS:
                self.datas["info"]["result"] = EXE_FAIL
                msg = "ERROR: SuperScalarModelCompile::on_dispatcher_end no_bins={}," \
                    " change result to FAIL".format(no_bins)
                mylog.output(msg)
        return

    def on_stream_end(self, paras, stream_name, trd_run_ctl):
        logfile = self.get_logfile(stream_name)
        err_msg = self.get_bins_zips(paras, stream_name)
        if err_msg is not None:
            ToolFuncs.out_log(logfile, "ERROR:" + err_msg)
        #
        GhRunCommon.on_stream_end(self, paras, stream_name, trd_run_ctl)
        mylog.output("stream: %s thread execution completed: %s" \
                     "" % (stream_name, RES_MAP_R[paras["result"]]))
        return
        
    # zip从来没用过，故这里不再处理
    def get_bins_zips(self, paras, stream_name):
        msg = None
        stm_res = paras["result"]
        if stream_name == "model_compile":
            bin_path = os.path.join(self.model_path, "bin")
        # elif stream_name == "dv121_model_compile":
        #     bin_path = os.path.join(self.dv121_model_path, "bin")
        else:
            bin_path = os.path.join(self.model_path, "bin")
            mylog.output("ERROR: impossible-get_bins_zips!!!")

        # 获取目录下的可执行文件
        get_bins = ToolFuncs.get_folders_or_files(bin_path, "bin")
        if len(get_bins) == 0:
            if stm_res == EXE_PASS:
                msg = "stream: %s no bin found, but result is PASS, change to FAIL" % stream_name
                paras["result"] = EXE_FAIL
            return msg

        if self.datas["bins"] is None:
            self.datas["bins"] = get_bins
        else:
            self.datas["bins"].extend(get_bins)

        # 只拷贝本次要跑的bin到build_path
        for one in get_bins:
            bin_name = os.path.basename(one)
            if bin_name not in self.run_models:
                continue

            scmd = "cp -f {} {}".format(one, self.models_build_path)
            ret = os.system(scmd)
            if ret != 0:
                msg = "stream %s: bin copy failed. cmd: %s" % (stream_name, scmd)
                paras["result"] = EXE_FAIL
                return msg

            if self.datas["bins_build"] is None:
                self.datas["bins_build"] = [os.path.join(self.models_build_path, bin_name)]
            else:
                self.datas["bins_build"].append(os.path.join(self.models_build_path, bin_name))
        return msg


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

    mp_args = {
        "build_path": env.build_path,
        "cfg_file": env.datas["mrp_json"]  # "pr.json",
    }
    mds_paras = ModelsParas()
    ret = mds_paras.init(mp_args)
    if ret != RET_OK:
        mylog.output("ModelsParas init failed.")
        sys.exit(1)

    ss_args = {
        "gh_env": env,
        "run_ctl": run_ctl,
        "parrel_cnt": env.datas["parrel_cnt"],  # 1,
        "run_one_mins": env.datas["s_timeout"],  # 20,
    }
    ssmc = SuperScalarModelCompile()
    ret = ssmc.init(ss_args)
    if ret != RET_OK:
        mylog.output("SuperScalarModelCompile init failed.")
        sys.exit(1)

    # ssmc.run_dispatcher()
    ssmc.run()
    ssmc.wait_run_over()
    ssmc.save_datas(SUPER_SCALAR_MODEL_COMPILE_JSON)
    print(ssmc.datas)
    print(ssmc.streams)
    
    run_ctl.end_trd()
    sys.exit(0)
