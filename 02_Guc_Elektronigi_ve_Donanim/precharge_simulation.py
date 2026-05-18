import numpy as np
import matplotlib.pyplot as plt

class PrechargeSimulation:
    """
    High Voltage Pre-charge Circuit Simulation
    Models the transient behavior of charging DC-link capacitors in EV inverters.
    Formula:
    V_c(t) = V_bat * (1 - exp(-t / tau))
    I_pre(t) = (V_bat / R_total) * exp(-t / tau)
    tau = R_total * C_link
    """
    def __init__(self, v_bat, c_link, r_pre, r_wire=1.0):
        self.v_bat = v_bat      # Battery pack total voltage (V)
        self.c_link = c_link    # DC-Link capacitance (Farads)
        self.r_pre = r_pre      # Pre-charge resistor value (Ohms)
        self.r_wire = r_wire    # Wiring and internal resistance (Ohms)
        
        self.r_total = self.r_pre + self.r_wire
        self.tau = self.r_total * self.c_link  # RC Time Constant (seconds)

    def run_simulation(self, duration_s, dt=0.001):
        """Simulates voltage and current curves over time."""
        time = np.arange(0, duration_s, dt)
        
        # Transient equations
        v_cap = self.v_bat * (1.0 - np.exp(-time / self.tau))
        current = (self.v_bat / self.r_total) * np.exp(-time / self.tau)
        
        # Power dissipation on pre-charge resistor: P = I^2 * R_pre
        p_resistor = (current ** 2) * self.r_pre
        
        # Calculate theoretical values
        peak_current = self.v_bat / self.r_total
        peak_power = (peak_current ** 2) * self.r_pre
        total_energy_j = 0.5 * self.c_link * (self.v_bat ** 2)
        
        # Find 95% charge time (t = 3 * tau)
        t_95 = 3.0 * self.tau
        
        return time, v_cap, current, p_resistor, peak_current, peak_power, total_energy_j, t_95

if __name__ == "__main__":
    # EVs typically run on 400V or 800V architectures. Let's model a 400V pack.
    v_bat = 400.0        # 400 Volts
    c_link = 820e-6      # 820 uF DC-Link Capacitor
    r_pre = 47.0         # 47 Ohm high-power stone resistor
    
    sim = PrechargeSimulation(v_bat, c_link, r_pre)
    
    # Run sim for 0.25 seconds (250 ms)
    time, v_cap, current, p_resistor, peak_curr, peak_pow, energy, t_95 = sim.run_simulation(0.25)
    
    print("--- Ön Şarj Simülasyon Raporu ---")
    print(f"Batarya Gerilimi: {v_bat:.1f} V")
    print(f"DC-Link Kapasitesi: {c_link*1e6:.1f} uF")
    print(f"Ön Şarj Direnci: {r_pre:.1f} Ohm (Toplam Seri Direnç: {sim.r_total:.1f} Ohm)")
    print(f"Zaman Sabiti (Tau): {sim.tau*1000:.2f} ms")
    print(f"Teorik Pik Akım: {peak_curr:.2f} A")
    print(f"Direnç Üzerindeki Pik Güç: {peak_pow/1000:.2f} kW")
    print(f"Kapasitörde Depolanan Enerji: {energy:.2f} Joules")
    print(f"%95 Şarj Seviyesine Ulaşma Süresi (3*Tau): {t_95*1000:.2f} ms")
    print("---------------------------------")
    
    # --- Plotting Transient Curves ---
    fig, axs = plt.subplots(3, 1, figsize=(10, 10), sharex=True)
    
    # Voltage Curve
    axs[0].plot(time * 1000, v_cap, color='crimson', linewidth=2, label='DC-Link Voltajı (V_cap)')
    axs[0].axhline(y=v_bat, color='black', linestyle='--', linewidth=1.0, label='Batarya Voltajı')
    axs[0].axvline(x=t_95 * 1000, color='blue', linestyle=':', label='t_95 (%95 Voltaj)')
    axs[0].set_ylabel('Gerilim [V]')
    axs[0].grid(True, linestyle='--', alpha=0.6)
    axs[0].legend(loc='lower right')
    axs[0].set_title('Yüksek Voltaj Ön Şarj (Pre-charge) Geçici Durum Cevabı')

    # Current Curve
    axs[1].plot(time * 1000, current, color='navy', linewidth=2, label='Ön Şarj Akımı (I_pre)')
    axs[1].axvline(x=t_95 * 1000, color='blue', linestyle=':')
    axs[1].set_ylabel('Akım [A]')
    axs[1].grid(True, linestyle='--', alpha=0.6)
    axs[1].legend(loc='upper right')

    # Resistor Power Dissipation
    axs[2].plot(time * 1000, p_resistor / 1000.0, color='darkorange', linewidth=2, label='Direnç Güç Tüketimi (kW)')
    axs[2].axvline(x=t_95 * 1000, color='blue', linestyle=':')
    axs[2].set_ylabel('Güç [kW]')
    axs[2].set_xlabel('Zaman [Milisaniye]')
    axs[2].grid(True, linestyle='--', alpha=0.6)
    axs[2].legend(loc='upper right')

    plt.tight_layout()
    plt.savefig('assets/precharge_simulation.png', dpi=300)
    print("Simülasyon tamamlandı. Grafik 'assets/precharge_simulation.png' konumuna kaydedildi.")
