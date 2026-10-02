"""
电路 ③：NMOS 共源放大器 —— 从直流工作点走到小信号增益

任务：手算静态工作点，判断管子是否工作在饱和区，再求跨导 gm、
      输出电阻 ro 和电压增益 Av，最后用仿真验证并解释误差。

                        VDD = 5 V
                          │
                     [ R_D = 2 kΩ ]
                          │
              vg ──┤G  ┌──┴── vout
                   │   │D
                  M1   │
                   │S  │
                  ─┴────┴─ GND
                 （源极接地 = 共源）

器件参数（level=1 Shichman-Hodges 模型）：
    V_TO = 1 V      阈值电压
    KP   = 200 µA/V²  本征跨导系数
    W/L  = 8 µm / 2 µm = 4
    λ    = 0.02 V⁻¹   沟道长度调制系数

偏置：栅极用理想电压源给 V_GS = 2 V（这样能把注意力集中在放大特性上，
      真实电路会改用分压偏置 + 耦合电容，影响的是输入阻抗而非增益，
      放在最后的延伸思考里）。

手算分两套，这是本脚本最有价值的地方：

  ① 理想平方律模型（先忽略 λ，教材上的入门算法）
       V_ov = V_GS − V_TO = 2 − 1 = 1 V
       I_D  = ½ · KP · (W/L) · V_ov² = ½ × 200µ × 4 × 1² = 0.4 mA
       V_DS = VDD − I_D·R_D = 5 − 0.4m × 2000 = 4.2 V
       饱和判据 V_DS > V_ov → 4.2 > 1，工作在饱和区 ✓

  ② 含沟道长度调制（把 λ 算进去，更接近真实器件）
       I_D = ½·KP·(W/L)·V_ov²·(1 + λ·V_DS)，而 V_DS = VDD − I_D·R_D，
       两个式子互相耦合，联立求解：
       I_D = k(1+λVDD) / (1 + k·λ·R_D)，其中 k = ½·KP·(W/L)·V_ov²
           = 0.4m × 1.1 / (1 + 0.016) = 0.4331 mA
       V_DS = 5 − 0.4331m × 2000 = 4.1339 V

  小信号参数：
       gm = ∂I_D/∂V_GS = KP·(W/L)·V_ov·(1 + λ·V_DS)   （理想：2I_D/V_ov）
       ro = 1 / (λ · I_D)
       Av = −gm · (R_D ∥ ro)      ← 负号表示共源放大器输出反相 180°
"""

import numpy as np

import spice_env
from spice_env import plt

from PySpice.Spice.Netlist import Circuit
from PySpice.Unit import *

# ============================================================
# 参数
# ============================================================
VDD = 5.0            # V
RD = 2000.0          # Ω
VGS_Q = 2.0          # V，静态栅源电压
VTO = 1.0            # V
KP = 200e-6          # A/V²
W = 8e-6             # m
L = 2e-6             # m
LAMBDA = 0.02        # 1/V
CL = 10e-12          # F，负载电容（决定放大器带宽）

MOS_PARAMS = dict(level=1, kp=KP, vto=VTO, lambda_=LAMBDA, w=W, l=L)
W_OVER_L = W / L

# ------------------------------------------------------------
# 手算
# ------------------------------------------------------------
V_OV = VGS_Q - VTO
K_PEAK = 0.5 * KP * W_OVER_L * V_OV ** 2      # 即「忽略 λ 时的 I_D」

# ① 理想
ID_IDEAL = K_PEAK
VDS_IDEAL = VDD - ID_IDEAL * RD
GM_IDEAL = KP * W_OVER_L * V_OV
RO_IDEAL = 1.0 / (LAMBDA * ID_IDEAL)
ROUT_IDEAL = RD * RO_IDEAL / (RD + RO_IDEAL)          # R_D ∥ ro
AV_IDEAL = -GM_IDEAL * ROUT_IDEAL
FP_IDEAL = 1.0 / (2 * np.pi * ROUT_IDEAL * CL)

