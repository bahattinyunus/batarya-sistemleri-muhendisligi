import numpy as np
import matplotlib.pyplot as plt

class BatteryCell1RC:
    """
    1-RC Thevenin Battery Model
    V_t = OCV(SoC) - I*R0 - V_rc
    dV_rc/dt = -V_rc/(R1*C1) + I/C1
    """
    def __init__(self, R0, R1, C1, capacity_ah):
        self.R0 = R0  # Ohmic resistance
        self.R1 = R1  # Polarization resistance
        self.C1 = C1  # Polarization capacitance
        self.capacity_s = capacity_ah * 3600 # Convert Ah to As (Coulombs)
        self.v_rc = 0.0
        self.soc = 1.0 # Start fully charged

    def ocv_func(self, soc):
        # Simplified OCV-SoC lookup (Linear approximation for example)
        # In real projects, this is a LUT or a polynomial
        return 3.0 + 1.2 * soc

    def step(self, current, dt):
        # Update V_rc using Zero-Order Hold (ZOH) discretization
        # V_rc(k+1) = V_rc(k) * exp(-dt/(R1*C1)) + R1*I(k)*(1 - exp(-dt/(R1*C1)))
        tau = self.R1 * self.C1
        self.v_rc = self.v_rc * np.exp(-dt/tau) + self.R1 * current * (1 - np.exp(-dt/tau))
        
        # Update SoC
        self.soc -= (current * dt) / self.capacity_s
        self.soc = np.clip(self.soc, 0, 1)

        # Calculate Terminal Voltage
        v_t = self.ocv_func(self.soc) - current * self.R0 - self.v_rc
        return v_t

# --- Simulation ---
cell = BatteryCell1RC(R0=0.01, R1=0.02, C1=5000, capacity_ah=5.0)
dt = 1.0 # 1 second steps
time = np.arange(0, 3600, dt)
current_profile = np.ones_like(time) * 2.0 # Constant 2A discharge

voltages = []
socs = []

for i in range(len(time)):
    v = cell.step(current_profile[i], dt)
    voltages.append(v)
    socs.append(cell.soc)

print("Simulation complete. Terminal voltage at end:", voltages[-1])
