import os
import numpy as np
import matplotlib.pyplot as plt


class RLS_Parameter_And_SoP_Estimator:
    """
    Online Recursive Least Squares (RLS) with Forgetting Factor for Battery
    Internal Resistance (R0), Polarization (R1, C1), State of Health (SoH_R),
    and Multi-Constraint Horizon State of Power (SoP) Estimation.

    ARX Regression Model for Terminal Voltage Difference:
        y(k) = V_t(k) - OCV(SoC_k)
        y(k) = a1 * y(k-1) + b0 * I(k) + b1 * I(k-1)
    where:
        phi(k)   = [y(k-1), I(k), I(k-1)]^T
        theta(k) = [a1, b0, b1]^T
    Physical parameter mapping (Bilinear / ZOH):
        a1 = exp(-dt / (R1 * C1))
        R0 = -b0
        R1 = (b1 + a1 * R0) / (a1 - 1)
    """

    def __init__(
        self,
        r0_init=0.015,
        r1_init=0.020,
        c1_init=3000.0,
        forgetting_factor=0.994,
        dt=1.0,
        r0_bol=0.015,
        r0_eol=0.030,
        capacity_ah=5.0,
        v_min=2.80,
        v_max=4.20,
        soc_min=0.10,
        soc_max=0.95,
        i_max_dch_hw=35.0,
        i_max_chg_hw=-20.0,
    ):
        self.lmbd = forgetting_factor
        self.dt = dt
        self.r0_bol = r0_bol
        self.r0_eol = r0_eol
        self.capacity_s = capacity_ah * 3600.0

        self.v_min = v_min
        self.v_max = v_max
        self.soc_min = soc_min
        self.soc_max = soc_max
        self.i_max_dch_hw = i_max_dch_hw
        self.i_max_chg_hw = i_max_chg_hw

        # Initialize ARX parameter vector theta = [a1, b0, b1]^T
        a1_0 = np.exp(-dt / (r1_init * c1_init))
        b0_0 = -r0_init
        b1_0 = a1_0 * r0_init - r1_init * (1.0 - a1_0)
        self.theta = np.array([[a1_0], [b0_0], [b1_0]], dtype=float)

        # Covariance matrix P(0)
        self.P = np.diag([10.0, 10.0, 10.0])

        # Memory states for ARX regression
        self.prev_y = 0.0
        self.prev_i = 0.0

        # Physical parameter estimates
        self.r0_est = r0_init
        self.r1_est = r1_init
        self.c1_est = c1_init

        # NMC OCV polynomial coefficients
        self.ocv_coefs = [-18.232, 62.915, -82.684, 51.341, -15.127, 3.0645, 3.3210]

    def ocv_func(self, soc):
        return float(np.polyval(self.ocv_coefs, np.clip(soc, 0.0, 1.0)))

    def update_rls(self, v_terminal, current, soc):
        """
        Executes one step of Forgetting-Factor RLS when current excitation is sufficient.
        """
        ocv = self.ocv_func(soc)
        y_k = v_terminal - ocv

        phi = np.array([[self.prev_y], [current], [self.prev_i]], dtype=float)

        # Update RLS only when dynamic excitation exists to avoid covariance windup
        if abs(current - self.prev_i) > 0.2 or abs(current) > 0.5:
            denom = self.lmbd + (phi.T @ self.P @ phi).item()
            K = (self.P @ phi) / denom
            err = y_k - (phi.T @ self.theta).item()
            self.theta = self.theta + K * err
            self.P = (np.eye(3) - K @ phi.T) @ self.P / self.lmbd

            # Extract physical parameters with stability bounds
            a1 = float(np.clip(self.theta[0, 0], 0.80, 0.9995))
            b0 = float(self.theta[1, 0])
            b1 = float(self.theta[2, 0])

            r0_candidate = np.clip(-b0, 0.005, 0.080)
            r1_candidate = np.clip((b1 + a1 * r0_candidate) / (a1 - 1.0), 0.005, 0.080)
            tau_candidate = -self.dt / np.log(a1)
            c1_candidate = np.clip(tau_candidate / r1_candidate, 500.0, 15000.0)

            # Smooth physical estimates
            self.r0_est = 0.90 * self.r0_est + 0.10 * r0_candidate
            self.r1_est = 0.90 * self.r1_est + 0.10 * r1_candidate
            self.c1_est = 0.90 * self.c1_est + 0.10 * c1_candidate

        self.prev_y = y_k
        self.prev_i = current

        # Compute Resistance State of Health (SoH_R)
        soh_r = (self.r0_eol - self.r0_est) / (self.r0_eol - self.r0_bol) * 100.0
        soh_r = float(np.clip(soh_r, 0.0, 100.0))

        return self.r0_est, self.r1_est, soh_r

    def compute_sop(self, soc, v_rc, horizon_s=10.0):
        """
        Computes Multi-Constraint Horizon State of Power (SoP) over a pulse horizon
        (default 10 seconds) for both Discharge (>0) and Charge (<0).
        """
        ocv = self.ocv_func(soc)
        tau = self.r1_est * self.c1_est
        exp_h = np.exp(-horizon_s / tau)
        r_eff = self.r0_est + self.r1_est * (1.0 - exp_h)

        # 1. Voltage-Constrained Current Limits over Horizon delta_t
        i_max_dch_v = (ocv - v_rc * exp_h - self.v_min) / r_eff
        i_min_chg_v = (ocv - v_rc * exp_h - self.v_max) / r_eff  # Negative value

        # 2. SoC-Constrained Current Limits over Horizon delta_t
        i_max_dch_soc = max(0.0, (soc - self.soc_min) * self.capacity_s / horizon_s)
        i_min_chg_soc = min(0.0, (soc - self.soc_max) * self.capacity_s / horizon_s)

        # 3. Combine all constraints (Voltage, SoC, Hardware Limits)
        i_peak_dch = max(0.0, min(i_max_dch_v, i_max_dch_soc, self.i_max_dch_hw))
        i_peak_chg = min(0.0, max(i_min_chg_v, i_min_chg_soc, self.i_max_chg_hw))

        # Terminal voltage at the end of the 10s max pulse
        v_end_dch = max(self.v_min, ocv - v_rc * exp_h - i_peak_dch * r_eff)
        v_end_chg = min(self.v_max, ocv - v_rc * exp_h - i_peak_chg * r_eff)

        p_max_dch_w = i_peak_dch * v_end_dch
        p_max_chg_w = abs(i_peak_chg * v_end_chg)

        return p_max_dch_w, p_max_chg_w, i_peak_dch, abs(i_peak_chg)