# ② 含 λ（联立求解）
ID_LAM = K_PEAK * (1 + LAMBDA * VDD) / (1 + K_PEAK * LAMBDA * RD)
VDS_LAM = VDD - ID_LAM * RD
GM_LAM = KP * W_OVER_L * V_OV * (1 + LAMBDA * VDS_LAM)
# ro 这里是本脚本最反直觉的一处（详见文件末尾的误差分析）：
# 输出电导 gds = ∂I_D/∂V_DS = λ · I_D0，用的是「不含 λ 的基准电流 I_D0」，
# 而不是含 λ 修正后的实际电流。所以 ro = 1/(λ·I_D0) = 125 kΩ，
# 与 λ 修正后的 I_D = 0.4331 mA 无关。
RO_LAM = 1.0 / (LAMBDA * K_PEAK)
ROUT_LAM = RD * RO_LAM / (RD + RO_LAM)
AV_LAM = -GM_LAM * ROUT_LAM
FP_LAM = 1.0 / (2 * np.pi * ROUT_LAM * CL)

SAT_CHECK = "饱和区 ✓" if VDS_LAM > V_OV else "线性区（三极管区）"

spice_env.title("电路 ③  NMOS 共源放大器")
spice_env.note(
    f"""
手算结果：
                     理想平方律        含沟道长度调制 λ
    V_ov              {V_OV:.4f} V            {V_OV:.4f} V
    I_D               {ID_IDEAL * 1e3:.4f} mA          {ID_LAM * 1e3:.4f} mA
    V_DS              {VDS_IDEAL:.4f} V            {VDS_LAM:.4f} V
    gm                {GM_IDEAL * 1e3:.4f} mA/V        {GM_LAM * 1e3:.4f} mA/V
    ro = 1/(λ·I_D0)   {RO_IDEAL / 1000:.2f} kΩ           {RO_LAM / 1000:.2f} kΩ   ← 与 λ 无关，见误差分析
    R_out = R_D∥ro    {ROUT_IDEAL:.1f} Ω         {ROUT_LAM:.1f} Ω
    Av = −gm·R_out    {AV_IDEAL:.4f}            {AV_LAM:.4f}
    带宽 f_p          {FP_IDEAL / 1e6:.3f} MHz          {FP_LAM / 1e6:.3f} MHz

饱和判据：V_DS ({VDS_LAM:.3f} V) > V_ov ({V_OV:.3f} V)，管子工作在 {SAT_CHECK}
"""
)


# ============================================================
# 电路构建
# ============================================================
def build_amp(**overrides):
    """
    放大器：VDD → R_D → 漏极(=vout)；栅极由 VGG 提供直流偏置与交流激励；
    源极接地；输出端挂负载电容 C_L。
    """
    vgs = overrides.get("vgs", VGS_Q)
    rd = overrides.get("rd", RD)
    cl = overrides.get("cl", CL)
    # 交流分析的激励要写进源里：DC 给偏置，AC 1V 用于算增益
    ac = overrides.get("ac", 1.0)

    c = Circuit("NMOS 共源放大器")
    c.V("dd", "vdd", c.gnd, VDD @ u_V)
    c.V("gg", "vg", c.gnd, f"DC {vgs}V AC {ac}V")
    c.R("d", "vdd", "vout", rd @ u_Ohm)
    c.MOSFET("M1", "vout", "vg", c.gnd, c.gnd, model="nmos1")
    c.model("nmos1", "nmos", **MOS_PARAMS)
    if cl > 0:
        c.C("L", "vout", c.gnd, cl @ u_F)
    return c


def dc_op(circuit):
    """返回 (V_GS, V_DS, I_D)。I_D 由欧姆定律从 R_D 上的压降反推，顺带验证它。"""
    sim = circuit.simulator(temperature=25, nominal_temperature=25)
    op = sim.operating_point()
    vg = float(np.array(op["vg"]).flatten()[0])
    vout = float(np.array(op["vout"]).flatten()[0])
    i_d = (VDD - vout) / RD
    return vg, vout, i_d


