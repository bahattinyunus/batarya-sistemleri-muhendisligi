import numpy as np

class EKF_SoC_Estimator:
    """
    Extended Kalman Filter for SoC Estimation
    Simplified version using a linear OCV model for demonstration
    """
    def __init__(self, x0, P0, Q, R):
        self.x = x0 # State vector [SoC]
        self.P = P0 # State covariance
        self.Q = Q  # Process noise covariance
        self.R = R  # Measurement noise covariance

    def predict(self, current, dt, capacity_ah):
        # SoC Prediction: x(k+1) = x(k) - I*dt / Cap
        # Transition matrix F = 1
        F = 1.0
        B = -dt / (capacity_ah * 3600)
        
        self.x = F * self.x + B * current
        self.P = F * self.P * F + self.Q
        return self.x

    def update(self, measured_voltage, current, R0):
        # Measurement: V = OCV(SoC) - I*R0
        # h(x) = OCV(x) - I*R0
        # H = dh/dx (Jacobian of OCV function)
        
        # Assume OCV = 3.0 + 1.2 * SoC -> dh/dx = 1.2
        H = 1.2
        
        y = measured_voltage - (3.0 + 1.2 * self.x - current * R0) # Innovation
        S = H * self.P * H + self.R
        K = self.P * H / S # Kalman Gain
        
        self.x = self.x + K * y
        self.P = (1 - K * H) * self.P
        return self.x

# --- Example Usage ---
estimator = EKF_SoC_Estimator(x0=0.8, P0=0.01, Q=1e-6, R=0.01)
soc_est = estimator.predict(current=2.0, dt=1.0, capacity_ah=5.0)
soc_est = estimator.update(measured_voltage=3.9, current=2.0, R0=0.01)

print("Estimated SoC:", soc_est)
