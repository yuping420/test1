import os
import sys
import time
import threading
import json
import subprocess
import traceback
from const_def import *


class ToolFuncs:
    @staticmethod
    def get_cmd_output(cmd, expect_code=0, retry_times=3):
        ret_dic = {"ret_code": RET_OK, "stdout": None, "stderr": None}
        for i in range(retry_times):
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            ret_dic["stdout"] = res.stdout
            ret_dic["stderr"] = res.stderr
            
            if res.returncode == expect_code:
                ret_dic["ret_code"] = RET_OK
                return ret_dic

        ret_dic["ret_code"] = RET_ERR
        return ret_dic

    @staticmethod
    def get_folders_or_files(path_name, get_type="file"):
        if not os.path.exists(path_name):
            return []

        lst_ret = []
        lst = os.listdir(path_name)
        for one in lst:
            cur_file = os.path.join(path_name, one)
            if get_type == "file" and os.path.isfile(cur_file):
                lst_ret.append(cur_file)
            elif get_type == "bin":
                if os.access(cur_file, os.X_OK) and (not os.path.isdir(cur_file)):
                    lst_ret.append(cur_file)
            else:
                if os.path.isdir(cur_file):
                    lst_ret.append(cur_file)
        return lst_ret

    @staticmethod
    def save_datas(datas, path_file):
        with open(path_file, "w") as fh:
            jstr = json.dumps(datas, indent=4)
            fh.write(jstr)
            fh.flush()

    @staticmethod
    def load_datas(path_file, enc="utf-8"):
        with open(path_file, "r", encoding=enc) as fh:
            return json.load(fh)
        return None

    @staticmethod
    def out_log(logfile, content):
        with open(logfile, "a") as fh:
            fh.write(content + "\n")
            fh.flush()

    @staticmethod
    def summary_to_enhanced_table(data):
        # 准备表头
        headers = ["model.paras", "Pass", "Fail", "Timeout", "NoRun", "Pass Rate"]
        rows = []
        # 遍历数据
        for model_name, suites in data.items():
            for paras_name, results in suites.items():
                # 获取各状态计数，缺失默认为0
                pass_count = results.get(EXE_PASS, 0)  # "%d" % EXE_PASS
                fail_count = results.get(EXE_FAIL, 0)
                timeout_count = results.get(EXE_TIMEOUT, 0)
                norun_count = results.get(EXE_INIT, 0)
                total_executed = pass_count + fail_count + timeout_count + norun_count
                
                # 计算 Pass 率
                if total_executed > 0:
                    rate = (pass_count / total_executed) * 100
                    rate_str = f"{rate:.2f}%"
                else:
                    rate_str = "0.00%"
                
                # 构建行数据
                # 第一列合并 model 和 paras
                merged_col = f"{model_name}.{paras_name}"
                
                row = [
                    merged_col,
                    str(pass_count),
                    str(fail_count),
                    str(timeout_count),
                    str(norun_count),
                    rate_str
                ]
                rows.append(row)
                
        if not rows:
            return "ERROR: summary_to_enhanced_table: Empty Data"
        
        # 计算每列的最大宽度，以便对齐
        col_widths = [len(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                col_widths[i] = max(col_widths[i], len(cell))
                
        # 构建格式化字符串辅助函数
        def format_row(cells):
            return "| " + " | ".join(cell.ljust(width) for cell, width in zip(cells, col_widths)) + " |"
        
        # 生成分隔线
        separator = "+" + "+".join("-" * (width + 2) for width in col_widths) + "+"
        
        # 组装表格
        table_lines = []
        table_lines.append(separator)
        table_lines.append(format_row(headers))
        table_lines.append(separator)
        for row in rows:
            table_lines.append(format_row(row))
        table_lines.append(separator)
        return "\n".join(table_lines)

    @staticmethod
    def init_env_for_debug():
        os.environ["GITHUB_WORKSPACE"] = "/home/yuping/github_runner/testdir/SuperScalarModel"
        os.environ["GITHUB_RUN_NUMBER"] = "1"
        os.environ["GITHUB_EVENT_NAME"] = "push"  # "workflow_dispatch"
        os.environ["GITHUB_ACTOR"] = "somebody"
        os.environ["GITHUB_ACTOR_ID"] = "1"
        os.environ["GITHUB_REF_NAME"] = "main"
        os.environ["GITHUB_SHA"] = "abc123"
        os.environ["GITHUB_SHA_BEFORE"] = ""
        #
        os.environ["GITHUB_HEAD_REF"] = "feature-branch"
        os.environ["GITHUB_BASE_REF"] = "main"
        os.environ["GITHUB_HEAD_SHA"] = "def456"
        os.environ["GITHUB_BASE_SHA"] = "ghi789"
        #
        os.environ["MODELS_RUN_PARAS_JSON"] = "gh.json"
        os.environ["GLOB_TIMEOUT"] = "20"
        os.environ["SELF_TIMEOUT"] = "20"
        os.environ["PARREL_CNT"] = "5"
        return


class MyLogger:
    def __init__(self):
        self.fn = None
        self.fh = None
        self.fmt = "%Y-%m-%d %H:%M:%S| "
        self.lc = threading.Lock()

    def __del__(self):
        if self.fh:
            self.fh.flush()
            self.fh_close()

    def init(self, fn):
        self.fn = fn
        self.fh = open(fn, "w+")

    def output(self, msg, pr=True):
        msg = time.strftime(self.fmt, time.localtime()) + msg
        if pr:
            print(msg)
        self.lc.acquire()
        self.fh.write(msg + "\n")
        self.fh.flush()
        self.lc.release()

    def fh_flush(self):
        if self.fh:
            self.fh.flush()

    def fh_close(self):
        if self.fh:
            self.fh.flush()
            self.fh.close()
            self.fh = None
mylog = MyLogger()


class RunCtl:
    def __init__(self, in_args):
        self.gtimeout = in_args["gTimeout"] * 60  # minutes, 外部传入要确保正确
        self.run_ctl = RUN_CTL_RUNNING
        self.my_run = RUN_CTL_RUNNING
        self.trd = None
        self.RUN_LOCK = threading.Lock()

    def set_run_ctl(self, ctl):
        self.RUN_LOCK.acquire()
        self.run_ctl = ctl
        self.RUN_LOCK.release()

    def get_run_ctl(self):
        self.RUN_LOCK.acquire()
        ctl = self.run_ctl
        self.RUN_LOCK.release()
        return ctl

    def _run_ctl_thread(self):
        mylog.output("run_ctl thread start.")
        st_time = time.time()
        while self.my_run == RUN_CTL_RUNNING:
            if int(time.time() - st_time) > self.gtimeout:
                self.set_run_ctl(RUN_CTL_GTIMEOUT)
                self.my_run = RUN_CTL_FINISH  # RUN_CTL_GTIMEOUT

            time.sleep(0.2)
        mylog.output("run_ctl thread finish.")

    def start_trd(self):
        self.trd = threading.Thread(target=self._run_ctl_thread)
        self.trd.start()
        return

    def end_trd(self):
        self.my_run = RUN_CTL_FINISH
        if self.trd:
            self.trd.join()
            self.trd = None


class GhEnv:
    def __init__(self):
        self.code_path = None
        self.workspace_path = None
        self.build_path = None
        self.build_no = None
        self.datas = dict()

    def init(self):
        ghwk_path = os.environ.get("GITHUB_WORKSPACE", "unkown")
        if ghwk_path == "unkown":
            print("ERROR: GITHUB_WORKSPACE is not set, please check your environment.")
            return RET_ERR

        if not os.path.exists(ghwk_path):
            print("ERROR: GITHUB_WORKSPACE is not exist, please check: %s" % ghwk_path)
            return RET_ERR

        bno = os.environ.get("GITHUB_RUN_NUMBER", "unkown")
        if bno == "unkown":
            print("ERROR: GITHUB_RUN_NUMBER is not set, please check your environment.")
            return RET_ERR

        if not bno.isdigit():
            print("ERROR: GITHUB_RUN_NUMBER is not a number, please check your environment.")
            return RET_ERR

        self.code_path = ghwk_path
        self.workspace_path = os.path.dirname(ghwk_path)
        self.build_no = int(bno)
        self.build_path = os.path.join(self.workspace_path, "build_" + str(self.build_no))
        if not os.path.exists(self.build_path):
            os.makedirs(self.build_path)
            # 方便代码调试而改
            # print("build path is exist, please check: %s" % self.build_path)

        evt = os.environ.get("GITHUB_EVENT_NAME", "unkown")
        if evt not in ALL_EVENT_S:
            print("ERROR: event unkown, please check: %s" % evt)
            return RET_ERR

        logfile = os.path.join(self.build_path, LOG_FILE)
        mylog.init(logfile)

        self.datas["workspace"] = self.workspace_path
        self.datas["code_path"] = self.code_path
        self.datas["build_no"] = self.build_no
        self.datas["build_path"] = self.build_path
        self.datas["event"] = evt
        self.datas["actor"] = os.environ.get("GITHUB_ACTOR", "unkown")
        self.datas["actor_id"] = os.environ.get("GITHUB_ACTOR_ID", "unkown")
        # commit的
        self.datas["branch"] = os.environ.get("GITHUB_REF_NAME", "unkown")
        self.datas["commit_id"] = os.environ.get("GITHUB_SHA", "unkown")
        self.datas["before_commit_id"] = os.environ.get("GITHUB_SHA_BEFORE", "unkown")  # add
        # PR的
        self.datas["src_branch"] = os.environ.get("GITHUB_HEAD_REF", "unkown")
        self.datas["tgt_branch"] = os.environ.get("GITHUB_BASE_REF", "unkown")
        self.datas["src_commit_id"] = os.environ.get("GITHUB_HEAD_SHA", "unkown")
        self.datas["tgt_commit_id"] = os.environ.get("GITHUB_BASE_SHA", "unkown")
        # 其余参数也从env进
        self.datas["mrp_json"] = os.environ.get("MODELS_RUN_PARAS_JSON", "unkown")
        g_timeout = os.environ.get("GLOB_TIMEOUT", "unkown")
        s_timeout = os.environ.get("SELF_TIMEOUT", "unkown")
        parrel_cnt = os.environ.get("PARREL_CNT", "unkown")
        try:
            self.datas["g_timeout"] = int(g_timeout)
            self.datas["s_timeout"] = int(s_timeout)
            self.datas["parrel_cnt"] = int(parrel_cnt)
        except:
            print("ERROR: please check paras: %s" % str([g_timeout, s_timeout, parrel_cnt]))
            return RET_ERR
        return RET_OK

    def output(self):
        mylog.output("github env:")
        for one in self.datas:
            mylog.output("%s: %s" % (one, self.datas[one]))


if __name__ == "__main__":
    log_datas_json = "/home/yuping/github_runner/testdir/build_1/testcase_logs.json"
    data = ToolFuncs.load_datas(log_datas_json)
    print(ToolFuncs.summary_to_enhanced_table(data["info"]["summary"]))