def device_current(vgs, vds):
    """
    测单个管子的特性：栅压固定在 V_GS，漏压固定在 V_DS，返回漏极电流。

    怎么读电流？这里用了一个 SPICE 里的标准技巧：
    串一只 0 V 的理想电压源当「电流表」—— 因为电压恒为 0，
    它不改变电路的工作状态，但它的支路电流就是漏极电流本身，
    精度是浮点精度（而不是像采样电阻那样要靠压降反推）。

    第一版我是串 10 mΩ 采样电阻去测压降的，马上发现问题：
    0.4 mA 流过 10 mΩ 只有 4 µV 压降，而 SPICE 的电压收敛容差是
    RELTOL×V ≈ 1e-3 × 4 V = 4 mV，比待测信号还大三个数量级，
    量出来的电流基本是噪声。
    """
    c = Circuit("单管特性")
    c.V("gg", "vg", c.gnd, vgs @ u_V)
    c.V("dd", "vd_src", c.gnd, vds @ u_V)
    c.V("sense", "vd_src", "drain", 0 @ u_V)     # 0 V 理想电流表
    c.MOSFET("M1", "drain", "vg", c.gnd, c.gnd, model="nmos1")
    c.model("nmos1", "nmos", **MOS_PARAMS)
    op = c.simulator(temperature=25, nominal_temperature=25).operating_point()
    return float(np.array(op.branches["vsense"]).flatten()[0])


def measure_rout():
    """
    直接测输出电阻：把输入端的交流激励置零（只保留直流偏置），
    在输出节点注入 1 A 的交流电流，此时 |vout| 就等于输出电阻。

    再用 R_out = R_D ∥ ro 反解出 ro。

    第一版我是用 |Av|/gm 去反推 R_out 的，结果算出的 ro 是 −6.5×10⁸ Ω ——
    因为 R_out (1965.9 Ω) 和 R_D (2000 Ω) 只差 1.7%，
    两个相近的数相减会剧烈放大误差，这就是典型的「数值相消」。
    教训：能直接测量的物理量，就别拿间接公式去凑。
    """
    c = Circuit("输出电阻测量")
    c.V("dd", "vdd", c.gnd, VDD @ u_V)
    c.V("gg", "vg", c.gnd, f"DC {VGS_Q}V")          # 无交流激励
    c.R("d", "vdd", "vout", RD @ u_Ohm)
    c.MOSFET("M1", "vout", "vg", c.gnd, c.gnd, model="nmos1")
    c.model("nmos1", "nmos", **MOS_PARAMS)
    c.I("probe", c.gnd, "vout", "DC 0 AC 1")         # 注入 1 A 交流
    ac = c.simulator(temperature=25, nominal_temperature=25).ac(
        start_frequency=1 @ u_Hz, stop_frequency=10 @ u_Hz,
        number_of_points=3, variation="dec")
    r_out = float(np.abs(np.array(ac["vout"]))[0])
    return r_out, 1.0 / (1.0 / r_out - 1.0 / RD)


# ------------------------------------------------------------
# 第 1 步：直流工作点
# ------------------------------------------------------------
vg_sim, vds_sim, id_sim = dc_op(build_amp())

print("【直流工作点】")
spice_env.compare([
    ("V_GS", VGS_Q, vg_sim, "V", 0.5),
    ("I_D（理想手算）", ID_IDEAL * 1e3, id_sim * 1e3, "mA", 0.5),
    ("I_D（含 λ 手算）", ID_LAM * 1e3, id_sim * 1e3, "mA", 0.5),
    ("V_DS（理想手算）", VDS_IDEAL, vds_sim, "V", 0.5),
    ("V_DS（含 λ 手算）", VDS_LAM, vds_sim, "V", 0.5),
])

