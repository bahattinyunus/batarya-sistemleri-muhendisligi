import os
import numpy as np
import matplotlib.pyplot as plt


class ElectrochemicalImpedanceSimulator:
    """
    High-Fidelity Electrochemical Impedance Spectroscopy (EIS) Simulator.
    Models battery cell impedance across frequency spectrum (10 mHz to 100 kHz)
    using an extended Randles circuit with Constant Phase Elements (CPE)
    and Warburg diffusion:

        Z(w) = R_ohm + Z_sei(w) + Z_ct_dl(w) + Z_diff(w) + j*w*L_cable

    Where:
        Z_sei(w)   = R_sei / (1 + (j*w*R_sei*C_sei)^alpha_sei)
        Z_diff(w)  = sigma_w * (1 - j) / sqrt(w)  (Warburg mass diffusion)
        Z_ct_dl(w) = (R_ct + Z_diff) / (1 + (j*w*(R_ct + Z_diff)*C_dl)^alpha_dl)
        L_cable    = High-frequency inductive tail from cell tabs and cables
    """

    def __init__(
        self,
        name="Fresh Cell",
        r_ohm=0.012,       # Ohmic internal resistance (Ohms)
        r_sei=0.008,       # SEI layer resistance (Ohms)
        c_sei=1.5,         # SEI layer capacitance (Farads)
        alpha_sei=0.88,    # SEI CPE ideality factor (0 < alpha <= 1)
        r_ct=0.015,        # Charge transfer resistance (Ohms)
        c_dl=25.0,         # Double-layer capacitance (Farads)
        alpha_dl=0.85,     # Double-layer CPE factor
        sigma_w=0.004,     # Warburg coefficient (Ohm * s^0.5)
        l_cable=1.5e-7,    # High frequency inductance (Henries)
    ):
        self.name = name
        self.r_ohm = r_ohm
        self.r_sei = r_sei
        self.c_sei = c_sei
        self.alpha_sei = alpha_sei
        self.r_ct = r_ct
        self.c_dl = c_dl
        self.alpha_dl = alpha_dl
        self.sigma_w = sigma_w
        self.l_cable = l_cable

    def compute_impedance(self, frequencies):
        """
        Calculates complex impedance Z(j*omega) across array of frequencies (Hz).
        """
        w = 2.0 * np.pi * np.asarray(frequencies, dtype=float)
        jw = 1j * w

        # 1. Cable & tab high-frequency parasitic inductance
        z_ind = jw * self.l_cable

        # 2. Ohmic bulk resistance
        z_ohm = self.r_ohm

        # 3. SEI layer impedance (high-to-medium frequency semicircle)
        # CPE admittance: Y_cpe = C * (jw)^alpha
        y_cpe_sei = self.c_sei * (jw ** self.alpha_sei)
        z_sei = self.r_sei / (1.0 + self.r_sei * y_cpe_sei)

        # 4. Semi-infinite Warburg diffusion impedance (low frequency 45-degree tail)
        # Z_w = sigma_w * (1 - 1j) / sqrt(w)
        z_w = self.sigma_w * (1.0 - 1j) / np.sqrt(np.maximum(w, 1e-12))

        # 5. Charge transfer & double-layer CPE (medium-to-low frequency semicircle)
        y_cpe_dl = self.c_dl * (jw ** self.alpha_dl)
        z_faradaic = self.r_ct + z_w
        z_ct_dl = z_faradaic / (1.0 + z_faradaic * y_cpe_dl)

        # Total battery impedance
        z_total = z_ind + z_ohm + z_sei + z_ct_dl
        return z_total


