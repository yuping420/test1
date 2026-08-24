# 本地测试的执行、配置与日志查看

---

## 执行

在本地ubuntu开发环境中，在`SuperScalarModel`根目录下，执行`python3 ci_scripts/local_test.py`，可以对本地代码执行门禁测试。

---

## 配置

用户可以根据实际测试需求修改`ci_scripts/local_test.py`中的如下配置：
```python
class LocalTest(GhTest):
    # 本地可修改的执行配置
    LOCAL_EVENT = "local_run"  # 或 "workflow_dispatch"
    GLOB_TIMEOUT = 30  # 整体超时，单位：分钟
    SELF_TIMEOUT = 20  # 单个测例执行超时，单位：分钟
    PARREL_CNT = 6     # 执行并发量
    # 要跑的模型及各模型要跑的参数
    MODELS_PARAS = {
        "gfrun": {
            "": "nosoc"
        },
        "gfsim": {
            "-s core.simtEnable=true": "nosoc"
        }
    }
```
- **LOCAL_EVENT**：可以配置为`local_run`或`workflow_dispatch`。
  - 配置为`local_run`，则本次测试`gfrun`将会执行`tests/gfrun-pass-list.txt`中的测例，`gfsim`将会执行`tests/gfsim-pass-list.txt`中的测例；
  - 配置为`workflow_dispatch`，则本次测试`gfrun`将会执行`tests/gfrun-pass-list-nightly.txt`中的测例，`gfsim`将会执行`tests/gfsim-pass-list-nightly.txt`中的测例；
- **GLOB_TIMEOUT**：整体超时，单位：分钟。
- **SELF_TIMEOUT**：单个测例执行超时，单位：分钟。
- **PARREL_CNT**：编译和测例执行时的并发数量。根据电脑的实际情况进行配置。
- **MODELS_PARAS**：详细说明如下：
  - 字典的第一层key（如`gfrun`，`gfsim`），是本次测试要执行的模型名称。可以多个，按需配置；
  - 第二层字典，也就是模型字典，用来配置模型要跑的参数。key是模型要执行的原始参数，value为根据原始参数含义进行简化得到的一个大家都懂的简短描述（该描述会被显示在最后的汇总表）。如：`-s core.soc_enable=true core.bp_mode=0 core.perfect_load_store=false: soc,fullBP,fullLS`。可以多个，按需配置；
  - **示例**：
  ```python
  MODELS_PARAS = {
      "gfrun": {
          "": "nosoc"
      },
      "gfsim": {
          "-s core.soc_enable=true core.bp_mode=0 core.perfect_load_store=false": "soc,fullBP,fullLS",
          "-s core.soc_enable=false core.bp_mode=0 core.perfect_load_store=false": "nosoc,fullBP,fullLS",
          "-s core.soc_enable=true core.bp_mode=0 core.perfect_load_store=true": "soc,fullBP,perfectLS",
          "-s core.soc_enable=false core.bp_mode=0 core.perfect_load_store=true": "soc,fullBP,perfectLS"
      }
  }
  ```

---

## 日志查看

脚本在执行时会自动在`SuperScalarModel`源码的同级目录生成一个名为`build_年月日时分秒`的目录。  
如执行时时间为2026/8/13 11:21:32，则会自动生成一个`build_20260813112132`的目录。  
在该目录保存了各种执行记录，说明如下：  
- **run.log**：脚本的执行日志。就是`local_test.py`脚本执行时输出到屏幕上的内容的保存。
- **models_run_paras.json**：就是上面配置的`MODELS_PARAS`。
- **super_scalar_model_compile.log**：编译日志。
- **super_scalar_model_models/**：该目录下保存了本次测试的模型二进制。
- **testcase_logs/**：该目录下保存了本次测试的所有测例的执行日志，按`tests`目录下测例的目录结构进行保存。
- 其余文件为脚本执行的中间文件。

---

## 常见问题

### 报 `xxx: command not found`
缺xxx
