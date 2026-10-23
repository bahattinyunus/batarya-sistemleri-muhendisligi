import os
import numpy as np
import matplotlib.pyplot as plt


class PackBalancingSimulator:
    """
    Multi-Cell (12S) Battery Pack Balancing & HV Isolation Monitoring Simulator.

    Compares:
    1. Passive Shunt Balancing (Bleed Resistor R_bleed = 33 Ohm, dissipates excess charge as heat)
    2. Active Inductive Balancing (Buck-Boost / Flyback topology, transfers charge from high to low cells)
    3. High-Voltage Isolation Monitoring Device (IMD - ISO 6469-3 / UN ECE R100)
    """

    def __init__(self, initial_socs, capacities_ah, r_bleed=33.0, active_current=1.5, active_eff=0.88):
        self.num_cells = len(initial_socs)
        self.initial_socs = np.array(initial_socs, dtype=float)
        self.capacities_c = np.array(capacities_ah, dtype=float) * 3600.0  # Coulombs
        self.r_bleed = r_bleed
        self.active_current = active_current
        self.active_eff = active_eff

        # NMC OCV polynomial coefficients
        self.ocv_coefs = [-18.232, 62.915, -82.684, 51.341, -15.127, 3.0645, 3.3210]

    def get_ocv(self, soc):
        return np.polyval(self.ocv_coefs, np.clip(soc, 0.0, 1.0))

    def simulate_passive(self, max_time_s=7200, dt=5.0, soc_tol=0.003):
        """
        Simulates Passive Balancing:
        All cells above (min_soc + soc_tol) turn on their bleed MOSFETs.
        Includes PCB thermal duty-cycle limit (80% duty factor).
        """
        socs = self.initial_socs.copy()
        time_steps = np.arange(0, max_time_s, dt)
        soc_history = np.zeros((len(time_steps), self.num_cells))
        power_loss_history = np.zeros(len(time_steps))
        cumulative_heat_j = 0.0
        converged_time = max_time_s
        converged = False

        thermal_duty = 0.80  # 80% PWM to keep AFE PCB temperature < 85°C

        for k, t in enumerate(time_steps):
            soc_history[k, :] = socs
            min_soc = np.min(socs)
            spread = np.max(socs) - min_soc

            if spread <= soc_tol and not converged:
                converged_time = t
                converged = True

            step_heat_w = 0.0
            for i in range(self.num_cells):
                if socs[i] > min_soc + soc_tol:
                    v_cell = self.get_ocv(socs[i])
                    i_bleed = (v_cell / self.r_bleed) * thermal_duty
                    socs[i] -= (i_bleed * dt) / self.capacities_c[i]
                    step_heat_w += (v_cell ** 2 / self.r_bleed) * thermal_duty

            power_loss_history[k] = step_heat_w
            cumulative_heat_j += step_heat_w * dt

        return time_steps, soc_history, power_loss_history, cumulative_heat_j, converged_time

    def simulate_active(self, max_time_s=7200, dt=5.0, soc_tol=0.003):
        """
        Simulates Active Pack/Cell-to-Cell Balancing:
        Extracts charge from cells above average SoC and injects into cells below average SoC
        with DC-DC converter efficiency eta = 88%.
        """
        socs = self.initial_socs.copy()
        time_steps = np.arange(0, max_time_s, dt)
        soc_history = np.zeros((len(time_steps), self.num_cells))
        power_loss_history = np.zeros(len(time_steps))
        cumulative_heat_j = 0.0
        converged_time = max_time_s
        converged = False

        for k, t in enumerate(time_steps):
            soc_history[k, :] = socs
            spread = np.max(socs) - np.min(socs)

            if spread <= soc_tol and not converged:
                converged_time = t
                converged = True

            if spread > soc_tol:
                idx_max = int(np.argmax(socs))
                idx_min = int(np.argmin(socs))

                v_donor = self.get_ocv(socs[idx_max])
                v_receiver = self.get_ocv(socs[idx_min])

                # Donor cell discharges at I_active
                i_donor = self.active_current
                p_donor = v_donor * i_donor

                # Receiver cell receives power * efficiency
                p_receiver = p_donor * self.active_eff
                i_receiver = p_receiver / v_receiver

                socs[idx_max] -= (i_donor * dt) / self.capacities_c[idx_max]
                socs[idx_min] += (i_receiver * dt) / self.capacities_c[idx_min]

                p_loss = p_donor * (1.0 - self.active_eff)
                power_loss_history[k] = p_loss
                cumulative_heat_j += p_loss * dt

        return time_steps, soc_history, power_loss_history, cumulative_heat_j, converged_time


