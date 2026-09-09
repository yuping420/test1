import os
import sys
import re
from copy import deepcopy
from const_def import *
from gh_tools import *
from gh_run_common import GhRunCommon
from run_ssm_testcases import RunSsmTestcases
from mds_paras import ModelsParas


# 门禁性能对比功能
class RunSsmTestcasesPerfCompare(RunSsmTestcases):
    def __init__(self):
        RunSsmTestcases.__init__(self)
        #
        self.main_compile_datas = None

    def init(self, in_args):
        jfile = os.path.join(in_args["gh_env"].build_path, SUPER_SCALAR_MODEL_MAIN_COMPILE_JSON)
        if os.path.exists(jfile):
            self.main_compile_datas = ToolFuncs.load_datas(jfile)
        self.parrel_cnt = 1  # for debug
        return RunSsmTestcases.init(self, in_args)

    def get_testcases(self, md, evt):
        return self.gtc.get_ssm_cases(self.get_md_orid_name(md), evt)

    def get_cmd_str(self, case, md, paras_orid):
        md_bin = self.get_model_bin_in_build(md)
        if md_bin is None:
            return RET_ERR, None

        md_dir = os.path.dirname(md_bin)
        md_name = os.path.basename(md_bin)
        scmd = "cd {} && ./{} {} -f {}".format(md_dir, md_name, paras_orid, case)
        return RET_OK, scmd

    def get_model_bin_in_build(self, md):
        lst = self.model_compile_datas["bins_build"]
        if self.main_compile_datas is not None:
            lst = lst + self.main_compile_datas["bins_build"]
        for one in lst:
            if os.path.basename(one) == md:
                return one

        mylog.output("ERROR: get_model_bin_in_build:%s None!!!" % md)
        return None

    def on_dispatcher_end(self):
        RunSsmTestcases.on_dispatcher_end(self)
        # testcase failure logs
        sep_line = "-" * 100
        out_lines = []
        for stm in self.streams.keys():
            res = self.streams[stm]["args"]["result"]
            if res in [EXE_FAIL, EXE_ERROR]:
                out_lines.append(sep_line)
                log_file = self.streams[stm]["args"]["log"]
                out_lines.append(log_file + ":")
                with open(log_file, "r", errors="replace") as fh:
                    lines = fh.readlines()[-40:]
                    for one in lines:
                        one = one.strip()
                        out_lines.append(one)
        if len(out_lines) > 0:
            mylog.output("RunTestcases-failure logs: \n" + "\n".join(out_lines))
        return

    def on_stream_end(self, paras, stream_name, trd_run_ctl):
        res, infos = self.add_testcase_run_infos(paras, stream_name)
        # 仅在失败时在CI执行日志中写入信息
        # if res != EXE_PASS:
        #     md = self.streams[stream_name]["args"]["md"]
        #     if self.get_md_orid_name(md) == MODEL_MAP_R[GFRUN]:
        #         add_infos = "insts = {}".format(infos["inst_cnt"])
        #     elif self.get_md_orid_name(md) == MODEL_MAP_R[GFSIM]:
        #         add_infos = "cycles = {}".format(infos["cycle"])
        #     else:
        #         add_infos = None
        #     mylog.output("{}: {}({})".format(stream_name, RES_MAP_R[res], add_infos))

        GhRunCommon.on_stream_end(self, paras, stream_name, trd_run_ctl)
        self.stream_run_datas2datas(stream_name)
        return

    # 在保存完json后再调用。如果执行参数有变化，该函数要跟着改
    def gen_perf_table(self):
        del self.datas["info"]
        new_datas = {os.path.basename(k): v for k, v in self.datas.items()}
        new_datas = {k: v for k, v in sorted(new_datas.items())}
        rows = []
        for idx, (testcase_name, data) in enumerate(new_datas.items(), start=1):
            gfrun_inst = data.get("gfrun", {}).get("nosoc", {}).get("inst_cnt", 0)
            gfrun_inst = 0 if gfrun_inst is None else gfrun_inst  # 可能没跑导致本来就是None
            main_gfrun_inst = data.get("main_gfrun", {}).get("nosoc", {}).get("inst_cnt", 0)
            main_gfrun_inst = 0 if main_gfrun_inst is None else main_gfrun_inst
            inst_rate = (main_gfrun_inst - gfrun_inst) / main_gfrun_inst if main_gfrun_inst != 0 else 0.0
            inst_rate = inst_rate * 100

            gfsim_cycle = data.get("gfsim", {}).get("nosoc", {}).get("cycle", 0)
            gfsim_cycle = 0 if gfsim_cycle is None else gfsim_cycle
            main_gfsim_cycle = data.get("main_gfsim", {}).get("nosoc", {}).get("cycle", 0)
            main_gfsim_cycle = 0 if main_gfsim_cycle is None else main_gfsim_cycle
            cycle_rate = (main_gfsim_cycle - gfsim_cycle) / main_gfsim_cycle if main_gfsim_cycle != 0 else 0.0
            cycle_rate = cycle_rate * 100
            
            rows.append([
                idx,
                testcase_name,
                gfrun_inst,
                main_gfrun_inst,
                f"{inst_rate:.2f}",
                gfsim_cycle,
                main_gfsim_cycle,
                f"{cycle_rate:.2f}"
            ])

        # 计算平均行（无no列）
        avg_row = ["", "Average"]
        for col_idx in range(2, len(rows[0])):
            values = []
            for row in rows:
                val = row[col_idx]
                values.append(float(val) if isinstance(val, str) else val)
            avg = sum(values) / len(values)
            avg_row.append(f"{avg:.2f}")
        rows.append(avg_row)

        # 计算每列最大宽度
        headers = ["no", "testcase", "gfrun-inst_cnt", "main_gfrun-inst_cnt", "inst-rate",
                    "gfsim-cycle", "main_gfsim-cycle", "cycle-speedup"]
        col_widths = [len(h) for h in headers]
        for row in rows:
            for col_idx, val in enumerate(row):
                col_widths[col_idx] = max(col_widths[col_idx], len(str(val)))

        # 构建格式化字符串辅助函数
        def format_row(row):
            parts = [str(val).ljust(col_widths[col_idx]) for col_idx, val in enumerate(row)]
            return "| " + " | ".join(parts) + " |"
        
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


