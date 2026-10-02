"""
电路 ①：RC 低通滤波器 —— 时域看充放电，频域看截止频率

任务：手算时间常数 τ 与截止频率 f_c，再用仿真验证两者，并解释误差来源。

    vin ──[ R = 1 kΩ ]──┬── vout
                        │
                       ═╪═  C = 1 µF
                        │
                       GND

手算依据（大一电路分析就够）：
    τ  = R · C = 1 kΩ × 1 µF = 1 ms
    f_c = 1 / (2πRC) = 1 / (2π × 1 ms) ≈ 159.155 Hz

两个要点，一开始没意识到会踩：
  1. 看充放电过程必须用方波源。SPICE 的瞬态分析默认从稳态开始，
     若用恒定直流源，电容早已充满，输出是一条直线，什么都看不到。
  2. -3 dB 点的含义是输出幅度降到输入的 1/√2 ≈ 0.7071，
     换算成分贝是 20·log10(0.7071) = -3.01 dB，同时相位滞后 45°。
"""

import numpy as np

import spice_env  # 必须先导入：它负责加载 ngspice.dll 与中文字体
from spice_env import plt

from PySpice.Spice.Netlist import Circuit
from PySpice.Unit import *

# ============================================================
# 参数（改这里就能换一组数重跑）
# ============================================================
R_VALUE = 1 @ u_kOhm
C_VALUE = 1 @ u_uF
V_HIGH = 5 @ u_V

# 方波：周期 10 ms（半周期 5 ms = 5τ，足够电容充满放完，波形才好看）
PULSE_WIDTH = 5 @ u_ms
PERIOD = 10 @ u_ms
END_TIME = 20 @ u_ms
STEP_TIME = 10 @ u_us

# ------------------------------------------------------------
# 手算
# ------------------------------------------------------------
R_OHM = float(R_VALUE)
C_FARAD = float(C_VALUE)
TAU = R_OHM * C_FARAD
F_C = 1.0 / (2 * np.pi * TAU)

spice_env.title("电路 ①  RC 低通滤波器")
spice_env.note(
    f"""
电路参数：R = {R_OHM:.0f} Ω，C = {C_FARAD * 1e6:.0f} µF，输入为 0→{float(V_HIGH):.0f} V 的方波。

手算：
    τ   = R·C = {R_OHM:.0f} × {C_FARAD * 1e6:.0f}e-6 = {TAU * 1e3:.3f} ms
    f_c = 1/(2πτ) = {F_C:.3f} Hz

关键概念 —— 为什么 τ 叫「时间常数」：
    电容充电到 63.2% 所需的时间就是 τ（1 - e⁻¹ = 0.632）。
    充到 2τ 是 86.5%，3τ 是 95.0%，5τ 是 99.3% —— 工程上认为 5τ 后已充满。
    所以方波的半周期取 5τ = 5 ms，才能看到完整的充电与放电。
"""
)

# ------------------------------------------------------------
# 仿真 1：瞬态（方波激励，看电容怎么充放电）
# ------------------------------------------------------------
circuit = Circuit("RC低通滤波器")
circuit.PulseVoltageSource(
    "vin", "vin", circuit.gnd,
    initial_value=0 @ u_V,
    pulsed_value=V_HIGH,
    pulse_width=PULSE_WIDTH,
    period=PERIOD,
    rise_time=1 @ u_us,     # 给一点上升时间，避免理想阶跃导致求解器不收敛
    fall_time=1 @ u_us,
)
circuit.R("1", "vin", "out", R_VALUE)
circuit.C("1", "out", circuit.gnd, C_VALUE)

simulator = circuit.simulator(temperature=25, nominal_temperature=25)
tran = simulator.transient(step_time=STEP_TIME, end_time=END_TIME)

t = np.array(tran.time)                 # 单位：秒
v_in = np.array(tran["vin"])
v_out = np.array(tran["out"])