def run_rls_soh_sop_simulation():
    os.makedirs("assets", exist_ok=True)
    np.random.seed(7)

    dt = 1.0
    time = np.arange(0, 3600, dt)

    # Dynamic current excitation profile (WLTP / DST hybrid)
    current = np.zeros_like(time)
    for i in range(len(time)):
        c = i % 240
        if c < 40:
            current[i] = 6.0
        elif c < 70:
            current[i] = 18.0
        elif c < 110:
            current[i] = 0.0
        elif c < 140:
            current[i] = -8.0
        elif c < 190:
            current[i] = 10.0
        else:
            current[i] = 2.0

    # True cell parameters with simulated resistance aging/heating drift:
    # R0 starts at 15 mOhm (100% SoH_R) and rises to 24 mOhm (40% SoH_R)
    r0_true_profile = 0.015 + 0.009 * (1.0 - np.exp(-time / 1400.0))
    r1_true = 0.022
    c1_true = 3200.0
    capacity_s = 5.0 * 3600.0

    estimator = RLS_Parameter_And_SoP_Estimator(
        r0_init=0.012,  # Deliberate initial mismatch (12 mOhm vs 15 mOhm true)
        r1_init=0.018,
        c1_init=3000.0,
        forgetting_factor=0.992,
        dt=dt,
    )

    soc = 0.92
    v_rc = 0.0

    r0_est_hist = np.zeros_like(time)
    soh_true_hist = np.zeros_like(time)
    soh_est_hist = np.zeros_like(time)
    soc_hist = np.zeros_like(time)
    p_dch_hist = np.zeros_like(time)
    p_chg_hist = np.zeros_like(time)

    for i in range(len(time)):
        r0_t = r0_true_profile[i]
        tau_t = r1_true * c1_true
        alpha = np.exp(-dt / tau_t)

        v_rc = v_rc * alpha + r1_true * current[i] * (1.0 - alpha)
        soc -= (current[i] * dt) / capacity_s
        soc = float(np.clip(soc, 0.05, 0.98))

        ocv = estimator.ocv_func(soc)
        vt_true = ocv - v_rc - current[i] * r0_t
        vt_meas = vt_true + np.random.normal(0.0, 0.0025)  # 2.5 mV ADC noise

        r0_est, _, soh_est = estimator.update_rls(vt_meas, current[i], soc)
        p_dch, p_chg, _, _ = estimator.compute_sop(soc, v_rc, horizon_s=10.0)

        r0_est_hist[i] = r0_est
        soh_true_hist[i] = (0.030 - r0_t) / (0.030 - 0.015) * 100.0
        soh_est_hist[i] = soh_est
        soc_hist[i] = soc
        p_dch_hist[i] = p_dch
        p_chg_hist[i] = p_chg

    # --- Plotting ---
    fig, axs = plt.subplots(2, 2, figsize=(14, 9), sharex=True)

    # 1. Online R0 Identification via RLS
    axs[0, 0].plot(time / 60.0, r0_true_profile * 1000, color="black", linewidth=2.0, label="Gerçek Ohmik Direnç R0")
    axs[0, 0].plot(time / 60.0, r0_est_hist * 1000, color="crimson", linestyle="--", linewidth=1.8, label="RLS Kestirimi R0_hat (λ=0.992)")
    axs[0, 0].set_title("Unutma Faktörlü RLS ile Çevrimiçi Ohmik Direnç (R0) Takibi")
    axs[0, 0].set_ylabel("Ohmik Direnç R0 [mΩ]")
    axs[0, 0].grid(True, linestyle="--", alpha=0.6)
    axs[0, 0].legend(loc="lower right")

    # 2. State of Health (SoH_R) Tracking
    axs[0, 1].plot(time / 60.0, soh_true_hist, color="black", linewidth=2.0, label="Gerçek Direnç Bazlı SoH_R")
    axs[0, 1].plot(time / 60.0, soh_est_hist, color="forestgreen", linestyle="--", linewidth=1.8, label="RLS Tahmini SoH_R")
    axs[0, 1].set_title("Hücre Sağlık Durumu (SoH_R) Kestirimi")
    axs[0, 1].set_ylabel("Sağlık Durumu SoH_R [%]")
    axs[0, 1].grid(True, linestyle="--", alpha=0.6)
    axs[0, 1].legend(loc="upper right")

    # 3. Multi-Constraint State of Power (SoP) Envelope
    axs[1, 0].plot(time / 60.0, p_dch_hist, color="darkorange", linewidth=2.0, label="Maks. Deşarj Gücü SoP_dch (10s Ufuk)")
    axs[1, 0].plot(time / 60.0, p_chg_hist, color="royalblue", linewidth=2.0, label="Maks. Rejeneratif Şarj Gücü SoP_chg (10s Ufuk)")
    axs[1, 0].set_title("Çok-Kısıtlı (Gerilim, SoC, Akım) Dinamik Güç Durumu (SoP)")
    axs[1, 0].set_xlabel("Zaman [Dakika]")
    axs[1, 0].set_ylabel("Kullanılabilir Pik Güç [W / Hücre]")
    axs[1, 0].grid(True, linestyle="--", alpha=0.6)
    axs[1, 0].legend(loc="center right")

    # 4. SoC Trajectory & Derating Region
    axs[1, 1].plot(time / 60.0, soc_hist * 100.0, color="purple", linewidth=2.0, label="Hücre SoC [%]")
    axs[1, 1].axhline(y=10.0, color="crimson", linestyle=":", label="Alt SoC Koruma Sınırı (%10)")
    axs[1, 1].set_title("Sürüş Döngüsü Boyunca SoC Değişimi ve Güç Kısıtlama (Derating) Etkisi")
    axs[1, 1].set_xlabel("Zaman [Dakika]")
    axs[1, 1].set_ylabel("SoC [%]")
    axs[1, 1].grid(True, linestyle="--", alpha=0.6)
    axs[1, 1].legend(loc="upper right")

    plt.tight_layout()
    output_path = "assets/rls_soh_sop_estimation.png"
    plt.savefig(output_path, dpi=300)
    plt.close(fig)

    print("=== RLS Çevrimiçi Parametre (SoH_R) ve Çok-Kısıtlı SoP Raporu ===")
    print(f"Gerçek Son R0 Direnci: {r0_true_profile[-1]*1000:.2f} mOhm | RLS Tahmini: {r0_est_hist[-1]*1000:.2f} mOhm")
    print(f"Direnç Kestirim Hatası: {abs(r0_true_profile[-1] - r0_est_hist[-1])*1000:.3f} mOhm")
    print(f"Başlangıç Pik Deşarj Gücü (SoC %92): {p_dch_hist[10]:.1f} W/hücre")
    print(f"Düşük SoC Pik Deşarj Gücü (SoC %{soc_hist[-1]*100:.1f}): {p_dch_hist[-1]:.1f} W/hücre (Gerilim & SoC Derating Aktif)")
    print(f"Grafik kaydedildi: '{output_path}'")


if __name__ == "__main__":
    run_rls_soh_sop_simulation()
