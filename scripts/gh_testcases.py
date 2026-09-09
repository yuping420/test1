import os
import sys
import re
from const_def import *
from gh_tools import *


class GhTestcases:
    def __init__(self):
        self.gh_env = None
        self.code_path = None
        self.datas = None

    def init(self, in_args):
        self.gh_env = in_args["gh_env"]
        self.code_path = self.gh_env.datas["code_path"]
        return RET_OK

    # 跑包的方式，待后续根据需求实现
    def init_datas(self):
        return RET_OK

    # super_scalar_model仓，匹配当前策略：区分模型和event，从指定文件中读取
    def get_ssm_cases(self, md, evt):
        get_cases = []
        if md == MODEL_MAP_R[GFRUN]:
            if evt in [EVENT_MAP_R[EVENT_PUSH], EVENT_MAP_R[EVENT_PULL_REQUEST], 
                       EVENT_MAP_R[EVENT_LOCAL_RUN]]:
                case_list_file = self.code_path + "/tests/gfrun-pass-list.txt"
            else:  # if evt in [EVENT_MAP_R[EVENT_SCHEDULE], EVENT_MAP_R[EVENT_WORKFLOW_DISPATCH]]:
                case_list_file = self.code_path + "/tests/gfrun-pass-list-nightly.txt"
        elif md == MODEL_MAP_R[GFSIM]:
            if evt in [EVENT_MAP_R[EVENT_PUSH], EVENT_MAP_R[EVENT_PULL_REQUEST], 
                       EVENT_MAP_R[EVENT_LOCAL_RUN]]:
                case_list_file = self.code_path + "/tests/gfsim-pass-list.txt"
            else:  # if evt in [EVENT_MAP_R[EVENT_SCHEDULE], EVENT_MAP_R[EVENT_WORKFLOW_DISPATCH]]:
                case_list_file = self.code_path + "/tests/gfsim-pass-list-nightly.txt"
        else:
            case_list_file = None

        if case_list_file is None:
            mylog.output("ERROR: case_list_file is None: md={} evt={}".format(md, evt))
            return get_cases

        if not os.path.exists(case_list_file):
            mylog.output("ERROR: case_list_file not exists: {}".format(case_list_file))
            return get_cases
        
        with open(case_list_file, "r") as f:
            lines = f.readlines()
            for one in lines:
                lst = re.findall(r"(#.*)", one)
                if len(lst) > 0:
                    one = one.replace(lst[0], "")
                one = one.strip()
                if len(one) == 0:
                    continue

                # check exist
                case_file = os.path.join(self.code_path, one)
                if not os.path.exists(case_file):
                    continue
                get_cases.append(case_file)

        mylog.output("get_ssm_cases {} {} {}".format(md, evt, len(get_cases)))
        return get_cases

    def get_prebuilt_cases(self):
        cases_path = os.path.join(self.code_path, "tests/prebuilt-elf")
        scmd = "cd {} && find . -name '*.elf'".format(cases_path)
        ret_dic = ToolFuncs.get_cmd_output(scmd)
        if ret_dic["ret_code"] != RET_OK:
            mylog.output("ERROR: find prebuilt-elf stderr: {}".format(ret_dic["stderr"]))
            return RET_ERR, []

        outs = ret_dic["stdout"]
        if len(outs) == 0:
            mylog.output("ERROR: find prebuilt-elf stdout is empty!")
            return RET_ERR, []
        lines = outs.split("\n")
        cases = [os.path.join(cases_path, one) for one in lines if len(one) > 0]
        mylog.output("get_prebuilt_cases {}".format(len(cases)))
        return RET_OK, cases



if __name__ == "__main__":
    pass