# ------------------------------------------------------------
# 第 2 步：用差分法从仿真里量 gm
# ------------------------------------------------------------
# gm = ∂I_D/∂V_GS，用中心差分（V_GS 上下各偏 10 mV）比直接取单点更稳，
# 而且绕开了「SPICE 内部的小信号参数怎么读」这个问题 —— 用宏观量测出来。
#
# 关键：必须把 V_DS 固定在 Q 点再去测。gm 的定义就是「V_DS 不变时，
# I_D 对 V_GS 的偏导」。第一版我直接拿放大器电路去测，V_GS 一变 V_DS
# 也跟着变（因为 R_D 上的压降变了），量到的是「沿负载线的斜率」而不是 gm，
# 结果偏了 1.6%。改用固定 V_DS 的单管测量后，与手算值吻合到 0.1%。
DV = 0.01
gm_sim = (device_current(VGS_Q + DV, VDS_LAM)
          - device_current(VGS_Q - DV, VDS_LAM)) / (2 * DV)

print("【跨导 gm】由 ΔI_D/ΔV_GS 差分测得")
spice_env.compare([
    ("gm（理想手算）", GM_IDEAL * 1e3, gm_sim * 1e3, "mA/V", 2.0),
    ("gm（含 λ 手算）", GM_LAM * 1e3, gm_sim * 1e3, "mA/V", 2.0),
])

# ------------------------------------------------------------
# 第 3 步：交流分析（扫频，得到增益与带宽）
# ------------------------------------------------------------
ac_sim = build_amp().simulator(temperature=25, nominal_temperature=25)
ac = ac_sim.ac(start_frequency=1 @ u_Hz, stop_frequency=1 @ u_GHz,
               number_of_points=20, variation="dec")

freq = np.array(ac.frequency)
gain_lin = np.abs(np.array(ac["vout"]))
gain_db = 20 * np.log10(gain_lin)
phase_deg = np.degrees(np.angle(np.array(ac["vout"])))

av_sim = gain_lin[0]                 # 低频平台值就是增益大小
f_p_meas = None
target = gain_db[0] - 3.0103
for i in range(1, len(gain_db)):
    if gain_db[i] < target:
        x0, x1 = np.log10(freq[i - 1]), np.log10(freq[i])
        y0, y1 = gain_db[i - 1], gain_db[i]
        f_p_meas = 10 ** (x0 + (y0 - target) * (x1 - x0) / (y0 - y1))
        break

# 直接测输出电阻与 ro（不用 |Av|/gm 反推，理由见 measure_rout 的注释）
rout_sim, ro_sim = measure_rout()

print("【小信号增益 Av = −gm·R_out】")
spice_env.compare([
    ("|Av|（理想手算）", abs(AV_IDEAL), av_sim, "", 2.0),
    ("|Av|（含 λ 手算）", abs(AV_LAM), av_sim, "", 2.0),
    ("R_out（含 λ 手算）", ROUT_LAM, rout_sim, "Ω", 2.0),
    ("ro（含 λ 手算）", RO_LAM / 1000, ro_sim / 1000, "kΩ", 5.0),
    ("带宽 f_p（含 λ 手算）", FP_LAM / 1e6, f_p_meas / 1e6, "MHz", 5.0),
])

