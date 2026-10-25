"""
thermal_runaway_propagation.py
===============================
Multi-Cell Pack Thermal Runaway Propagation & Early-Warning Simulation

Physics modelled:
- Each cell: C_th * dT/dt = Q_joule + Q_exo(T) - Q_conv_neighbour - Q_cooling
- Exothermic SEI decomposition (Arrhenius):   Q_sei  = A_sei  * exp(-Ea_sei  / RT) * m_sei  * H_sei
- Exothermic cathode decomposition (>150°C):  Q_cat  = A_cat  * exp(-Ea_cat  / RT) * m_cat  * H_cat
- Thermal coupling between adjacent cells:   Q_ij   = lambda_cell * (T_j - T_i)
- Active liquid-cooling plate:               Q_cool = UA_plate * (T_i - T_coolant)

IMD & FBG early-warning triggers simulated:
- Voltage drop derivative (dV/dt)
- Temperature derivative (dT/dt > threshold)
- Pressure/strain proxy (electrode expansion model)

Run:
    python 05_Guvenlik_ve_Termal_Yonetim/thermal_runaway_propagation.py
"""

import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors


# ---------------------------------------------------------------------------
# Physical constants and material data
# ---------------------------------------------------------------------------
R_GAS = 8.31446          # J/(mol·K)
T0_K  = 298.15           # Reference temperature 25 °C in Kelvin


class CellThermalRunawayModel:
    """
    Lumped single-cell thermal model with exothermic decomposition kinetics.

    State: (temperature [°C], sei_fraction_remaining [0-1], cathode_fraction_remaining [0-1])
    """

    # ------ Arrhenius parameters (NMC 811 literature values) ---------------
    A_SEI   = 1.667e15   # 1/s  pre-exponential factor SEI decomposition
    EA_SEI  = 1.35e5     # J/mol
    H_SEI   = 2.57e5     # J/kg  specific heat of SEI exothermic reaction
    M_SEI   = 0.10       # kg/cell  effective SEI reactive mass (normalised)

    A_CAT   = 2.5e14
    EA_CAT  = 1.40e5
    H_CAT   = 3.30e5     # J/kg
    M_CAT   = 0.20       # kg

    T_SEI_ONSET = 80.0   # °C — SEI decomposition initiates
    T_CAT_ONSET = 150.0  # °C — cathode decomposition initiates
    T_RUNAWAY   = 200.0  # °C — full thermal runaway trigger

    def __init__(self, c_th=800.0, r0=0.012, h_ambient=0.05,
                 ua_plate=2.0, initial_temp=25.0, cell_id=0):
        self.c_th      = c_th           # J/K  cell heat capacity
        self.r0        = r0             # Ohm  internal resistance
        self.h_ambient = h_ambient      # W/K  natural convection
        self.ua_plate  = ua_plate       # W/K  cooling plate UA
        self.temp      = float(initial_temp)
        self.cell_id   = cell_id

        self.sei_frac  = 1.0   # 1.0 = intact SEI
        self.cat_frac  = 1.0   # 1.0 = intact cathode
        self.runaway   = False
        self.runaway_time = np.inf

        # Electrode swelling proxy: cumulative strain (dimensionless)
        self.strain    = 0.0
        self.isc_energy_left = 180000.0  # Joules of electrical energy dumped on runaway

    def q_exothermic(self, dt):
        """Arrhenius SEI + cathode decomposition heat rates [W]."""
        T_k = self.temp + 273.15

        q_sei = 0.0
        if self.temp >= self.T_SEI_ONSET and self.sei_frac > 1e-6:
            k_sei = self.A_SEI * np.exp(-self.EA_SEI / (R_GAS * T_k))
            d_sei = min(self.sei_frac, k_sei * self.sei_frac * dt)
            self.sei_frac = max(0.0, self.sei_frac - d_sei)
            q_sei = (d_sei / dt) * self.M_SEI * self.H_SEI

        q_cat = 0.0
        if self.temp >= self.T_CAT_ONSET and self.cat_frac > 1e-6:
            k_cat = self.A_CAT * np.exp(-self.EA_CAT / (R_GAS * T_k))
            d_cat = min(self.cat_frac, k_cat * self.cat_frac * dt)
            self.cat_frac = max(0.0, self.cat_frac - d_cat)
            q_cat = (d_cat / dt) * self.M_CAT * self.H_CAT

        # Severe internal short circuit (ISC) upon runaway trigger
        q_isc = 0.0
        if self.runaway and self.isc_energy_left > 0.0:
            burn_rate = min(self.isc_energy_left, 5500.0 * dt)
            self.isc_energy_left -= burn_rate
            q_isc = burn_rate / dt

        return q_sei + q_cat + q_isc

    def step(self, current, t_ambient, t_coolant, u_cooling, q_neighbours, dt):
        """Integrate cell temperature by one dt step."""
        q_joule    = (current ** 2) * self.r0
        q_exo      = self.q_exothermic(dt)
        q_conv     = self.h_ambient * (self.temp - t_ambient)
        q_cooling  = u_cooling * self.ua_plate * max(0.0, self.temp - t_coolant)
        q_neigh    = q_neighbours   # Net heat received from adjacent cells

        dT = (q_joule + q_exo - q_conv - q_cooling + q_neigh) / self.c_th
        self.temp += dT * dt

        # Electrode strain proxy: expansion proportional to temperature above ref
        self.strain += max(0.0, (self.temp - 30.0)) * 1e-5 * dt

        if self.temp >= self.T_RUNAWAY and not self.runaway:
            self.runaway = True

        return self.temp


