import os
import sys
import unittest
import importlib
import numpy as np

# Ensure project root is in path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
sys.path.insert(0, PROJECT_ROOT)

# Dynamic imports for numbered directories
mod1_1rc = importlib.import_module("01_Hucre_Modelleme_ve_Karakterizasyon.cell_model_1RC")
BatteryCell1RC = mod1_1rc.BatteryCell1RC

mod1_2rc = importlib.import_module("01_Hucre_Modelleme_ve_Karakterizasyon.cell_model_2RC_hysteresis")
BatteryCell2RCHysteresis = mod1_2rc.BatteryCell2RCHysteresis

mod2_pre = importlib.import_module("02_Guc_Elektronigi_ve_Donanim.precharge_simulation")
PrechargeSimulation = mod2_pre.PrechargeSimulation

mod2_bal = importlib.import_module("02_Guc_Elektronigi_ve_Donanim.cell_balancing_simulation")
PackBalancingSimulator = mod2_bal.PackBalancingSimulator
IsolationMonitoringDevice = mod2_bal.IsolationMonitoringDevice

mod4_ekf = importlib.import_module("04_Tahmin_Algoritmalari.ekf_soc_estimator")
EKF_SoC_Estimator = mod4_ekf.EKF_SoC_Estimator

mod4_rls = importlib.import_module("04_Tahmin_Algoritmalari.rls_soh_sop_estimator")
RLS_Parameter_And_SoP_Estimator = mod4_rls.RLS_Parameter_And_SoP_Estimator

mod5_pid = importlib.import_module("05_Guvenlik_ve_Termal_Yonetim.thermal_pid_control")
ThermalPIDController = mod5_pid.ThermalPIDController

mod5_eis = importlib.import_module("05_Guvenlik_ve_Termal_Yonetim.eis_nyquist_simulator")
ElectrochemicalImpedanceSimulator = mod5_eis.ElectrochemicalImpedanceSimulator

mod6_can = importlib.import_module("06_Endustriyel_Protokoller_ve_Test.bms_can_simulator")
BMS_CAN_Simulator = mod6_can.BMS_CAN_Simulator

mod6_uds = importlib.import_module("06_Endustriyel_Protokoller_ve_Test.uds_diagnostic_simulator")
BMS_UDS_Server = mod6_uds.BMS_UDS_Server
SID = mod6_uds.SID

mod7_pack = importlib.import_module("07_Tam_Entegre_Batarya_Paketi_Simulasyonu.integrated_bms_pack_sim")
IntegratedBatteryPack96S = mod7_pack.IntegratedBatteryPack96S


class TestModule1CellModels(unittest.TestCase):
    def test_1rc_discharge_voltage_drop(self):
        cell = BatteryCell1RC(R0=0.015, R1=0.025, C1=4500, capacity_ah=5.0, initial_soc=1.0)
        vt_rest, ocv_rest = cell.step(current=0.0, dt=1.0)
        self.assertAlmostEqual(vt_rest, ocv_rest, places=4)

        # 10A discharge should produce an immediate drop > I*R0
        vt_dch, _ = cell.step(current=10.0, dt=1.0)
        self.assertLess(vt_dch, vt_rest - 10.0 * 0.015)

    def test_2rc_hysteresis_and_arrhenius(self):
        cell = BatteryCell2RCHysteresis(capacity_ah=50.0, initial_soc=0.80)
        r0_25c, _, _ = cell.get_resistances(temp_c=25.0, soc=0.80)
        r0_0c, _, _ = cell.get_resistances(temp_c=0.0, soc=0.80)
        # Cold temperature must substantially increase internal resistance
        self.assertGreater(r0_0c, r0_25c * 1.5)


class TestModule2HardwareAndBalancing(unittest.TestCase):
    def test_precharge_95_percent_time(self):
        sim = PrechargeSimulation(v_bat=400.0, c_link=820e-6, r_pre=47.0)
        time, v_cap, _, _, _, _, _, t_95 = sim.run_simulation(0.25)
        self.assertAlmostEqual(t_95, 3.0 * sim.tau, places=4)
        idx_95 = np.argmin(np.abs(time - t_95))
        self.assertGreaterEqual(v_cap[idx_95], 400.0 * 0.94)

    def test_active_balancing_conserves_energy_better_than_passive(self):
        socs = [0.88, 0.82, 0.85]
        caps = [2.5, 2.5, 2.5]
        sim = PackBalancingSimulator(socs, caps, r_bleed=33.0, active_current=1.5, active_eff=0.88)
        _, _, _, heat_pass_j, _ = sim.simulate_passive(max_time_s=3600, dt=5.0)
        _, _, _, heat_act_j, _ = sim.simulate_active(max_time_s=3600, dt=5.0)
        self.assertLess(heat_act_j, heat_pass_j * 0.20)

    def test_iso_6469_imd_evaluation(self):
        imd = IsolationMonitoringDevice(v_pack=400.0)
        _, opv_healthy, status_healthy = imd.evaluate_isolation(15e6, 12e6)
        self.assertIn("HEALTHY", status_healthy)
        self.assertGreaterEqual(opv_healthy, 500.0)

        _, opv_fault, status_fault = imd.evaluate_isolation(30e3, 500e3)
        self.assertIn("CRITICAL FAULT", status_fault)
        self.assertLess(opv_fault, 100.0)