spice_env.note(
    f"""
误差分析 —— 把两套手算都列出来，就是为了看清偏差到底来自哪里：

    对照「理想平方律」：I_D 差 {spice_env.rel_err(id_sim, ID_IDEAL):.2f}%，gm 差 {spice_env.rel_err(gm_sim, GM_IDEAL):.2f}%，|Av| 差 {spice_env.rel_err(av_sim, abs(AV_IDEAL)):.2f}%
    对照「含 λ 修正」：  I_D 差 {spice_env.rel_err(id_sim, ID_LAM):.2f}%，gm 差 {spice_env.rel_err(gm_sim, GM_LAM):.2f}%，|Av| 差 {spice_env.rel_err(av_sim, abs(AV_LAM)):.2f}%

    这三个量都是同一个 8.27%，说明偏差只有一个来源：漏掉了沟道长度调制。
    修正之后误差降到 0.2% 以内（剩下的是数值精度），
    所以问题从来不是仿真器算不准 —— 它的求解精度远高于此。

    但写这段代码的过程中我还犯过第二个错，比第一个更有意思：ro 的公式。
    第一版我写 ro = 1/(λ·I_D)，代入含 λ 修正后的实际电流 0.4331 mA，
    算出 115.45 kΩ；仿真却给 125 kΩ —— 正好是用「不含 λ 的基准电流
    0.4 mA」算出来的那个数。

    原因在 level=1 模型的定义：
        I_D  = I_D0 · (1 + λ·V_DS)，其中 I_D0 = ½·KP·(W/L)·V_ov²（与 λ 无关）
        gds  = ∂I_D/∂V_DS = λ · I_D0     ← 是 I_D0，不是 I_D
    物理上也讲得通：沟道长度调制描述的是「V_DS 变化使有效沟道长度变化」，
    它的强度由基准电流决定；λ 带来的那部分额外直流电流，
    并不会再反过来影响输出电导。
    所以 ro = 1/(λ·I_D0) = 125 kΩ，与 λ 修正无关 ——
    这也解释了上表里 ro 那一行为什么两套手算值完全相同。

    另外注意 f_p：它由 R_out·C_L 决定，而 R_out = R_D ∥ ro。
    因为 R_D (2 kΩ) 远小于 ro (125 kΩ)，所以 R_out ≈ R_D，
    带宽对手算误差天然不敏感 —— 这是「输出节点被 R_D 主导」的直接体现。
    如果把 R_D 换成电流源负载（让 ro 变成主角），带宽就会对 ro 极其敏感。
"""
)

# ------------------------------------------------------------
# 第 4 步：瞬态验证（看波形，确认放大与反相）
# ------------------------------------------------------------
trans_amp = 20e-3     # 20 mV 输入，远在放大器的线性范围内
t_circuit = Circuit("NMOS 共源放大器-瞬态")
t_circuit.V("dd", "vdd", t_circuit.gnd, VDD @ u_V)
# 源写法有讲究：必须把直流偏置写进 SIN 的第一个参数（VO 就是直流分量）。
# 看起来更直观的 "DC 2V AC 1V SIN(...)" 在 ngspice 47 上会直接执行失败
# （报 Command 'run' failed），而 PySpice 的 SinusoidalVoltageSource
# 生成的恰好是那种写法 —— 所以这里手写 netlist 字符串。
t_circuit.V("gg", "vg", t_circuit.gnd, f"SIN({VGS_Q}V {trans_amp}V 100kHz)")
t_circuit.R("d", "vdd", "vout", RD @ u_Ohm)
t_circuit.MOSFET("M1", "vout", "vg", t_circuit.gnd, t_circuit.gnd, model="nmos1")
t_circuit.model("nmos1", "nmos", **MOS_PARAMS)
t_circuit.C("L", "vout", t_circuit.gnd, CL @ u_F)

tran = t_circuit.simulator(temperature=25, nominal_temperature=25).transient(
    step_time=0.05 @ u_us, end_time=100 @ u_us)
tt = np.array(tran.time)
vv_in = np.array(tran["vg"]) - VGS_Q          # 去掉直流，只看交流分量
vv_out = np.array(tran["vout"]) - vds_sim

# 用后半段（已经进入稳态）估计实际增益
half = tt > 50e-6
gain_trans = (vv_out[half].max() - vv_out[half].min()) / (vv_in[half].max() - vv_in[half].min())

print("【瞬态验证】100 kHz 正弦，输入 20 mV")
spice_env.compare([
    ("输出摆幅 / 输入摆幅", abs(AV_LAM), gain_trans, "", 5.0),
])
spice_env.note(
    f"""
    瞬态结果：输入摆幅 {((vv_in[half].max() - vv_in[half].min()) * 1e3):.2f} mV，
    输出摆幅 {((vv_out[half].max() - vv_out[half].min()) * 1e3):.2f} mV，
    比值 {gain_trans:.3f}，与交流分析给出的 {av_sim:.3f} 一致 ——
    两条完全不同的技术路线（频域线性化 vs 时域逐步积分）得到同一个答案，
    这是仿真结果可信的最强证据。

    另外看波形会发现输出与输入反相 180°，这正是共源放大器的标志：
    栅压升高 → 沟道电流增大 → R_D 上压降增大 → 漏极电压下降。
"""
)