class MultiCellPackSimulator:
    """
    Simulates a linear 8-cell module with nearest-neighbour thermal coupling.
    Cell-0 is artificially triggered (nail penetration / internal short circuit).
    """

    N_CELLS     = 8
    LAMBDA_CELL = 2.4    # W/K thermal conductance between adjacent cells (busbars + contact)
    I_DISCHARGE = 35.0   # A constant discharge during event

    def __init__(self, trigger_power_w=32000.0):
        self.cells = [
            CellThermalRunawayModel(
                c_th=850.0, r0=0.012, h_ambient=0.06,
                ua_plate=2.5, initial_temp=25.0 + np.random.uniform(-0.5, 0.5),
                cell_id=i
            )
            for i in range(self.N_CELLS)
        ]
        self.trigger_power_w = trigger_power_w

    def run(self, total_time=600.0, dt=0.5, t_ambient=35.0, t_coolant=18.0,
            cooling_active=True):
        """
        Run simulation. Returns time array and (n_steps × N_CELLS) temperature matrix.
        """
        steps   = int(total_time / dt)
        time    = np.arange(steps) * dt
        T_hist  = np.zeros((steps, self.N_CELLS))
        V_hist  = np.zeros((steps, self.N_CELLS))  # Voltage proxy (OCV drop)
        S_hist  = np.zeros((steps, self.N_CELLS))  # Strain proxy
        runaway_times = [np.inf] * self.N_CELLS

        def ocv_approx(T, runaway):
            if runaway:
                return 0.0
            return max(0.0, 4.15 - 0.0035 * max(0.0, T - 25.0))

        for k in range(steps):
            t = time[k]

            # Nail penetration / severe external trigger on cell-0 in first 6 seconds
            ext_heat_cell0 = self.trigger_power_w if t < 6.0 else 0.0

            # Compute neighbour heat exchange
            q_neigh = [0.0] * self.N_CELLS
            temps = [c.temp for c in self.cells]
            for i in range(self.N_CELLS):
                if i > 0:
                    q_neigh[i] += self.LAMBDA_CELL * (temps[i-1] - temps[i])
                if i < self.N_CELLS - 1:
                    q_neigh[i] += self.LAMBDA_CELL * (temps[i+1] - temps[i])

            # Cooling duty: PID-like bang-bang on cell temp > 35 °C
            for i, cell in enumerate(self.cells):
                u_cool = 1.0 if (cooling_active and cell.temp > 35.0) else 0.0
                q_ext = ext_heat_cell0 if i == 0 else 0.0

                cell.step(
                    current      = self.I_DISCHARGE,
                    t_ambient    = t_ambient,
                    t_coolant    = t_coolant,
                    u_cooling    = u_cool,
                    q_neighbours = q_neigh[i] + q_ext,
                    dt           = dt
                )

                T_hist[k, i] = cell.temp
                V_hist[k, i] = ocv_approx(cell.temp, cell.runaway)
                S_hist[k, i] = cell.strain

                if cell.runaway and runaway_times[i] == np.inf:
                    runaway_times[i] = t

        return time, T_hist, V_hist, S_hist, runaway_times