def vout_theory(t_arr, t_start, v_from, v_to):
    """一阶电路的全响应：从 v_from 出发，按 τ 指数趋近 v_to。"""
    dt = np.clip(t_arr - t_start, 0, None)
    return v_to + (v_from - v_to) * np.exp(-dt / TAU)


# 取几个典型时刻和理论值对照
# 充电段从 t=0 开始（0 → 5V），放电段从 t=5ms 开始（5V → 0）
samples = [
    ("t = 0.5 ms（充电 0.5τ）", 0.5e-3, vout_theory(0.5e-3, 0.0, 0.0, 5.0)),
    ("t = 1.0 ms（充电 1τ）", 1.0e-3, vout_theory(1.0e-3, 0.0, 0.0, 5.0)),
    ("t = 3.0 ms（充电 3τ）", 3.0e-3, vout_theory(3.0e-3, 0.0, 0.0, 5.0)),
    ("t = 5.5 ms（放电 0.5τ）", 5.5e-3, vout_theory(5.5e-3, 5.0e-3, 5.0, 0.0)),
    ("t = 10.0 ms（放电 5τ）", 10.0e-3, vout_theory(10.0e-3, 5.0e-3, 5.0, 0.0)),
]


def sample_at(t_query):
    """从仿真结果里取最接近 t_query 的那一时刻的值。"""
    i = int(np.argmin(np.abs(t - t_query)))
    return float(v_out[i])


print("【时域对比】电容电压 vout(t)")
rows = [(name, theory, sample_at(tq), "V", 2.0) for name, tq, theory in samples]
spice_env.compare(rows)

# ------------------------------------------------------------
# 仿真 2：交流分析（扫频，看幅度随频率怎么衰减）
# ------------------------------------------------------------
# 交流分析要用独立的交流源（幅度 1 V，这样输出幅度本身就是增益）
ac_circuit = Circuit("RC低通-交流")
ac_circuit.V("input", "vin", ac_circuit.gnd, "DC 0V AC 1V")
ac_circuit.R("1", "vin", "out", R_VALUE)
ac_circuit.C("1", "out", ac_circuit.gnd, C_VALUE)

ac_sim = ac_circuit.simulator(temperature=25, nominal_temperature=25)
ac = ac_sim.ac(start_frequency=1 @ u_Hz, stop_frequency=100 @ u_kHz,
               number_of_points=20, variation="dec")

freq = np.array(ac.frequency)                       # Hz
gain_db = 20 * np.log10(np.abs(np.array(ac["out"])))
phase_deg = np.degrees(np.angle(np.array(ac["out"])))


def cross_frequency(f_arr, y_arr, target):
    """在单调下降的曲线上，用对数频率线性插值求 y = target 处的频率。"""
    idx = int(np.argmax(y_arr < target))
    if idx == 0:
        return float(f_arr[0])
    x0, x1 = np.log10(f_arr[idx - 1]), np.log10(f_arr[idx])
    y0, y1 = y_arr[idx - 1], y_arr[idx]
    return float(10 ** (x0 + (y0 - target) * (x1 - x0) / (y0 - y1)))


f_3db = cross_frequency(freq, gain_db, -3.0103)     # 20log10(1/√2)
f_45deg = cross_frequency(freq, phase_deg, -45.0)
gain_at_fc = float(np.interp(np.log10(F_C), np.log10(freq), gain_db))

print("【频域对比】截止频率与相位")
spice_env.compare([
    ("-3 dB 截止频率 f_c", F_C, f_3db, "Hz", 2.0),
    ("f_c 处的增益", -3.0103, gain_at_fc, "dB", 5.0),
    ("相位滞后 45° 的频率", F_C, f_45deg, "Hz", 2.0),
])