# ------------------------------------------------------------
# 第 5 步：线性范围测试（增益在多大输入下开始失真）
# ------------------------------------------------------------
print("【线性范围】输入幅度对增益的影响")
levels = [0.002, 0.02, 0.05, 0.1, 0.3, 0.6, 0.9]
print(f"{'输入幅度':>12}{'输出基波':>14}{'实测增益':>12}{'相对小信号':>14}")
print("-" * 54)

lin_rows = []
for amp in levels:
    cc = Circuit(f"线性度-{amp}")
    cc.V("dd", "vdd", cc.gnd, VDD @ u_V)
    cc.V("gg", "vg", cc.gnd, f"SIN({VGS_Q}V {amp}V 100kHz)")
    cc.R("d", "vdd", "vout", RD @ u_Ohm)
    cc.MOSFET("M1", "vout", "vg", cc.gnd, cc.gnd, model="nmos1")
    cc.model("nmos1", "nmos", **MOS_PARAMS)
    cc.C("L", "vout", cc.gnd, CL @ u_F)

    tr = cc.simulator(temperature=25, nominal_temperature=25).transient(
        step_time=0.05 @ u_us, end_time=100 @ u_us)
    ti = np.array(tr.time)
    vo = np.array(tr["vout"]) - vds_sim
    # 重采样到均匀网格再做 FFT：ngspice 的步长是自适应的，时间点并不均匀
    grid = np.linspace(60e-6, 100e-6, 2000)   # 恰好覆盖 4 个 100 kHz 周期
    vo_u = np.interp(grid, ti, vo)
    spec = np.abs(np.fft.rfft(vo_u - vo_u.mean()))
    # 频率分辨率 = 1/(100µs−60µs) = 25 kHz，所以 100 kHz 落在第 4 根谱线上。
    # 第一版我直接取了 spec[1]（那是 25 kHz 的分量），量出来的增益自然是错的。
    bin_idx = int(round(100e3 * (grid[-1] - grid[0])))
    amp_out = 2 * spec[bin_idx] / len(grid)   # 实数信号的单边谱要乘 2
    lin_rows.append((amp, amp_out, amp_out / amp))
    print(f"{amp * 1e3:>9.1f} mV{amp_out * 1e3:>12.3f} mV{amp_out / amp:>12.3f}"
          f"{amp_out / amp / av_sim:>13.1%}")

print()
# 结论不写死：从实测数据里找出增益开始明显偏离小信号值的那个输入幅度
drop_idx = next((i for i, r in enumerate(lin_rows) if r[2] < av_sim * 0.985), None)
if drop_idx is None:
    degrade = f"本次测到 {lin_rows[-1][0] * 1e3:.0f} mV，增益仍保持在小信号值的 {lin_rows[-1][2] / av_sim:.1%}"
else:
    degrade = (f"输入 {lin_rows[drop_idx][0] * 1e3:.0f} mV 时，增益已掉到小信号值的 "
               f"{lin_rows[drop_idx][2] / av_sim:.1%}")

