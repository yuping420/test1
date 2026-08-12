import os
import sys
import time
from const_def import *
from gh_tools import *


class ModelsParas:
    def __init__(self):
        self.build_path = None
        self.cfg_file = None
        self.cfg_ver = None
        self.datas = None

    # local_run时直接从参数传入
    def init_lr(self, in_args):
        self.build_path = in_args["build_path"]
        self.datas = in_args["mds_paras"]
        self.init_cfg_ver()
        ToolFuncs.save_datas(self.datas, os.path.join(self.build_path, MODELS_RUN_PARAS_JSON))
        return RET_OK

    # 从github触发的就配置文件化，以避免代码的修改
    def init(self, in_args):
        self.build_path = in_args["build_path"]
        self.cfg_file = in_args["cfg_file"]
        ret = self.init_datas()
        if ret != RET_OK:
            return ret
        
        self.init_cfg_ver()
        ToolFuncs.save_datas(self.datas, os.path.join(self.build_path, MODELS_RUN_PARAS_JSON))
        return RET_OK

    def init_datas(self):
        mp_file = os.path.join(MODELS_PARAS_ROOT, self.cfg_file)
        if not os.path.exists(mp_file):
            mylog.output("models_run_paras file not exist: %s" % mp_file)
            return RET_ERR

        self.datas = ToolFuncs.load_datas(mp_file)
        if self.datas is None:
            mylog.output("models_run_paras file load failed: %s" % mp_file)
            return RET_ERR
        return RET_OK

    def init_cfg_ver(self):
        ver = self.datas.get("version", None)
        if ver is None:
            self.cfg_ver = 1
        else:
            self.cfg_ver = int(ver)
        return

    # 和init一个层级
    def init_from_json_of_build(self, build_path):
        mp_file = os.path.join(build_path, MODELS_RUN_PARAS_JSON)
        if not os.path.exists(mp_file):
            mylog.output("models_run_paras file not exist: %s" % mp_file)
            return RET_ERR

        self.datas = ToolFuncs.load_datas(mp_file)
        if self.datas is None:
            mylog.output("models_run_paras file load failed: %s" % mp_file)
            return RET_ERR

        self.init_cfg_ver()
        return RET_OK

    def get_run_model_names(self):
        lst_ret = []
        if self.cfg_ver == 1:
            lst_ret = self.datas.keys()
        elif self.cfg_ver == 2:
            for pkg in self.datas.keys():
                if pkg == "version":
                    continue

                mds = []
                for md in self.datas[pkg].keys():
                    if md == "pkg_type":
                        continue
                    mds.append(md)
                lst_ret.extend(mds)

        lst_ret = list(set(lst_ret))
        return lst_ret


if __name__ == "__main__":
    print("=========================")
    pass_args = {
        "build_path": "/home/yuping/github_runner/_work/SuperScalarModel/build_1",
        "cfg_file": "gh.json",  # "pr.json", 这个多包配置的
    }
    mp = ModelsParas()
    print(mp.init(pass_args))
    # print(mp.init_lr(pass_args))
    print(mp.init_from_json_of_build(pass_args["build_path"]))
    print(mp.datas)
    print(mp.get_run_model_names())
    print(ALL_MODEL_S)