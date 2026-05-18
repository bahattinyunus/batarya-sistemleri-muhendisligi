import numpy as np
import matplotlib.pyplot as plt

class EKF_SoC_Estimator:
    """
    2D Extended Kalman Filter (EKF) for Battery State of Charge (SoC) Estimation.
    State Vector: x = [V_rc, SoC]^T
    Input: u = Current (A) [Discharge > 0, Charge < 0]
    Measurement: z = Terminal Voltage Vt (V)
    
    Equivalent Circuit: 1-RC Thevenin Model
    """
    def __init__(self, R0, R1, C1, capacity_ah, Q_cov, R_cov, x0, P0):
        self.R0 = R0  # Ohmic internal resistance (Ohms)
        self.R1 = R1  # Polarization resistance (Ohms)
        self.C1 = C1  # Polarization capacitance (Farads)
        self.capacity_s = capacity_ah * 3600.0  # Capacity in Ampere-seconds
        
        # EKF Matrices
        self.x = np.array(x0, dtype=float).reshape(2, 1)  # State vector [V_rc, SoC]^T
        self.P = np.array(P0, dtype=float)                # State covariance matrix (2x2)
        self.Q = np.array(Q_cov, dtype=float)              # Process noise covariance (2x2)
        self.R = float(R_cov)                              # Measurement noise variance (scalar)
        
        # 6th-degree polynomial coefficients for OCV-SoC (NMC cell)
        self.ocv_coefs = [-18.232, 62.915, -82.684, 51.341, -15.127, 3.0645, 3.3210]
        # Derivative coefficients for Jacobian: dOCV/dSoC
        # Voc'(SoC) = 6*p6*SoC^5 + 5*p5*SoC^4 + ... + p1
        self.d_ocv_coefs = [6*self.ocv_coefs[0], 5*self.ocv_coefs[1], 4*self.ocv_coefs[2], 
                            3*self.ocv_coefs[3], 2*self.ocv_coefs[4], self.ocv_coefs[5]]

    def ocv_func(self, soc):
        """Calculates Open Circuit Voltage."""
        return np.polyval(self.ocv_coefs, soc)

    def ocv_derivative(self, soc):
        """Calculates the derivative of OCV with respect to SoC: dOCV/dSoC."""
        return np.polyval(self.d_ocv_coefs, soc)

    def predict(self, current, dt):
        """
        Prediction Step (Time Update)
        x_k^- = A * x_{k-1} + B * u_{k-1}
        P_k^- = A * P_{k-1} * A^T + Q
        """
        tau = self.R1 * self.C1
        a11 = np.exp(-dt / tau)
        
        # Durum geçiş matrisi A
        A = np.array([
            [a11, 0.0],
            [0.0, 1.0]
        ])
        
        # Giriş kontrol matrisi B
        b1 = self.R1 * (1.0 - a11)
        b2 = -dt / self.capacity_s
        B = np.array([
            [b1],
            [b2]
        ])
        
        # State and Covariance prediction
        self.x = np.dot(A, self.x) + B * current
        self.x[1, 0] = np.clip(self.x[1, 0], 0.0, 1.0) # Clip SoC between 0 and 1
        
        self.P = np.dot(np.dot(A, self.P), A.T) + self.Q
        return self.x

    def update(self, measured_voltage, current):
        """
        Correction Step (Measurement Update)
        K = P^- * H^T * (H * P^- * H^T + R)^-1
        x^+ = x^- + K * (z - h(x^-, u))
        P^+ = (I - K * H) * P^-
        """
        v_rc = self.x[0, 0]
        soc = self.x[1, 0]
        
        # 1. Calculate h(x, u) - estimated terminal voltage
        ocv = self.ocv_func(soc)
        estimated_voltage = ocv - v_rc - current * self.R0
        
        # 2. Compute Measurement Jacobian H = [-1, dOCV/dSoC]
        d_ocv = self.ocv_derivative(soc)
        H = np.array([[-1.0, d_ocv]])
        
        # 3. Kalman Gain
        S = np.dot(np.dot(H, self.P), H.T) + self.R
        K = np.dot(self.P, H.T) / S
        
        # 4. State Update (Innovation correction)
        innovation = measured_voltage - estimated_voltage
        self.x = self.x + K * innovation
        self.x[1, 0] = np.clip(self.x[1, 0], 0.0, 1.0)
        
        # 5. Covariance Update
        I = np.eye(2)
        self.P = np.dot(I - np.dot(K, H), self.P)
        
        return self.x