if __name__ == "__main__":
    env = GhEnv()
    ToolFuncs.init_env_for_debug()
    ret = env.init()
    if ret != RET_OK:
        print("GhEnv init failed.")
        sys.exit(1)
    env.build_path = "/home/yuping/github_runner/testdir/build_1_30"
    env.datas["build_path"] = env.build_path

    rc_args = {
        "gTimeout": env.datas["g_timeout"],
    }
    run_ctl = RunCtl(rc_args)
    run_ctl.start_trd()

    mp_args = {
        "build_path": env.build_path,
        "mds_paras": {
            "gfrun": {
                "": "nosoc"
            },
            "gfsim": {
                "-s core.simtEnable=true": "nosoc"
            },
            "main_gfrun": {
                "": "nosoc"
            },
            "main_gfsim": {
                "-s core.simtEnable=true": "nosoc"
            },
        },
    }
    mds_paras = ModelsParas()
    ret = mds_paras.init_lr(mp_args)
    if ret != RET_OK:
        mylog.output("ModelsParas init failed.")
        sys.exit(1)

    ss_args = {
        "gh_env": env,
        "run_ctl": run_ctl,
        "parrel_cnt": env.datas["parrel_cnt"],
        "run_one_mins": env.datas["s_timeout"],
    }
    sstc = RunSsmTestcasesPerfCompare()
    ret = sstc.init(ss_args)
    if ret != RET_OK:
        mylog.output("RunSsmTestcasesPerfCompare init failed.")
        sys.exit(1)
    
    sstc.run()
    sstc.wait_run_over()
    sstc.save_datas(TESTCASE_LOG_JSON)
    sum_lines = ToolFuncs.summary_to_enhanced_table(sstc.datas["info"]["summary"])
    mylog.output("RunTestcases-summary table: \n" + sum_lines)
    perf_tbl = sstc.gen_perf_table()
    mylog.output("RunTestcases-performance comparison details table: \n" + perf_tbl)
    run_ctl.end_trd()
    sys.exit(0)
    #
    # datas = ToolFuncs.load_datas("/home/yuping/github_runner/testdir/build_1_30/testcase_logs.json")
    # perf_tbl = gen_perf_table(datas)
    # mylog.output("RunTestcases-performance comparison details table: \n" + perf_tbl)