class IsolationMonitoringDevice:
    """
    ISO 6469-3 / UN ECE R100 High-Voltage Isolation Monitoring Device (IMD) Model.
    Evaluates positive (R_iso_p) and negative (R_iso_n) insulation resistance between
    HV rails and vehicle LV chassis using an asymmetric switched reference resistor bridge.
    """

    def __init__(self, v_pack=400.0, r_ref=1.0e6):
        self.v_pack = v_pack
        self.r_ref = r_ref  # 1 MOhm known reference test resistor

    def evaluate_isolation(self, r_iso_p_ohm, r_iso_n_ohm):
        """
        Calculates equivalent parallel isolation resistance R_iso and ISO 6469-3 status
        (Warning < 500 Ohm/V, Fault < 100 Ohm/V).
        """
        r_parallel = (r_iso_p_ohm * r_iso_n_ohm) / (r_iso_p_ohm + r_iso_n_ohm)
        ohm_per_volt = min(r_iso_p_ohm, r_iso_n_ohm) / self.v_pack

        if ohm_per_volt < 100.0:
            status = "CRITICAL FAULT (< 100 Ohm/V - Contactor Open Required)"
        elif ohm_per_volt < 500.0:
            status = "WARNING (< 500 Ohm/V - Service Required)"
        else:
            status = "HEALTHY (>= 500 Ohm/V - ISO 6469-3 Compliant)"

        return r_parallel, ohm_per_volt, status


