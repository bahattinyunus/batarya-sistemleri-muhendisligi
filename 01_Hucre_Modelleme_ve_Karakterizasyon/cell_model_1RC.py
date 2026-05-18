import numpy as np
import matplotlib.pyplot as plt

class BatteryCell1RC:
    """
    High-Fidelity 1-RC Thevenin Battery Model
    V_t(t) = OCV(SoC) - I(t)*R0 - V_rc(t)
    dV_rc/dt = -V_rc/(R1*C1) + I/C1
    Discretized using Zero-Order Hold (ZOH) for real-time applications.
    """
    def __init__(self, R0, R1, C1, capacity_ah, initial_soc=1.0):
        self.R0 = R0  # Ohmic internal resistance (Ohms)
        self.R1 = R1  # Polarization resistance (Ohms)
        self.C1 = C1  # Polarization capacitance (Farads)
        self.capacity_s = capacity_ah * 3600.0  # Convert Ah to Ampere-seconds (Coulombs)
        self.v_rc = 0.0  # Transient voltage drop across RC parallel group (Volts)
        self.soc = initial_soc  # State of Charge (0.0 to 1.0)
        
        # 6th-degree polynomial coefficients fitted for a typical NMC Chemistry cell
        # Voc(SoC) = p6*SoC^6 + p5*SoC^5 + ... + p0
        self.ocv_coefs = [
            -18.232,   # p6
            62.915,    # p5
            -82.684,   # p4
            51.341,    # p3
            -15.127,   # p2
            3.0645,    # p1
            3.3210     # p0
        ]

    def ocv_func(self, soc):
        """Calculates Open Circuit Voltage based on NMC polynomial model."""
        soc = np.clip(soc, 0.0, 1.0)
        return np.polyval(self.ocv_coefs, soc)

    def step(self, current, dt):
        """
        Advances the battery model state by one time step.
        current: Discharging current in Amperes (>0 for discharge, <0 for charge)
        dt: Time step in seconds
        """
        # 1. State update: v_rc using Zero-Order Hold (ZOH) analytical solution
        tau = self.R1 * self.C1
        decay_factor = np.exp(-dt / tau)
        self.v_rc = self.v_rc * decay_factor + self.R1 * current * (1.0 - decay_factor)
        
        # 2. State update: SoC using Coulomb Counting
        self.soc -= (current * dt) / self.capacity_s
        self.soc = np.clip(self.soc, 0.0, 1.0)

        # 3. Output equation: calculate terminal voltage
        ocv = self.ocv_func(self.soc)
        v_t = ocv - current * self.R0 - self.v_rc
        return v_t, ocv

# --- Simulation setup ---
if __name__ == "__main__":
    # Instantiate a high-quality 5.0 Ah NMC cell
    cell = BatteryCell1RC(R0=0.015, R1=0.025, C1=4500, capacity_ah=5.0, initial_soc=1.0)
    
    # 1-hour simulation (3600 seconds) with a 1Hz sample rate
    dt = 1.0
    time = np.arange(0, 3600, dt)
    
    # Dynamic Current Profile (DST-like: Dynamic Stress Test)
    # Repeated cycles of high discharge pulse, regenerative charge, and rest
    current_profile = np.zeros_like(time)
    for i in range(len(time)):
        cycle_time = i % 300
        if cycle_time < 50:
            current_profile[i] = 2.0  # Constant discharge
        elif cycle_time < 70:
            current_profile[i] = 10.0  # Pulse discharge
        elif cycle_time < 120:
            current_profile[i] = 0.0  # Rest
        elif cycle_time < 160:
            current_profile[i] = -4.0  # Regen Charge
        elif cycle_time < 200:
            current_profile[i] = 1.0  # Slow discharge
        else:
            current_profile[i] = 0.0  # Rest

    # Allocate arrays for logging results
    voltages = np.zeros_like(time)
    ocvs = np.zeros_like(time)
    socs = np.zeros_like(time)
    v_rcs = np.zeros_like(time)

    # Run loop
    for i in range(len(time)):
        v, ocv = cell.step(current_profile[i], dt)
        voltages[i] = v
        ocvs[i] = ocv
        socs[i] = cell.soc
        v_rcs[i] = cell.v_rc

    # --- Plotting Results ---
    fig, axs = plt.subplots(3, 1, figsize=(10, 10), sharex=True)
    
    # Current plot
    axs[0].plot(time, current_profile, color='darkorange', linewidth=1.5, label='Akım (A)')
    axs[0].set_ylabel('Akım [A]')
    axs[0].grid(True, linestyle='--', alpha=0.6)
    axs[0].legend(loc='upper right')
    axs[0].set_title('Dinamik Hücre Simülasyonu - 1-RC Thevenin Modeli')

    # Voltages plot
    axs[1].plot(time, voltages, color='crimson', linewidth=1.5, label='Terminal Voltajı (Vt)')
    axs[1].plot(time, ocvs, color='navy', linestyle='--', linewidth=1.2, label='Açık Devre Voltajı (OCV)')
    axs[1].set_ylabel('Gerilim [V]')
    axs[1].grid(True, linestyle='--', alpha=0.6)
    axs[1].legend(loc='upper right')

    # SoC and V_rc plot
    axs[2].plot(time, socs * 100.0, color='forestgreen', linewidth=1.5, label='Şarj Durumu (SoC %)')
    axs[2].set_ylabel('SoC [%]')
    axs[2].set_xlabel('Zaman [Saniye]')
    axs[2].grid(True, linestyle='--', alpha=0.6)
    
    # Second y-axis for V_rc
    ax2 = axs[2].twinx()
    ax2.plot(time, v_rcs, color='purple', linewidth=1.0, linestyle='-.', label='Polarizasyon Gerilimi (Vrc)')
    ax2.set_ylabel('Vrc [V]')
    
    # Merge legends for bottom plot
    lines1, labels1 = axs[2].get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    axs[2].legend(lines1 + lines2, labels1 + labels2, loc='upper right')

    plt.tight_layout()
    plt.savefig('assets/simulation_results.png', dpi=300)
    print("Simülasyon başarıyla tamamlandı. Sonuç grafiği 'assets/simulation_results.png' olarak kaydedildi.")