def run_eis_analysis_and_plot():
    os.makedirs("assets", exist_ok=True)

    # Frequency grid: 10 mHz (0.01 Hz) to 100 kHz (100,000 Hz)
    frequencies = np.logspace(-2, 5, 400)

    # Define 3 representative battery degradation states:
    # 1. Fresh Cell (BOL - Beginning of Life)
    fresh_cell = ElectrochemicalImpedanceSimulator(
        name="Yeni Hücre (BOL - %100 SoH)",
        r_ohm=0.012, r_sei=0.007, c_sei=2.0, alpha_sei=0.88,
        r_ct=0.014, c_dl=30.0, alpha_dl=0.86, sigma_w=0.0035, l_cable=1.2e-7
    )

    # 2. Aged Cell (Cycle aged, thickened SEI, depleted electrolyte)
    aged_cell = ElectrochemicalImpedanceSimulator(
        name="Yaşlanmış Hücre (%78 SoH - SEI Büyümesi)",
        r_ohm=0.024, r_sei=0.022, c_sei=1.1, alpha_sei=0.82,
        r_ct=0.038, c_dl=18.0, alpha_dl=0.79, sigma_w=0.0090, l_cable=1.2e-7
    )

    # 3. Lithium Plated Cell (Cold Fast-Charging induced dendrite anomaly)
    plated_cell = ElectrochemicalImpedanceSimulator(
        name="Lityum Dendrit / Plating Anomalisi (Soğuk Hızlı Şarj)",
        r_ohm=0.019, r_sei=0.036, c_sei=0.7, alpha_sei=0.75,
        r_ct=0.052, c_dl=12.0, alpha_dl=0.72, sigma_w=0.0150, l_cable=1.2e-7
    )

    cells = [fresh_cell, aged_cell, plated_cell]
    colors = ["forestgreen", "darkorange", "crimson"]

    # Compute impedances
    z_dict = {}
    for cell in cells:
        z_dict[cell.name] = cell.compute_impedance(frequencies)

    # --- Plotting ---
    fig = plt.figure(figsize=(15, 10))

    # 1. Nyquist Plot (-Im(Z) vs Re(Z))
    ax_nyquist = fig.add_subplot(2, 2, (1, 3))
    for cell, color in zip(cells, colors):
        z = z_dict[cell.name]
        re_mohm = z.real * 1000.0
        im_mohm = -z.imag * 1000.0
        ax_nyquist.plot(re_mohm, im_mohm, color=color, linewidth=2.0, label=cell.name)

        # Highlight characteristic frequencies (100 Hz, 10 Hz, 1 Hz, 0.1 Hz)
        sample_freqs = [1000.0, 100.0, 10.0, 1.0, 0.1]
        for sf in sample_freqs:
            idx = np.argmin(np.abs(frequencies - sf))
            ax_nyquist.scatter(re_mohm[idx], im_mohm[idx], color=color, s=28, zorder=5)
            if cell == fresh_cell:
                ax_nyquist.annotate(f"{sf}Hz", (re_mohm[idx], im_mohm[idx]),
                                   textcoords="offset points", xytext=(0, 7),
                                   fontsize=7.5, ha='center', color='black')

    ax_nyquist.set_title("Elektrokimyasal Empedans Spektroskopisi (EIS) - Nyquist Diyagramı", fontsize=11, fontweight='bold')
    ax_nyquist.set_xlabel("Reel Empedans Re(Z) [mΩ]", fontsize=10)
    ax_nyquist.set_ylabel("Negatif İmajiner Empedans -Im(Z) [mΩ]", fontsize=10)
    ax_nyquist.grid(True, linestyle="--", alpha=0.6)
    ax_nyquist.legend(loc="upper left", fontsize=9)
    ax_nyquist.set_aspect('equal', adjustable='datalim')

    # Add explanatory annotations on Nyquist diagram
    ax_nyquist.axhline(0, color='gray', linestyle=':', linewidth=0.8)
    ax_nyquist.annotate('Ohmik Direnç (R0)\n(Yüksek Frekans Kesişimi)',
                       xy=(fresh_cell.r_ohm * 1000.0, 0), xytext=(8, -12),
                       arrowprops=dict(arrowstyle="->", color="black"), fontsize=8)

    # 2. Bode Magnitude Plot (|Z| vs Frequency)
    ax_bode_mag = fig.add_subplot(2, 2, 2)
    for cell, color in zip(cells, colors):
        z = z_dict[cell.name]
        mag_mohm = np.abs(z) * 1000.0
        ax_bode_mag.loglog(frequencies, mag_mohm, color=color, linewidth=1.8, label=cell.name)

    ax_bode_mag.set_title("Bode Diyagramı - Empedans Genliği |Z|", fontsize=10, fontweight='bold')
    ax_bode_mag.set_xlabel("Frekans [Hz]", fontsize=9)
    ax_bode_mag.set_ylabel("|Z| [mΩ]", fontsize=9)
    ax_bode_mag.grid(True, which="both", linestyle="--", alpha=0.5)
    ax_bode_mag.legend(loc="upper right", fontsize=7.5)

    # 3. Bode Phase Plot (Phase vs Frequency)
    ax_bode_phase = fig.add_subplot(2, 2, 4)
    for cell, color in zip(cells, colors):
        z = z_dict[cell.name]
        phase_deg = np.angle(z, deg=True)
        ax_bode_phase.semilogx(frequencies, phase_deg, color=color, linewidth=1.8, label=cell.name)

    ax_bode_phase.set_title("Bode Diyagramı - Faz Açısı θ", fontsize=10, fontweight='bold')
    ax_bode_phase.set_xlabel("Frekans [Hz]", fontsize=9)
    ax_bode_phase.set_ylabel("Faz Açısı [Derece]", fontsize=9)
    ax_bode_phase.grid(True, which="both", linestyle="--", alpha=0.5)
    ax_bode_phase.legend(loc="lower left", fontsize=7.5)

    plt.tight_layout()
    output_path = "assets/eis_nyquist_bode.png"
    plt.savefig(output_path, dpi=300)
    plt.close(fig)

    print("=== Elektrokimyasal Empedans Spektroskopisi (EIS) Raporu ===")
    print(f"Frekans Aralığı: {frequencies[0]:.2f} Hz -> {frequencies[-1]/1e3:.1f} kHz")
    for cell in cells:
        z = z_dict[cell.name]
        r0_intercept = z.real[np.argmin(np.abs(z.imag))] * 1000.0
        z_max_imag = -np.min(z.imag) * 1000.0
        print(f"[{cell.name}]")
        print(f"  -> R0 (HF Kesişimi): {r0_intercept:.2f} mOhm")
        print(f"  -> Maks. Yarım Daire Tepe Yüksekliği: {z_max_imag:.2f} mOhm")
        print(f"  -> 1 kHz Empedans Genliği: {np.abs(cell.compute_impedance(1000.0))*1000.0:.2f} mOhm")
    print(f"Grafik başarıyla kaydedildi: '{output_path}'")


if __name__ == "__main__":
    run_eis_analysis_and_plot()