# ---------------------------------------------------------------------------
# Early-Warning Feature Extraction
# ---------------------------------------------------------------------------
def compute_early_warning_features(time, T_hist, V_hist, S_hist, dt):
    """
    Returns:
      dT_dt  (n_steps × N_cells)  — temperature derivative
      dV_dt  (n_steps × N_cells)  — voltage derivative
      strain (n_steps × N_cells)  — accumulated strain
    """
    dT_dt = np.gradient(T_hist, dt, axis=0)
    dV_dt = np.gradient(V_hist, dt, axis=0)
    return dT_dt, dV_dt, S_hist


# ---------------------------------------------------------------------------
# Main simulation & plotting
# ---------------------------------------------------------------------------
def run_thermal_runaway_simulation():
    os.makedirs("assets", exist_ok=True)
    np.random.seed(12)

    dt         = 0.5
    total_time = 600.0   # 10 minutes

    # ---- Scenario A: With active liquid cooling ----
    sim_cool = MultiCellPackSimulator(trigger_power_w=32000.0)
    t, T_cool, V_cool, S_cool, rt_cool = sim_cool.run(
        total_time=total_time, dt=dt, cooling_active=True)

    # ---- Scenario B: Cooling failure ----
    sim_nocool = MultiCellPackSimulator(trigger_power_w=32000.0)
    _, T_nocool, _, _, rt_nocool = sim_nocool.run(
        total_time=total_time, dt=dt, cooling_active=False)

    dT_dt_cool, dV_dt_cool, strain_cool = compute_early_warning_features(
        t, T_cool, V_cool, S_cool, dt)

    N = MultiCellPackSimulator.N_CELLS
    cmap = plt.cm.plasma(np.linspace(0.1, 0.95, N))

    fig, axs = plt.subplots(2, 3, figsize=(16, 10))

    # ---- Plot 1: Temperature propagation — cooling active ----
    ax = axs[0, 0]
    for i in range(N):
        ax.plot(t / 60, T_cool[:, i], color=cmap[i], lw=1.6,
                label=f"Hücre {i}")
    ax.axhline(80,  color='orange', ls=':', lw=1.2, label='SEI Başlangıç (80°C)')
    ax.axhline(150, color='red',    ls=':', lw=1.2, label='Katot Bozunma (150°C)')
    ax.axhline(200, color='darkred',ls=':',lw=1.4, label='Termal Kaçak (200°C)')
    ax.set_title('Sıcaklık Yayılımı — Soğutma AKTİF')
    ax.set_xlabel('Zaman [dk]'); ax.set_ylabel('Sıcaklık [°C]')
    ax.legend(fontsize=7, ncol=2, loc='upper right')
    ax.grid(True, ls='--', alpha=0.5)

    # ---- Plot 2: Temperature propagation — no cooling ----
    ax = axs[0, 1]
    for i in range(N):
        ax.plot(t / 60, T_nocool[:, i], color=cmap[i], lw=1.6,
                label=f"Hücre {i}")
    ax.axhline(200, color='darkred', ls=':', lw=1.4, label='Termal Kaçak (200°C)')
    rt_finite = [(i, rt) for i, rt in enumerate(rt_nocool) if rt < np.inf]
    for i, rt in rt_finite:
        ax.axvline(rt / 60, color=cmap[i], ls='--', lw=1.0, alpha=0.8)
    ax.set_title('Sıcaklık Yayılımı — Soğutma KAPALI (Zincirleme Reaksiyon)')
    ax.set_xlabel('Zaman [dk]'); ax.set_ylabel('Sıcaklık [°C]')
    ax.legend(fontsize=7, ncol=2, loc='upper right')
    ax.grid(True, ls='--', alpha=0.5)

    # ---- Plot 3: Thermal runaway cascade timeline bar chart ----
    ax = axs[0, 2]
    rt_vals  = [rt / 60 if rt < np.inf else total_time / 60 for rt in rt_nocool]
    colors_r = ['darkred' if rt < np.inf else 'steelblue' for rt in rt_nocool]
    ax.barh(range(N), rt_vals, color=colors_r, edgecolor='black', height=0.6)
    ax.set_xlabel('Termal Kaçak Zamanı [dk]')
    ax.set_ylabel('Hücre Numarası')
    ax.set_title('Zincirleme Termal Kaçak Yayılım Zaman Çizelgesi')
    ax.set_yticks(range(N))
    ax.set_yticklabels([f'Hücre {i}' for i in range(N)])
    ax.grid(True, axis='x', ls='--', alpha=0.5)

    # ---- Plot 4: dT/dt Early Warning Signal (cooling active scenario) ----
    ax = axs[1, 0]
    for i in range(N):
        ax.plot(t / 60, dT_dt_cool[:, i], color=cmap[i], lw=1.3,
                label=f"Hücre {i}")
    ax.axhline(2.0, color='crimson', ls='--', lw=1.4,
               label='Erken Uyarı Eşiği (dT/dt > 2°C/s)')
    ax.set_title('FBG Erken Uyarı: Sıcaklık Türevi dT/dt')
    ax.set_xlabel('Zaman [dk]'); ax.set_ylabel('dT/dt [°C/s]')
    ax.legend(fontsize=7, ncol=2, loc='upper right')
    ax.set_ylim(-1, 10)
    ax.grid(True, ls='--', alpha=0.5)

    # ---- Plot 5: Voltage derivative dV/dt ----
    ax = axs[1, 1]
    for i in range(N):
        ax.plot(t / 60, dV_dt_cool[:, i] * 1000, color=cmap[i], lw=1.3,
                label=f"Hücre {i}")
    ax.axhline(-0.5, color='crimson', ls='--', lw=1.4,
               label='Erken Uyarı Eşiği (dV/dt < -0.5 mV/s)')
    ax.set_title('Online EIS Proxy: Voltaj Türevi dV/dt')
    ax.set_xlabel('Zaman [dk]'); ax.set_ylabel('dV/dt [mV/s]')
    ax.legend(fontsize=7, ncol=2, loc='lower right')
    ax.set_ylim(-5, 1)
    ax.grid(True, ls='--', alpha=0.5)

    # ---- Plot 6: Electrode strain (FBG swelling proxy) ----
    ax = axs[1, 2]
    for i in range(N):
        ax.plot(t / 60, strain_cool[:, i] * 1e3, color=cmap[i], lw=1.3,
                label=f"Hücre {i}")
    ax.set_title('FBG Strain Sensör: Elektrot Şişme Birikimi')
    ax.set_xlabel('Zaman [dk]'); ax.set_ylabel('Birikimli Strain [×10⁻³]')
    ax.legend(fontsize=7, ncol=2, loc='upper left')
    ax.grid(True, ls='--', alpha=0.5)

    plt.suptitle(
        'Çok-Hücreli Termal Kaçak Yayılım Simülasyonu — Zincirleme Reaksiyon & FBG/EIS Erken Uyarı',
        fontsize=12, fontweight='bold', y=1.01
    )
    plt.tight_layout()
    out = 'assets/thermal_runaway_propagation.png'
    plt.savefig(out, dpi=300, bbox_inches='tight')
    plt.close(fig)

    print("=== Çok-Hücreli Termal Kaçak Yayılım Raporu ===")
    print(f"Tetikleyici Hücre 0 → Termal Kaçak: t = {rt_nocool[0]:.1f} s")
    for i in range(1, N):
        if rt_nocool[i] < np.inf:
            print(f"  Hücre {i} → Termal Kaçak: t = {rt_nocool[i]:.1f} s"
                  f"  (Yayılım gecikmesi: +{rt_nocool[i]-rt_nocool[0]:.1f} s)")
        else:
            print(f"  Hücre {i} → Güvende (Termal Kaçak yok)")
    print(f"\nSoğutma KAPALI: {sum(1 for r in rt_nocool if r<np.inf)}/{N} hücre termal kaçağa girdi.")
    print(f"Soğutma AKTİF:  {sum(1 for r in rt_cool  if r<np.inf)}/{N} hücre termal kaçağa girdi.")
    print(f"Grafik: '{out}'")


if __name__ == "__main__":
    run_thermal_runaway_simulation()