def run_balancing_and_imd_simulation():
    os.makedirs("assets", exist_ok=True)

    # 12S Battery Module with realistic initial SoC imbalance (78% to 90%)
    initial_socs = [0.895, 0.840, 0.815, 0.870, 0.785, 0.855, 0.830, 0.902, 0.805, 0.860, 0.825, 0.880]
    capacities_ah = [2.50, 2.48, 2.52, 2.49, 2.47, 2.51, 2.50, 2.48, 2.51, 2.49, 2.50, 2.50]

    sim = PackBalancingSimulator(
        initial_socs=initial_socs,
        capacities_ah=capacities_ah,
        r_bleed=33.0,
        active_current=1.8,
        active_eff=0.88,
    )

    t_pass, soc_pass, p_pass, heat_pass_j, t_conv_pass = sim.simulate_passive(max_time_s=7200, dt=5.0)
    t_act, soc_act, p_act, heat_act_j, t_conv_act = sim.simulate_active(max_time_s=7200, dt=5.0)

    # --- Plot Comparison ---
    fig, axs = plt.subplots(2, 2, figsize=(14, 9), sharex=False)
    cmap = plt.cm.viridis(np.linspace(0.1, 0.9, len(initial_socs)))

    # 1. Passive Balancing SoC Trajectories
    for i in range(len(initial_socs)):
        axs[0, 0].plot(t_pass / 60.0, soc_pass[:, i] * 100, color=cmap[i], linewidth=1.4)
    axs[0, 0].axvline(t_conv_pass / 60.0, color="crimson", linestyle="--", label=f"Dengeleme Süresi: {t_conv_pass/60:.1f} dk")
    axs[0, 0].set_title(f"Pasif Dengeleme (12S Paket - Hedef SoC: %{soc_pass[-1, 0]*100:.1f})")
    axs[0, 0].set_xlabel("Zaman [Dakika]")
    axs[0, 0].set_ylabel("Hücre SoC [%]")
    axs[0, 0].grid(True, linestyle="--", alpha=0.6)
    axs[0, 0].legend(loc="upper right")

    # 2. Active Balancing SoC Trajectories
    for i in range(len(initial_socs)):
        axs[0, 1].plot(t_act / 60.0, soc_act[:, i] * 100, color=cmap[i], linewidth=1.4)
    axs[0, 1].axvline(t_conv_act / 60.0, color="forestgreen", linestyle="--", label=f"Dengeleme Süresi: {t_conv_act/60:.1f} dk")
    axs[0, 1].set_title(f"Aktif İndüktif Dengeleme (12S Paket - Hedef SoC: %{soc_act[-1, 0]*100:.1f})")
    axs[0, 1].set_xlabel("Zaman [Dakika]")
    axs[0, 1].set_ylabel("Hücre SoC [%]")
    axs[0, 1].grid(True, linestyle="--", alpha=0.6)
    axs[0, 1].legend(loc="upper right")

    # 3. Thermal Dissipation Power Comparison
    axs[1, 0].plot(t_pass / 60.0, p_pass, color="crimson", linewidth=1.8, label=f"Pasif Isı Kaybı (Toplam: {heat_pass_j/3600:.2f} Wh)")
    axs[1, 0].plot(t_act / 60.0, p_act, color="forestgreen", linewidth=1.8, label=f"Aktif Isı Kaybı (Toplam: {heat_act_j/3600:.2f} Wh)")
    axs[1, 0].set_title("BMS Kartı Üzerinde Isıya Dönüşen Güç (Termal Yük)")
    axs[1, 0].set_xlabel("Zaman [Dakika]")
    axs[1, 0].set_ylabel("Atık Isı Gücü [W]")
    axs[1, 0].grid(True, linestyle="--", alpha=0.6)
    axs[1, 0].legend(loc="upper right")

    # 4. Final Cell-by-Cell SoC Bar Comparison
    cell_indices = np.arange(1, len(initial_socs) + 1)
    width = 0.26
    axs[1, 1].bar(cell_indices - width, np.array(initial_socs) * 100, width=width, color="slategray", alpha=0.8, label="Başlangıç SoC")
    axs[1, 1].bar(cell_indices, soc_pass[-1, :] * 100, width=width, color="crimson", alpha=0.85, label="Pasif Sonu SoC")
    axs[1, 1].bar(cell_indices + width, soc_act[-1, :] * 100, width=width, color="forestgreen", alpha=0.85, label="Aktif Sonu SoC")
    axs[1, 1].set_ylim(74, 93)
    axs[1, 1].set_xticks(cell_indices)
    axs[1, 1].set_title("Hücre Bazlı Başlangıç vs. Dengeleme Sonu SoC Karşılaştırması")
    axs[1, 1].set_xlabel("Hücre Numarası (1..12)")
    axs[1, 1].set_ylabel("SoC [%]")
    axs[1, 1].grid(True, linestyle="--", alpha=0.6)
    axs[1, 1].legend(loc="upper right")

    plt.tight_layout()
    output_path = "assets/cell_balancing_comparison.png"
    plt.savefig(output_path, dpi=300)
    plt.close(fig)

    print("=== 12S Batarya Paketi Dengeleme (Pasif vs Aktif) Raporu ===")
    print(f"Başlangıç SoC Farkı (Max - Min): {(max(initial_socs) - min(initial_socs))*100:.2f} %")
    print(f"Pasif Dengeleme Sonu SoC: %{np.mean(soc_pass[-1])*100:.2f} | Süre: {t_conv_pass/60:.1f} dk | Atık Isı: {heat_pass_j:.1f} J ({heat_pass_j/3600:.2f} Wh)")
    print(f"Aktif Dengeleme Sonu SoC: %{np.mean(soc_act[-1])*100:.2f} | Süre: {t_conv_act/60:.1f} dk | Atık Isı: {heat_act_j:.1f} J ({heat_act_j/3600:.2f} Wh)")
    print(f"Aktif Dengeleme ile Korunan Kapasite Kazancı: +{(np.mean(soc_act[-1]) - np.mean(soc_pass[-1]))*100:.2f} % SoC")

    # --- IMD Isolation Test Report ---
    imd = IsolationMonitoringDevice(v_pack=400.0)
    print("\n=== ISO 6469-3 Yüksek Voltaj İzolasyon İzleme (IMD) Analizi ===")
    scenarios = [
        ("Normal Kuru Şasi", 15.0e6, 12.0e6),
        ("Nemli Konektör Sızıntısı", 160.0e3, 950.0e3),
        ("Soğutma Sıvısı Kaçağı (Kritik)", 28.0e3, 800.0e3),
    ]
    for name, rp, rn in scenarios:
        r_eq, opv, status = imd.evaluate_isolation(rp, rn)
        print(f"Senaryo: {name:<28} | R_iso_eq: {r_eq/1e3:7.1f} kOhm | {opv:6.0f} Ohm/V -> {status}")
    print(f"Grafik kaydedildi: '{output_path}'")


if __name__ == "__main__":
    run_balancing_and_imd_simulation()