class TestModule4EstimationAlgorithms(unittest.TestCase):
    def test_ekf_soc_convergence(self):
        ekf = EKF_SoC_Estimator(
            R0=0.015, R1=0.025, C1=4500, capacity_ah=5.0,
            Q_cov=np.diag([1e-8, 1e-7]), R_cov=0.02**2,
            x0=[0.0, 0.60], P0=np.diag([1e-4, 0.1])
        )
        soc_true = 0.90
        v_rc_true = 0.0
        tau_true = 0.025 * 4500.0
        for _ in range(300):
            current = 2.0
            dt = 1.0
            alpha = np.exp(-dt / tau_true)
            v_rc_true = v_rc_true * alpha + 0.025 * current * (1.0 - alpha)
            soc_true -= (current * dt) / (5.0 * 3600.0)
            vt_sim = ekf.ocv_func(soc_true) - v_rc_true - current * 0.015
            ekf.predict(current, dt)
            x_est = ekf.update(vt_sim, current)

        self.assertLess(abs(x_est[1, 0] - soc_true), 0.01)

    def test_rls_sop_multi_constraint_bounds(self):
        estimator = RLS_Parameter_And_SoP_Estimator(
            r0_init=0.015, r1_init=0.020, c1_init=3000.0, capacity_ah=5.0
        )
        p_dch_high, p_chg_high, _, _ = estimator.compute_sop(soc=0.85, v_rc=0.0)
        p_dch_low, _, _, _ = estimator.compute_sop(soc=0.08, v_rc=0.0)
        self.assertGreater(p_dch_high, p_dch_low * 2.0)


class TestModule5ThermalAndSafety(unittest.TestCase):
    def test_thermal_pid_anti_windup(self):
        pid = ThermalPIDController(Kp=0.08, Ki=0.002, Kd=0.1, dt=1.0, target_temp=35.0)
        for _ in range(500):
            u = pid.compute(current_temp=70.0)
        self.assertLessEqual(u, 1.0)
        self.assertGreaterEqual(u, 0.0)
        self.assertLessEqual(abs(pid.integral), 50.0)

    def test_eis_impedance_spectrum_properties(self):
        sim = ElectrochemicalImpedanceSimulator(r_ohm=0.012, r_ct=0.015)
        z_hf = sim.compute_impedance([100000.0])[0]
        self.assertAlmostEqual(z_hf.real, 0.012, delta=0.003)


class TestModule6ProtocolsAndUDS(unittest.TestCase):
    def test_can_encode_decode_roundtrip(self):
        can = BMS_CAN_Simulator()
        soc_in, v_in, i_in, fault_in = 84.6, 401.5, -35.2, 0x9003
        payload = can.encode_message(soc_in, v_in, i_in, fault_in)
        self.assertEqual(len(payload), 8)

        soc_out, v_out, i_out, fault_out = can.decode_message(payload)
        self.assertAlmostEqual(soc_out, soc_in, places=1)
        self.assertAlmostEqual(v_out, v_in, places=1)
        self.assertAlmostEqual(i_out, i_in, places=1)
        self.assertEqual(fault_out, fault_in)

    def test_uds_session_and_security_challenge(self):
        server = BMS_UDS_Server()
        resp_dsc = server.process(bytes([SID.DSC, 0x03]))
        self.assertEqual(resp_dsc[0], SID.DSC + 0x40)

        resp_seed = server.process(bytes([SID.SA, 0x01]))
        self.assertEqual(resp_seed[0], SID.SA + 0x40)
        seed = int.from_bytes(resp_seed[2:6], 'big')

        key = (seed ^ 0xBEEF1234) & 0xFFFFFFFF
        resp_key = server.process(bytes([SID.SA, 0x02]) + key.to_bytes(4, 'big'))
        self.assertEqual(resp_key[0], SID.SA + 0x40)
        self.assertTrue(server.unlocked)


class TestModule7IntegratedPack(unittest.TestCase):
    def test_96s_pack_voltage_and_precharge(self):
        pack = IntegratedBatteryPack96S(n_cells=96, seed=7)
        self.assertEqual(pack.v_dclink, 0.0)
        for _ in range(50):
            pack.step_precharge(dt=0.01)
        self.assertTrue(pack.main_pos_closed)
        self.assertGreater(pack.v_dclink, 300.0)


if __name__ == "__main__":
    unittest.main()
