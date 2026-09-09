import os
import sys
import time
import re
from const_def import *
from gh_tools import *
from gh_run_common import GhRunCommon
from mds_paras import ModelsParas
from super_scalar_model_compile import SuperScalarModelCompile


class SuperScalarModelMainCompile(SuperScalarModelCompile):
    def __init__(self):
        SuperScalarModelCompile.__init__(self)
        #
        self.need_run_main = False

    def init(self, in_args):
        ret = SuperScalarModelCompile.init(self, in_args)
        if ret != RET_OK:
            return ret

        self.need_run_main = self.get_need_run_main()
        if not self.need_run_main:
            mylog.output("need_run_main=False.")
            return RET_OK

        # main目录准备与clone。为了确保main是最新的，所以单独clone
        mylog.output("github_clone main start... ...")
        pre_time = time.time()
        get_dic = ToolFuncs.github_clone(SSM_GITHUB_HTTPS_URL, self.workspace,
                                         SUPER_SCALAR_MODEL_MAIN_PATH_NAME, "main")
        mylog.output("github_clone secs=%ds" % int(time.time() - pre_time))
        if get_dic["ret_code"] != RET_OK:
            mylog.output("ERROR: github_clone main: %s" % get_dic["stderr"])
            return RET_ERR
        self.model_path = os.path.join(self.workspace, SUPER_SCALAR_MODEL_MAIN_PATH_NAME)

        ret = self.init_datas()
        if ret != RET_OK:
            return ret
        return self.init_streams()

    def init_datas(self):
        SuperScalarModelCompile.init_datas(self)
        self.datas["info"]["log"] = os.path.join(self.build_path, SUPER_SCALAR_MODEL_MAIN_COMPILE_LOG)
        return RET_OK

    # 检查是否需要跑main分支，如果需要则要单独clone main并编译
    def get_need_run_main(self):
        for md in self.run_models:
            if md.startswith(NAME_RULE_MAIN):
                return True
        return False

    def on_dispatcher_begin(self):
        mylog.output(">>>>>>>SuperScalarModelCompile main begin..., please wait... ...")
        return GhRunCommon.on_dispatcher_begin(self)

    def on_dispatcher_end(self):
        GhRunCommon.on_dispatcher_end(self)
        #
        if self.datas["bins_build"] is None:
            return
        self.check_model_outs(NAME_RULE_MAIN)
        return

    def on_stream_end(self, paras, stream_name, trd_run_ctl):
        logfile = self.get_logfile(stream_name)
        err_msg = self.get_bins_zips(paras, stream_name, NAME_RULE_MAIN)
        if err_msg is not None:
            ToolFuncs.out_log(logfile, "ERROR:" + err_msg)
        #
        GhRunCommon.on_stream_end(self, paras, stream_name, trd_run_ctl)
        mylog.output("stream: %s(main) thread execution completed: %s" \
                     "" % (stream_name, RES_MAP_R[paras["result"]]))
        return


if __name__ == "__main__":
    pass