spice_env.note(
    f"""
    {degrade}。

    为什么会失真？栅压一摆大，两头都会出事：
      · 负半周：V_GS 被拉到接近阈值电压，沟道几乎关断，输出电流来不及跟上，
        输出被顶到接近 VDD（削顶）；
      · 正半周：V_GS 拉高使 I_D 剧增、V_DS 被压低，一旦 V_DS 掉到 V_ov 以下，
        管子退出饱和区进入线性区，增益公式整个失效。
    这两件事都不是线性的，所以输出波形不再是纯正弦 —— 用 FFT 提取基波时会发现
    出现了谐波分量，基波幅度因此低于「小信号增益 × 输入幅度」的预期。

    这就是「小信号」三个字的实际含义：不是管子小，而是信号必须小到
    让器件在静态点附近可以被当成线性的。
    另外注意本电路的线性范围相当宽（要到几百毫伏才看出增益下滑），
    原因是增益只有 {av_sim:.2f} 倍、静态 V_DS 又有 {vds_sim:.2f} V 的余量；
    如果把这个放大器做到 50 倍增益，几十毫伏就会削波。
"""
)

# ============================================================
# 画图
# ============================================================
fig, axes = plt.subplots(1, 3, figsize=(14, 4.2), dpi=130)

# --- 图 1：转移特性 + Q 点 + gm 切线 ---
# 转移特性：把 V_DS 固定在 Q 点的值，扫 V_GS（这样 Q 点正好落在曲线上）
vgs_sweep = np.linspace(0.0, 3.0, 46)
id_sweep = [max(device_current(v, VDS_LAM), 0.0) for v in vgs_sweep]

ax = axes[0]
ax.plot(vgs_sweep, np.array(id_sweep) * 1e3, color="#2f6fb3", linewidth=2)
ax.plot([VGS_Q], [id_sim * 1e3], "o", color="#c0392b", markersize=7, zorder=5)
# 在 Q 点画 gm 切线：斜率就是 gm
_vx = np.array([VGS_Q - 0.45, VGS_Q + 0.45])
_vy = id_sim * 1e3 + gm_sim * 1e3 * (_vx - VGS_Q)
ax.plot(_vx, _vy, "--", color="#c0392b", linewidth=1.4)
ax.annotate(f"Q 点 ({VGS_Q:.1f} V, {id_sim * 1e3:.3f} mA)\n切线斜率 = gm = {gm_sim * 1e3:.3f} mA/V",
            xy=(VGS_Q, id_sim * 1e3), xytext=(0.35, 0.62),
            arrowprops=dict(arrowstyle="->", color="#c0392b", lw=1),
            fontsize=9, color="#c0392b")
ax.axvline(VTO, color="#9aa7b4", linestyle=":", linewidth=1)
ax.text(VTO + 0.03, 0.75, f"V_TO = {VTO:.1f} V", fontsize=8.5, color="#5a6a7a")
ax.set_xlabel("栅源电压 V_GS (V)")
ax.set_ylabel("漏极电流 I_D (mA)")
ax.set_title("转移特性（V_GS 扫描）")
ax.grid(alpha=0.3)

# --- 图 2：输出特性族 I_D-V_DS ---
ax = axes[1]
colors = ["#8fb8dd", "#5b93c7", "#2f6fb3", "#1d4f85"]
for vgs_val, col in zip([1.8, 2.0, 2.2, 2.4], colors):
    vds_sweep = np.linspace(0.0, 5.0, 31)
    id_list = np.array([max(device_current(vgs_val, v), 0.0) * 1e3 for v in vds_sweep])
    ax.plot(vds_sweep, id_list, color=col, linewidth=1.8,
            label=f"V_GS = {vgs_val:.1f} V")
    # 饱和区分界点 V_DS = V_ov，在该曲线上取对应点标一条短竖线
    vov = vgs_val - VTO
    ax.plot([vov], [np.interp(vov, vds_sweep, id_list)], "|",
            color=col, markersize=10, markeredgewidth=2)

ax.plot([VDS_LAM], [id_sim * 1e3], "o", color="#c0392b", markersize=7, zorder=5)
ax.annotate(f"Q 点 ({VDS_LAM:.2f} V, {id_sim * 1e3:.3f} mA)",
            xy=(VDS_LAM, id_sim * 1e3), xytext=(0.85, 0.66),
            arrowprops=dict(arrowstyle="->", color="#c0392b", lw=1),
            fontsize=9, color="#c0392b")