# --- Simulation to verify EKF performance ---
if __name__ == "__main__":
    np.random.seed(42)  # For reproducible noise
    
    # 1. Physical Cell Specifications (True Cell)
    R0_true = 0.015
    R1_true = 0.025
    C1_true = 4500.0
    capacity_ah = 5.0
    capacity_s = capacity_ah * 3600.0
    
    # OCV function coefficients
    ocv_coefs = [-18.232, 62.915, -82.684, 51.341, -15.127, 3.0645, 3.3210]
    
    # 2. Generate True Battery States and Sensor Measurements (DST-like discharge)
    dt = 1.0
    time = np.arange(0, 4000, dt)
    current_profile = np.zeros_like(time)
    for i in range(len(time)):
        cycle = i % 400
        if cycle < 100: current_profile[i] = 3.0  # Discharge
        elif cycle < 150: current_profile[i] = 12.0 # High pulse discharge
        elif cycle < 250: current_profile[i] = 0.0  # Rest
        elif cycle < 320: current_profile[i] = -4.0 # Regen Charge
        else: current_profile[i] = 0.0             # Rest
        
    true_soc = np.zeros_like(time)
    true_vrc = np.zeros_like(time)
    true_vt = np.zeros_like(time)
    
    # Run physical cell simulation
    soc_temp = 1.0
    vrc_temp = 0.0
    tau_true = R1_true * C1_true
    decay = np.exp(-dt / tau_true)
    
    for i in range(len(time)):
        vrc_temp = vrc_temp * decay + R1_true * current_profile[i] * (1 - decay)
        soc_temp -= (current_profile[i] * dt) / capacity_s
        ocv = np.polyval(ocv_coefs, soc_temp)
        
        true_soc[i] = soc_temp
        true_vrc[i] = vrc_temp
        true_vt[i] = ocv - vrc_temp - current_profile[i] * R0_true
        
    # Add severe measurement noise to Voltage and current
    voltage_noise_std = 0.02  # 20 mV noise
    measured_voltage = true_vt + np.random.normal(0, voltage_noise_std, size=len(time))
    
    # 3. EKF Filter Configuration
    # Q: Process noise covariance (trust in model)
    Q = np.array([
        [1e-8, 0.0],
        [0.0, 1e-7]
    ])
    # R: Measurement noise variance
    R = voltage_noise_std ** 2
    
    # Initial state estimates (Deliberately wrong starting SoC to test convergence!)
    # True starting SoC = 1.0, EKF starting SoC = 0.65 (35% error!)
    x0 = [0.0, 0.65] 
    P0 = np.array([
        [1e-4, 0.0],
        [0.0, 0.1]  # High uncertainty in initial SoC
    ])
    
    ekf = EKF_SoC_Estimator(R0_true, R1_true, C1_true, capacity_ah, Q, R, x0, P0)
    
    # 4. Coulomb Counter Setup (with the same starting error)
    cc_soc = np.zeros_like(time)
    cc_soc[0] = 0.65
    
    ekf_soc_est = np.zeros_like(time)
    ekf_vrc_est = np.zeros_like(time)
    
    # 5. Run Estimator Loop
    for i in range(len(time)):
        # EKF Prediction
        ekf.predict(current_profile[i], dt)
        # EKF Correction
        x_est = ekf.update(measured_voltage[i], current_profile[i])
        
        ekf_soc_est[i] = x_est[1, 0]
        ekf_vrc_est[i] = x_est[0, 0]
        
        # Simple Coulomb Counter (Cannot correct starting error!)
        if i > 0:
            cc_soc[i] = cc_soc[i-1] - (current_profile[i] * dt) / capacity_s
            
    # --- Plotting EKF Performance vs Coulomb Counting ---
    fig, axs = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    
    # Terminal Voltage plot
    axs[0].plot(time, true_vt, color='black', linewidth=1.5, label='Gerçek Voltaj (Vt)')
    axs[0].scatter(time[::10], measured_voltage[::10], color='crimson', s=4, alpha=0.5, label='Gürültülü Ölçüm (ADC)')
    axs[0].set_ylabel('Gerilim [V]')
    axs[0].grid(True, linestyle='--', alpha=0.6)
    axs[0].legend(loc='upper right')
    axs[0].set_title('EKF SoC Kestirim Algoritması Performansı')

    # SoC Convergence plot
    axs[1].plot(time, true_soc * 100.0, color='black', linewidth=2.0, label='Gerçek SoC')
    axs[1].plot(time, cc_soc * 100.0, color='darkorange', linewidth=1.5, linestyle='--', label='Basit Coulomb Counting (%35 Hata ile)')
    axs[1].plot(time, ekf_soc_est * 100.0, color='forestgreen', linewidth=2.0, label='EKF SoC Tahmini (Yakınsama)')
    axs[1].set_ylabel('SoC [%]')
    axs[1].set_xlabel('Zaman [Saniye]')
    axs[1].grid(True, linestyle='--', alpha=0.6)
    axs[1].legend(loc='lower right')
    
    plt.tight_layout()
    plt.savefig('assets/ekf_soc_estimation.png', dpi=300)
    
    print("\n--- EKF Simülasyon Raporu ---")
    print(f"Gerçek Başlangıç SoC: 100.0%")
    print(f"Kestirim Başlangıç SoC: 65.0% (Kasıtlı Hata)")
    print(f"Simülasyon Sonu EKF SoC Hatası: {abs(ekf_soc_est[-1] - true_soc[-1])*100:.3f}%")
    print(f"Simülasyon Sonu Coulomb Counting Hatası: {abs(cc_soc[-1] - true_soc[-1])*100:.3f}%")
    print("------------------------------")
    print("Simülasyon başarıyla tamamlandı. Grafik 'assets/ekf_soc_estimation.png' konumuna kaydedildi.")
