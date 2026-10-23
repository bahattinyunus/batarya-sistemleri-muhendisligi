import os
import numpy as np
import matplotlib.pyplot as plt


class BatteryCell2RCHysteresis:
    """
    High-Fidelity 2-RC Electro-Thermal Battery Cell Model with Plett Hysteresis (LFP Chemistry).

    Features:
    - Dual RC Polarization Branches:
        * Fast dynamics (R1, C1): Charge-transfer & SEI layer kinetics (tau_1 ~ 15-30s)
        * Slow dynamics (R2, C2): Solid-phase Li+ mass diffusion (tau_2 ~ 200-500s)
    - Plett One-State Hysteresis Model:
        * dh/dt = -|gamma * I / Q_n| * (h - sgn(I))
        * V_h(t) = M(SoC) * h(t) + M_0 * sgn(I)
    - Arrhenius Temperature Dependence of Internal Resistances:
        * R(T) = R_ref * exp((E_a / R_gas) * (1/T - 1/T_ref))
    """

    def __init__(
        self,
        r0_ref=0.0012,
        r1_ref=0.0010,
        c1_ref=20000.0,
        r2_ref=0.0015,
        c2_ref=200000.0,
        capacity_ah=50.0,
        initial_soc=1.0,
        gamma_hyst=25.0,
        max_hyst_v=0.018,
        ea_j_mol=22000.0,
    ):
        self.r0_ref = r0_ref
        self.r1_ref = r1_ref
        self.c1 = c1_ref
        self.r2_ref = r2_ref
        self.c2 = c2_ref
        self.capacity_s = capacity_ah * 3600.0

        # State variables: [V_rc1, V_rc2, SoC, h]
        self.v_rc1 = 0.0
        self.v_rc2 = 0.0
        self.soc = float(initial_soc)
        self.h = 0.0  # Dimensionless hysteresis state in [-1, 1]

        # Plett hysteresis parameters
        self.gamma_hyst = gamma_hyst  # Hysteresis decay rate constant
        self.max_hyst_v = max_hyst_v  # Half-width of hysteresis loop (Volts)

        # Arrhenius parameters
        self.ea_j_mol = ea_j_mol      # Activation energy (J/mol)
        self.r_gas = 8.31446          # Universal gas constant (J/(mol*K))
        self.t_ref_k = 298.15         # Reference temperature (25 deg C)

    def lfp_ocv(self, soc):
        """
        Combined Nernst-Empirical model for LFP (LiFePO4) flat-plateau OCV curve.
        Exhibits a very flat plateau (~3.28V - 3.33V) between 20% and 90% SoC,
        sharp drop below 10% SoC, and steep rise above 95% SoC.
        """
        s = np.clip(soc, 1e-4, 1.0 - 1e-4)
        v_oc = (
            3.285
            + 0.045 * s
            - 0.085 * np.exp(-32.0 * s)
            + 0.145 * np.exp(-40.0 * (1.0 - s))
            - 0.012 / (s + 0.03)
            + 0.008 * np.log(s / (1.0 - s))
        )
        return v_oc

    def arrhenius_factor(self, temp_c):
        """Computes Arrhenius resistance scaling factor relative to 25°C."""
        temp_k = np.clip(temp_c + 273.15, 233.15, 353.15)
        return np.exp((self.ea_j_mol / self.r_gas) * (1.0 / temp_k - 1.0 / self.t_ref_k))

    def get_resistances(self, temp_c, soc):
        """Returns temperature and SoC-adjusted (R0, R1, R2)."""
        k_temp = self.arrhenius_factor(temp_c)
        # Resistance also increases at very low SoC (<15%) due to depletion of charge carriers
        k_soc = 1.0 + 0.65 * np.exp(-18.0 * np.clip(soc, 0.0, 1.0))
        scale = k_temp * k_soc
        return self.r0_ref * scale, self.r1_ref * scale, self.r2_ref * scale

    def step(self, current, dt, temp_c=25.0):
        """
        Advances the 2-RC + Hysteresis battery model by dt seconds.
        current > 0: Discharge, current < 0: Charge.
        """
        r0, r1, r2 = self.get_resistances(temp_c, self.soc)

        # 1. Update fast & slow RC branches via exact ZOH discretization
        tau1 = r1 * self.c1
        tau2 = r2 * self.c2
        alpha1 = np.exp(-dt / tau1)
        alpha2 = np.exp(-dt / tau2)

        self.v_rc1 = self.v_rc1 * alpha1 + r1 * current * (1.0 - alpha1)
        self.v_rc2 = self.v_rc2 * alpha2 + r2 * current * (1.0 - alpha2)

        # 2. Update Plett Hysteresis state
        # Convention: charging (I < 0) drives h -> +1 (upper branch), discharging (I > 0) drives h -> -1
        if abs(current) > 1e-4:
            ah_factor = np.exp(-abs(self.gamma_hyst * current * dt / self.capacity_s))
            target_h = -np.sign(current)  # +1 for charge (I<0), -1 for discharge (I>0)
            self.h = ah_factor * self.h + (1.0 - ah_factor) * target_h

        # 3. Update SoC via Coulomb Counting
        self.soc -= (current * dt) / self.capacity_s
        self.soc = float(np.clip(self.soc, 0.0, 1.0))

        # 4. Compute Terminal Voltage
        ocv_equil = self.lfp_ocv(self.soc)
        v_hyst = self.max_hyst_v * self.h
        v_oc_effective = ocv_equil + v_hyst
        v_terminal = v_oc_effective - current * r0 - self.v_rc1 - self.v_rc2

        return v_terminal, ocv_equil, v_oc_effective, self.v_rc1, self.v_rc2, r0