ax.set_xlabel("漏源电压 V_DS (V)")
ax.set_ylabel("漏极电流 I_D (mA)")
ax.set_title("输出特性族（│ 标出饱和区分界 V_DS = V_ov）")
ax.legend(fontsize=8.5, loc="lower right")
ax.grid(alpha=0.3)

# --- 图 3：波特图 ---
ax = axes[2]
ax.semilogx(freq, gain_db, color="#2f6fb3", linewidth=1.9, label="增益 (dB)")
ax.axhline(gain_db[0] - 3.0103, color="#9aa7b4", linestyle=":", linewidth=1)
ax.plot([f_p_meas], [gain_db[0] - 3.0103], "o", color="#c0392b", markersize=7)
ax.annotate(f"−3 dB 带宽\nf_p = {f_p_meas / 1e6:.2f} MHz\n（手算 {FP_LAM / 1e6:.2f} MHz）",
            xy=(f_p_meas, gain_db[0] - 3.0103),
            xytext=(f_p_meas * 0.012, gain_db[0] - 2.0),
            arrowprops=dict(arrowstyle="->", color="#c0392b", lw=1),
            fontsize=9, color="#c0392b")
ax.set_xlabel("频率 (Hz)")
ax.set_ylabel("增益 (dB)")
ax.set_title(f"幅频特性：低频增益 {gain_db[0]:.3f} dB（即 {av_sim:.3f} 倍）")
ax.grid(alpha=0.3, which="both")
ax.set_ylim(gain_db[0] - 6, gain_db[0] + 1)

ax2b = ax.twinx()
ax2b.semilogx(freq, phase_deg, color="#e08a1e", linewidth=1.4,
              linestyle="-.", label="相位 (°)")
ax2b.set_ylabel("相位 (°)", color="#e08a1e")

fig.tight_layout()
png = spice_env.os.path.join(spice_env.os.path.dirname(__file__), "nmos_amp.png")
fig.savefig(png, bbox_inches="tight")
print(f"  图已保存：{png}")

# 第二张图：瞬态波形（输入 vs 输出，反相）
fig2, (b1, b2) = plt.subplots(2, 1, figsize=(9, 5.6), dpi=130)
b1.plot(tt * 1e6, vv_in * 1e3, color="#9aa7b4", linewidth=1.6, label="输入交流分量 vin")
b1.plot(tt * 1e6, vv_out * 1e3, color="#2f6fb3", linewidth=1.8, label="输出交流分量 vout")
b1.axhline(0, color="#c8d2dc", linewidth=0.8)
b1.set_xlabel("时间 (µs)")
b1.set_ylabel("交流分量 (mV)")
b1.set_title(f"瞬态波形（100 kHz，输入 {trans_amp * 1e3:.0f} mV）：输出反相 180°")
b1.legend(fontsize=9)
b1.grid(alpha=0.3)

amps = [r[0] * 1e3 for r in lin_rows]
gains = [r[2] / av_sim * 100 for r in lin_rows]
b2.semilogx(amps, gains, "o-", color="#c0392b", linewidth=1.8, markersize=6)
b2.axhline(100, color="#9aa7b4", linestyle=":", linewidth=1)
b2.set_xlabel("输入幅度 (mV)")
b2.set_ylabel("实测增益 / 小信号增益 (%)")
b2.set_title("线性范围：输入越大，增益偏离小信号值越多（波形被削顶）")
b2.grid(alpha=0.3, which="both")
b2.set_ylim(min(gains) - 6, 108)

fig2.tight_layout()
png2 = spice_env.os.path.join(spice_env.os.path.dirname(__file__), "nmos_transient.png")
fig2.savefig(png2, bbox_inches="tight")
print(f"  图已保存：{png2}")

spice_env.hr()
print("小结：饱和区判据、gm、ro、Av、带宽都用手算和仿真各做了一遍。")
print("      误差的主要来源不是仿真器，而是手算时是否记得沟道长度调制 ——")
print("      这条结论本身就是「验证」这件事的意义所在。")
