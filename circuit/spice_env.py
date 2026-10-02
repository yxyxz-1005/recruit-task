"""
电路仿真脚本的公共引导模块（三个电路脚本都要先 import 它）。

它只干三件谁都要做的事：
  1. 让 ngspice 的动态库能被加载（Windows 上最容易翻车的一步）
  2. 让 matplotlib 能画中文（否则标题和轴标签会变成方框）
  3. 提供统一的「手算 vs 仿真」对比打印函数，保证三个脚本的输出格式一致

对大一零基础读者的说明：
  ngspice 是一个用 C 写好的电路仿真程序，PySpice 只是让你能用 Python 去指挥它。
  真正的计算是 ngspice 干的，所以必须先把 ngspice 的 .dll 找到并加载进来。
"""

import os
import sys

# ----------------------------------------------------------------------
# 1. 加载 ngspice 动态库
# ----------------------------------------------------------------------
# Windows 的经典陷阱：加载 ngspice.dll 时，它依赖的 sndfile.dll / samplerate.dll
# 并不会自动在「dll 自己所在的目录」里被查找。必须显式把那个目录加进搜索路径。
# 这就是之前一直报 cannot load library ... error 0x7e 的原因。

_DLL_SUBPATH = os.path.join("PySpice", "Spice", "NgSpice", "Spice64_dll", "dll-vs")


def _locate_ngspice():
    """返回 ngspice.dll 所在目录；找不到就返回 None（由调用方给出友好提示）。"""
    try:
        import PySpice
    except ImportError:
        return None
    base = os.path.dirname(os.path.dirname(os.path.abspath(PySpice.__file__)))
    # PySpice/__init__.py  ->  站点包目录 ->  拼出 dll 子目录
    candidates = [
        os.path.join(base, *_DLL_SUBPATH.split(os.sep)),
        os.path.join(base, "PySpice", "Spice", "NgSpice", "Spice64_dll", "dll-vs"),
    ]
    for d in candidates:
        if os.path.exists(os.path.join(d, "ngspice.dll")):
            return d
    return None


def enable_ngspice():
    """把 ngspice.dll 所在目录注册为 DLL 搜索路径。成功返回目录，失败抛异常。"""
    dll_dir = _locate_ngspice()
    if dll_dir is None:
        raise RuntimeError(
            "找不到 ngspice.dll。请先确认 PySpice 已安装，且 dll-vs 目录下有\n"
            "ngspice.dll / sndfile.dll / samplerate.dll 三个文件。"
        )
    if hasattr(os, "add_dll_directory"):
        os.add_dll_directory(dll_dir)
    os.environ["PATH"] = dll_dir + os.pathsep + os.environ.get("PATH", "")
    return dll_dir


# import 本模块即自动生效，脚本里不必再手写一遍
DLL_DIR = enable_ngspice()

# ----------------------------------------------------------------------
# 1b. 让 ngspice 的启动噪音安静下来
# ----------------------------------------------------------------------
# ngspice 启动时会去找它自带的 xspice 代码模型库（analog.cm、digital.cm 等），
# 这些文件路径是编译时写死的（C:/Spice64/lib/ngspice/），本机不存在，
# 于是会打印一串 Error。对线性电路和基本 MOS 模型没有任何影响，
# 但会污染输出，所以这里在文件描述符层面把它们吃掉。
#
# 为什么要用 dup2 而不是重定向 sys.stdout：
# 这些信息是 ngspice 这个 C 库直接写到 fd 1/2 的，走不到 Python 的 sys.stdout。
# 另外 PySpice 自己还会用 logging 报一条 "Unsupported Ngspice version" 警告。

import logging  # noqa: E402

logging.getLogger("PySpice.Spice.NgSpice.Shared").setLevel(logging.ERROR)
logging.getLogger("PySpice.Spice.NgSpice.Shared").disabled = True


class _SilenceNativeOutput:
    """临时把 fd 1/2 指向空设备，用于吞掉 C 库的打印。"""

    def __enter__(self):
        import sys
        self._saved = (os.dup(1), os.dup(2))
        self._null = os.open(os.devnull, os.O_WRONLY)
        os.dup2(self._null, 1)
        os.dup2(self._null, 2)
        return self

    def __exit__(self, *exc):
        import sys
        sys.stdout.flush()
        sys.stderr.flush()
        os.dup2(self._saved[0], 1)
        os.dup2(self._saved[1], 2)
        for fd in (*self._saved, self._null):
            os.close(fd)
        return False


def _warm_up():
    """跑一次最小仿真，把 ngspice 初始化时的加载噪音提前吃掉。"""
    try:
        from PySpice.Spice.Netlist import Circuit
        from PySpice.Unit import u_V, u_kOhm
        with _SilenceNativeOutput():
            c = Circuit("warmup")
            c.V("1", "n1", c.gnd, 1 @ u_V)
            c.R("1", "n1", c.gnd, 1 @ u_kOhm)
            c.simulator(temperature=25, nominal_temperature=25).operating_point()
        return True
    except Exception:
        return False


NGSPICE_WARMED_UP = _warm_up()

# ----------------------------------------------------------------------
# 2. 让 matplotlib 能显示中文
# ----------------------------------------------------------------------
import matplotlib

matplotlib.use("Agg")  # 无界面后端，直接输出 png，不弹窗口
import matplotlib.pyplot as plt

_CJK_FONTS = ["Microsoft YaHei", "SimHei", "SimSun", "DengXian"]
for _f in _CJK_FONTS:
    if _f in {f.name for f in matplotlib.font_manager.fontManager.ttflist}:
        plt.rcParams["font.sans-serif"] = [_f]
        break
plt.rcParams["axes.unicode_minus"] = False  # 否则负号会显示成方块

# ----------------------------------------------------------------------
# 3. 统一输出格式
# ----------------------------------------------------------------------


def hr(char="=", n=64):
    print(char * n)


def title(text):
    hr()
    print(text)
    hr()


def rel_err(sim, theory):
    """相对误差百分比。理论值为 0 时退化为绝对误差，避免除零。"""
    if theory == 0:
        return abs(sim) * 100
    return abs(sim - theory) / abs(theory) * 100


def compare(rows, headers=("物理量", "手算值", "仿真值", "相对误差")):
    """
    打印「手算 vs 仿真」对比表。

    rows: [(名称, 手算值, 仿真值, 单位, 误差容限%), ...]
    会自动判断是否超差，超差的行会标出来 —— 这不是失败，而是误差分析的起点。
    """
    w0 = max(len(str(r[0])) for r in rows) + 2
    print(f"{headers[0]:<{w0}}{headers[1]:>16}{headers[2]:>16}{headers[3]:>12}")
    print("-" * (w0 + 46))
    for name, theory, sim, unit, tol in rows:
        err = rel_err(sim, theory)
        flag = "" if err <= tol else "  <- 偏大，见误差分析"
        print(
            f"{name:<{w0}}{theory:>13.4f} {unit:<2}{sim:>13.4f} {unit:<2}"
            f"{err:>9.2f} %{flag}"
        )
    print()


def note(text):
    """打印一条解释性说明，缩进两格，和输出数据区分开。"""
    for line in text.strip().splitlines():
        print("  " + line)
    print()


if __name__ == "__main__":
    title("环境自检")
    print("  ngspice.dll 目录 :", DLL_DIR)
    print("  中文字体         :", plt.rcParams["font.sans-serif"][0])
    print("  Python           :", sys.version.split()[0])
    from PySpice.Spice.Netlist import Circuit  # noqa: E402

    print("  PySpice 导入     : OK")
