import numpy as np
import matplotlib.pyplot as plt

class ThermalPIDController:
    """
    Discrete PID Controller for Battery Active Cooling
    u(k) = Kp * e(k) + Ki * sum(e) * dt + Kd * (e(k) - e(k-1)) / dt
    """
    def __init__(self, Kp, Ki, Kd, dt, target_temp=35.0):
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.dt = dt
        self.target_temp = target_temp
        
        self.integral = 0.0
        self.prev_error = 0.0

    def compute(self, current_temp):
        error = current_temp - self.target_temp  # Error > 0 means too hot, need cooling
        
        # Proportional term
        P = self.Kp * error
        
        # Integral term (with windup protection/clipping)
        self.integral += error * self.dt
        self.integral = np.clip(self.integral, -50.0, 50.0)
        I = self.Ki * self.integral
        
        # Derivative term
        D = self.Kd * (error - self.prev_error) / self.dt
        self.prev_error = error
        
        # Output control action (duty cycle for cooling system [0.0 to 1.0])
        control_output = P + I + D
        return np.clip(control_output, 0.0, 1.0)


class BatteryThermalModel:
    """
    Physical thermal model of a single battery cell.
    C_th * dT_cell/dt = Q_gen - Q_conv - Q_cooling
    Q_gen = I^2 * R0 (Joule Heating) + I * T_cell * dOCV/dT (Entropic heating, simplified)
    Q_conv = h_ambient * (T_cell - T_ambient)
    Q_cooling = u_cooling * h_active * (T_cell - T_coolant)
    """
    def __init__(self, c_th=120.0, r0=0.015, h_ambient=0.1, h_active=2.5, initial_temp=25.0):
        self.c_th = c_th          # Heat capacity of cell (J/K)
        self.r0 = r0              # Ohmic internal resistance (Ohms)
        self.h_ambient = h_ambient # Natural convection coefficient (W/K)
        self.h_active = h_active  # Max active cooling heat transfer coefficient (W/K)
        self.temp = initial_temp  # Cell temperature (deg C)

    def step(self, current, u_cooling, t_ambient=25.0, t_coolant=15.0, dt=1.0):
        # 1. Heat Generation: Joule Heating Q = I^2 * R
        q_gen = (current ** 2) * self.r0
        
        # 2. Convective Heat Transfer to Ambient
        q_conv = self.h_ambient * (self.temp - t_ambient)
        
        # 3. Active Cooling (PID Controlled)
        q_cooling = u_cooling * self.h_active * (self.temp - t_coolant)
        
        # 4. Temperature rate of change
        dT_dt = (q_gen - q_conv - q_cooling) / self.c_th
        self.temp += dT_dt * dt
        
        return self.temp, q_gen, q_cooling


# --- Simulation ---
if __name__ == "__main__":
    dt = 1.0
    time = np.arange(0, 1200, dt) # 20 minutes simulation
    
    # Extreme discharge profile: Constant 45A de-charge
    current_profile = np.ones_like(time) * 45.0 
    
    # Initialize Cell and PID
    cell = BatteryThermalModel(c_th=150.0, r0=0.012, h_ambient=0.08, h_active=3.0, initial_temp=25.0)
    pid = ThermalPIDController(Kp=0.08, Ki=0.002, Kd=0.1, dt=dt, target_temp=35.0)
    
    temps = np.zeros_like(time)
    control_actions = np.zeros_like(time)
    q_gens = np.zeros_like(time)
    q_cools = np.zeros_like(time)
    
    # Uncontrolled baseline simulation (no cooling)
    baseline_cell = BatteryThermalModel(c_th=150.0, r0=0.012, h_ambient=0.08, h_active=3.0, initial_temp=25.0)
    baseline_temps = np.zeros_like(time)
    
    for i in range(len(time)):
        # Run controlled cell
        u = pid.compute(cell.temp)
        temp, q_gen, q_cool = cell.step(current_profile[i], u_cooling=u, dt=dt)
        
        temps[i] = temp
        control_actions[i] = u
        q_gens[i] = q_gen
        q_cools[i] = q_cool
        
        # Run uncontrolled cell
        baseline_temp, _, _ = baseline_cell.step(current_profile[i], u_cooling=0.0, dt=dt)
        baseline_temps[i] = baseline_temp

    # --- Plotting Results ---
    fig, axs = plt.subplots(3, 1, figsize=(10, 10), sharex=True)
    
    # Temperature comparison
    axs[0].plot(time / 60.0, baseline_temps, color='crimson', linestyle='--', linewidth=1.5, label='Kontrolsüz Hücre Sıcaklığı (Soğutma Yok)')
    axs[0].plot(time / 60.0, temps, color='forestgreen', linewidth=2.0, label='PID Kontrollü Hücre Sıcaklığı')
    axs[0].axhline(y=35.0, color='black', linestyle=':', label='Hedef Sıcaklık (35°C)')
    axs[0].set_ylabel('Sıcaklık [°C]')
    axs[0].grid(True, linestyle='--', alpha=0.6)
    axs[0].legend(loc='upper left')
    axs[0].set_title('Batarya Aktif Termal PID Kontrol Simülasyonu')

    # PID Control Output (Cooling effort)
    axs[1].plot(time / 60.0, control_actions * 100.0, color='navy', linewidth=2.0, label='Soğutma Sistemi Görev Oranı (PWM %)')
    axs[1].set_ylabel('Soğutma Çabası [%]')
    axs[1].grid(True, linestyle='--', alpha=0.6)
    axs[1].legend(loc='upper left')

    # Heat Power comparison
    axs[2].plot(time / 60.0, q_gens, color='orangered', linewidth=1.5, label='Üretilen Joule Isısı (I^2 * R0)')
    axs[2].plot(time / 60.0, q_cools, color='deepskyblue', linewidth=1.5, label='Aktif Soğutucuyla Çekilen Isı')
    axs[2].set_ylabel('Termal Güç [W]')
    axs[2].set_xlabel('Zaman [Dakika]')
    axs[2].grid(True, linestyle='--', alpha=0.6)
    axs[2].legend(loc='upper left')

    plt.tight_layout()
    plt.savefig('assets/thermal_pid_control.png', dpi=300)
    
    print("\n--- Termal PID Kontrol Raporu ---")
    print(f"Başlangıç Sıcaklığı: {baseline_temps[0]:.1f} °C")
    print(f"Kontrolsüz Maks Sıcaklık: {baseline_temps[-1]:.2f} °C (TERMAL KAÇAK TEHLİKESİ!)")
    print(f"PID Kontrollü Kararlı Durum Sıcaklığı: {temps[-1]:.2f} °C")
    print(f"Simülasyon Sonu Soğutucu Güç Tüketimi: {control_actions[-1]*100:.1f}% PWM")
    print("---------------------------------")
    print("Simülasyon başarıyla tamamlandı. Grafik 'assets/thermal_pid_control.png' konumuna kaydedildi.")