def run_hppc_and_hysteresis_demo():
    """
    Runs two complementary characterization experiments:
    1) Full Charge/Discharge OCV Hysteresis Loop (NMC vs LFP flat-plateau comparison)
    2) HPPC (Hybrid Pulse Power Characterization) Multi-Temperature Dynamic Response
    """
    os.makedirs("assets", exist_ok=True)

    # --- Experiment A: Hysteresis Loop & Flat OCV Curve ---
    soc_grid = np.linspace(0.01, 0.99, 300)
    cell_lfp = BatteryCell2RCHysteresis(capacity_ah=50.0, max_hyst_v=0.020)
    ocv_base = np.array([cell_lfp.lfp_ocv(s) for s in soc_grid])
    ocv_charge_branch = ocv_base + cell_lfp.max_hyst_v
    ocv_discharge_branch = ocv_base - cell_lfp.max_hyst_v

    # --- Experiment B: HPPC Pulse Profile at 25°C vs 0°C ---
    dt = 1.0
    total_time = 3600  # 1 hour HPPC sequence
    time = np.arange(0, total_time, dt)

    # Construct HPPC Profile:
    # 10s 2C discharge pulse (100A) -> 40s rest -> 10s 1.5C regen pulse (-75A) -> 540s 1C discharge sweep
    current_profile = np.zeros_like(time, dtype=float)
    for idx, t in enumerate(time):
        cycle_t = t % 600
        if 20 <= cycle_t < 30:
            current_profile[idx] = 100.0   # 2C Discharge Pulse
        elif 30 <= cycle_t < 70:
            current_profile[idx] = 0.0     # 40s Relaxation
        elif 70 <= cycle_t < 80:
            current_profile[idx] = -75.0   # 1.5C Regen Charge Pulse
        elif 80 <= cycle_t < 140:
            current_profile[idx] = 0.0     # 60s Relaxation
        elif 140 <= cycle_t < 440:
            current_profile[idx] = 35.0    # SoC step-down discharge
        else:
            current_profile[idx] = 0.0     # Rest before next HPPC pulse

    cell_25c = BatteryCell2RCHysteresis(capacity_ah=50.0, initial_soc=0.95)
    cell_0c = BatteryCell2RCHysteresis(capacity_ah=50.0, initial_soc=0.95)

    vt_25c = np.zeros_like(time, dtype=float)
    vt_0c = np.zeros_like(time, dtype=float)
    ocv_eff_25c = np.zeros_like(time, dtype=float)
    vrc1_25c = np.zeros_like(time, dtype=float)
    vrc2_25c = np.zeros_like(time, dtype=float)

    for i in range(len(time)):
        vt_25c[i], _, ocv_eff_25c[i], vrc1_25c[i], vrc2_25c[i], _ = cell_25c.step(
            current_profile[i], dt, temp_c=25.0
        )
        vt_0c[i], _, _, _, _, _ = cell_0c.step(current_profile[i], dt, temp_c=0.0)

    # --- Plotting ---
    fig, axs = plt.subplots(2, 2, figsize=(14, 9))

    # 1. LFP OCV-SoC & Hysteresis Envelope
    axs[0, 0].plot(soc_grid * 100, ocv_charge_branch, color="crimson", linestyle="--", linewidth=1.5, label="Şarj Kolu (Üst Histerezis)")
    axs[0, 0].plot(soc_grid * 100, ocv_base, color="black", linewidth=2.0, label="Denge OCV Eğrisi (LFP)")
    axs[0, 0].plot(soc_grid * 100, ocv_discharge_branch, color="navy", linestyle="--", linewidth=1.5, label="Deşarj Kolu (Alt Histerezis)")
    axs[0, 0].fill_between(soc_grid * 100, ocv_discharge_branch, ocv_charge_branch, color="gold", alpha=0.25, label="Histerezis Zarflama Bandı (±20 mV)")
    axs[0, 0].set_title("LFP Hücre Düz Platolu OCV ve Plett Histerezis Zarflaması")
    axs[0, 0].set_xlabel("Şarj Durumu - SoC [%]")
    axs[0, 0].set_ylabel("Açık Devre Gerilimi [V]")
    axs[0, 0].grid(True, linestyle="--", alpha=0.6)
    axs[0, 0].legend(loc="lower right", fontsize=8.5)

    # 2. Arrhenius Resistance Map across Temperature & SoC
    temps_c = np.linspace(-15, 55, 100)
    r0_curve_80 = [cell_lfp.get_resistances(t, 0.80)[0] * 1000 for t in temps_c]
    r0_curve_10 = [cell_lfp.get_resistances(t, 0.10)[0] * 1000 for t in temps_c]
    axs[0, 1].plot(temps_c, r0_curve_80, color="forestgreen", linewidth=2.0, label="R0 @ %80 SoC")
    axs[0, 1].plot(temps_c, r0_curve_10, color="darkorange", linewidth=2.0, linestyle="-.", label="R0 @ %10 SoC (Deplesyon Bölgesi)")
    axs[0, 1].axvline(x=25.0, color="gray", linestyle=":", label="Referans Sıcaklık (25°C)")
    axs[0, 1].set_title("Arrhenius Yasasına Göre Ohmik İç Direnç Değişimi R0(T, SoC)")
    axs[0, 1].set_xlabel("Hücre Sıcaklığı [°C]")
    axs[0, 1].set_ylabel("Ohmik Direnç R0 [mΩ]")
    axs[0, 1].grid(True, linestyle="--", alpha=0.6)
    axs[0, 1].legend(loc="upper right", fontsize=8.5)

    # 3. HPPC Terminal Voltage Comparison (25°C vs 0°C)
    axs[1, 0].plot(time / 60.0, ocv_eff_25c, color="black", linestyle=":", linewidth=1.3, label="Efektif OCV + Histerezis (25°C)")
    axs[1, 0].plot(time / 60.0, vt_25c, color="forestgreen", linewidth=1.6, label="Terminal Gerilimi Vt @ 25°C")
    axs[1, 0].plot(time / 60.0, vt_0c, color="crimson", linewidth=1.4, alpha=0.85, label="Terminal Gerilimi Vt @ 0°C (Arrhenius Etkisi)")
    axs[1, 0].set_title("HPPC Testi: 25°C vs 0°C Hücre Dinamik Gerilim Cevabı")
    axs[1, 0].set_xlabel("Zaman [Dakika]")
    axs[1, 0].set_ylabel("Gerilim [V]")
    axs[1, 0].grid(True, linestyle="--", alpha=0.6)
    axs[1, 0].legend(loc="lower left", fontsize=8.5)

    # 4. Fast (V_rc1) vs Slow (V_rc2) Polarization Dynamics
    axs[1, 1].plot(time / 60.0, vrc1_25c * 1000, color="royalblue", linewidth=1.6, label="Hızlı Polarizasyon V_rc1 (Yük Transferi)")
    axs[1, 1].plot(time / 60.0, vrc2_25c * 1000, color="purple", linewidth=1.8, label="Yavaş Polarizasyon V_rc2 (Katı Faz Difüzyonu)")
    axs[1, 1].set_title("2-RC Modeli: Hızlı (τ1) ve Yavaş (τ2) Polarizasyon Gerilimleri")
    axs[1, 1].set_xlabel("Zaman [Dakika]")
    axs[1, 1].set_ylabel("Polarizasyon Düşümü [mV]")
    axs[1, 1].grid(True, linestyle="--", alpha=0.6)
    axs[1, 1].legend(loc="upper right", fontsize=8.5)

    plt.tight_layout()
    output_path = "assets/hppc_2rc_hysteresis.png"
    plt.savefig(output_path, dpi=300)
    plt.close(fig)

    print("=== 2-RC + Plett Histerezis & HPPC Karakterizasyon Raporu ===")
    print(f"Nominal Kapasite: 50.0 Ah (LFP Kimyası)")
    print(f"25°C R0 Direnci (%80 SoC): {cell_lfp.get_resistances(25.0, 0.80)[0]*1000:.2f} mOhm")
    print(f" 0°C R0 Direnci (%80 SoC): {cell_lfp.get_resistances(0.0, 0.80)[0]*1000:.2f} mOhm")
    print(f"25°C Maksimum Gerilim Çökmesi (100A Darbe): {(ocv_eff_25c[29] - vt_25c[29])*1000:.1f} mV")
    print(f" 0°C Maksimum Gerilim Çökmesi (100A Darbe): {(ocv_eff_25c[29] - vt_0c[29])*1000:.1f} mV")
    print(f"Grafik kaydedildi: '{output_path}'")


if __name__ == "__main__":
    run_hppc_and_hysteresis_demo()
