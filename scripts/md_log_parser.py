#！/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import re
from const_def import *


class ModelLogParser:
    def __init__(self, md, logfile):
        self.md = md
        self.logfile = logfile
        self.lines = []
        if self.logfile is None:
            pass
        elif os.path.exists(self.logfile):
            fh = open(self.logfile, "r")
            self.lines = fh.readlines()
            fh.close()

    def get_gfrun_infos(self):
        infos = {"block_cnt": None, "inst_cnt": None}
        for one in self.lines:
            lst = re.findall(r"^Total Block number\s*=\s*(\d+)", one)
            if len(lst) == 1:
                infos["block_cnt"] = int(lst[0])

            lst = re.findall(r"^Total Inst number\s*=\s*(\d+)", one)
            if len(lst) == 1:
                infos["inst_cnt"] = int(lst[0])
        return infos

    def get_gfsim_infos(self):
        infos = {"cycle": None, "ipc": None}
        for one in self.lines:
            lst = re.findall(r"^Total Cycles\s*\.*\s*:\s*(\d+)", one)
            if len(lst) == 1:
                infos["cycle"] = int(lst[0])

            lst = re.findall(r"^IPC\s*\.*\s*:\s*(\d+\.\d+)", one)
            if len(lst) == 1:
                infos["ipc"] = lst[0]
        return infos


if __name__ == "__main__":
    pass