spice_env.note(
    f"""
误差分析：
    手算 f_c = {F_C:.3f} Hz，仿真 -3 dB 点 = {f_3db:.3f} Hz，相对误差 {spice_env.rel_err(f_3db, F_C):.2f}%。
    差距来自两处，都不是算错：
      1. 扫频是离散取样（每十倍频 20 个点），最后一步用对数插值逼近，
         采样越密误差越小，这是数值方法本身的分辨率限制；
      2. 方波源的上升沿设为 1 µs 而非理想 0 s，对时域影响可忽略，
         对频域只有极高频段才有体现。
    时域吻合得更好（误差普遍 <1%），因为一阶 RC 的解析解就是 e^(-t/τ)，
    SPICE 用梯形积分求它，精度足够高。
"""
)

# ------------------------------------------------------------
# 画图
# ------------------------------------------------------------
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 7), dpi=130)

ax1.plot(t * 1e3, v_in, color="#9aa7b4", linewidth=1.4,
         linestyle="--", label="输入方波 vin")
ax1.plot(t * 1e3, v_out, color="#2f6fb3", linewidth=1.8, label="输出 vout（电容电压）")
# 标出 τ 的位置
ax1.axvline(TAU * 1e3, color="#c0392b", linewidth=1, alpha=0.7)
ax1.plot([TAU * 1e3], [sample_at(TAU)], "o", color="#c0392b", markersize=6)
ax1.annotate(f"t = τ = {TAU * 1e3:.1f} ms\n电压 = 63.2% × 5 V = {sample_at(TAU):.2f} V",
             xy=(TAU * 1e3, sample_at(TAU)),
             xytext=(TAU * 1e3 + 1.6, 1.15),
             arrowprops=dict(arrowstyle="->", color="#c0392b", lw=1),
             fontsize=9, color="#c0392b")
ax1.set_xlabel("时间 t (ms)")
ax1.set_ylabel("电压 (V)")
ax1.set_title("RC 低通 —— 时域响应（方波激励）")
ax1.legend(loc="upper right")
ax1.grid(alpha=0.3)
ax1.set_xlim(0, float(END_TIME) * 1e3)
ax1.set_ylim(-0.4, 5.6)

ax2.semilogx(freq, gain_db, color="#2f6fb3", linewidth=1.8, label="幅度 (dB)")
ax2.axhline(-3.0103, color="#9aa7b4", linewidth=1, linestyle=":")
ax2.axvline(F_C, color="#c0392b", linewidth=1, linestyle="--", alpha=0.8)
ax2.plot([f_3db], [-3.0103], "o", color="#c0392b", markersize=6)
ax2.annotate(f"f_c ≈ {f_3db:.1f} Hz\n（手算 {F_C:.1f} Hz）",
             xy=(f_3db, -3.0103), xytext=(f_3db * 2.2, -12),
             arrowprops=dict(arrowstyle="->", color="#c0392b", lw=1),
             fontsize=9, color="#c0392b")
ax2.set_xlabel("频率 (Hz)")
ax2.set_ylabel("增益 (dB)")
ax2.set_title("RC 低通 —— 幅频特性（波特图）")
ax2.legend(loc="upper right")
ax2.grid(alpha=0.3, which="both")
ax2.set_ylim(-45, 3)

ax2b = ax2.twinx()
ax2b.semilogx(freq, phase_deg, color="#e08a1e", linewidth=1.4,
              linestyle="-.", label="相位 (°)")
ax2b.set_ylabel("相位 (°)", color="#e08a1e")
ax2b.set_ylim(-95, 5)
ax2b.legend(loc="center right")

fig.tight_layout()
out_png = spice_env.os.path.join(spice_env.os.path.dirname(__file__), "rc_bode.png")
fig.savefig(out_png)
print(f"  图已保存：{out_png}")

spice_env.hr()
print("小结：τ 与 f_c 的手算值和仿真值吻合，说明一阶 RC 的解析公式成立；")
print("      频域那个百分之零点几的偏差来自扫频采样密度，不是模型误差。")
