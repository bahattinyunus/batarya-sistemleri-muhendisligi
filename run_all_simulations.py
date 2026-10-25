import os
import sys
import time
import subprocess

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

SIMULATIONS = [
    {
        "module": "Modül 1: Hücre Modelleme (1-RC DST)",
        "script": "01_Hucre_Modelleme_ve_Karakterizasyon/cell_model_1RC.py",
        "output": "assets/simulation_results.png",
    },
    {
        "module": "Modül 1: Hücre Modelleme (2-RC + LFP Histerezis & HPPC)",
        "script": "01_Hucre_Modelleme_ve_Karakterizasyon/cell_model_2RC_hysteresis.py",
        "output": "assets/hppc_2rc_hysteresis.png",
    },
    {
        "module": "Modül 2: Güç Elektroniği (DC-Link Ön Şarj Analizi)",
        "script": "02_Guc_Elektronigi_ve_Donanim/precharge_simulation.py",
        "output": "assets/precharge_simulation.png",
    },
    {
        "module": "Modül 2: Dengeleme & İzolasyon (Pasif vs Aktif + ISO 6469-3 IMD)",
        "script": "02_Guc_Elektronigi_ve_Donanim/cell_balancing_simulation.py",
        "output": "assets/cell_balancing_comparison.png",
    },
    {
        "module": "Modül 4: Kestirim Algoritmaları (Extended Kalman Filter SoC)",
        "script": "04_Tahmin_Algoritmalari/ekf_soc_estimator.py",
        "output": "assets/ekf_soc_estimation.png",
    },
    {
        "module": "Modül 4: Kestirim Algoritmaları (RLS ile SoH & Çok-Kısıtlı SoP)",
        "script": "04_Tahmin_Algoritmalari/rls_soh_sop_estimator.py",
        "output": "assets/rls_soh_sop_estimation.png",
    },
    {
        "module": "Modül 5: Termal Yönetim (Aktif Sıvı Soğutma PID Kontrol)",
        "script": "05_Guvenlik_ve_Termal_Yonetim/thermal_pid_control.py",
        "output": "assets/thermal_pid_control.png",
    },
    {
        "module": "Modül 5: Fonksiyonel Güvenlik (Çok-Hücreli Termal Kaçak Yayılımı)",
        "script": "05_Guvenlik_ve_Termal_Yonetim/thermal_runaway_propagation.py",
        "output": "assets/thermal_runaway_propagation.png",
    },
    {
        "module": "Modül 5: Elektrokimyasal Teşhis (EIS Nyquist & Bode Analizi)",
        "script": "05_Guvenlik_ve_Termal_Yonetim/eis_nyquist_simulator.py",
        "output": "assets/eis_nyquist_bode.png",
    },
    {
        "module": "Modül 6: Endüstriyel CAN (BMS Little-Endian Paketleyici)",
        "script": "06_Endustriyel_Protokoller_ve_Test/bms_can_simulator.py",
        "output": None,
    },
    {
        "module": "Modül 6: Diyagnostik (ISO 14229 UDS & ISO-TP Simülatörü)",
        "script": "06_Endustriyel_Protokoller_ve_Test/uds_diagnostic_simulator.py",
        "output": None,
    },
    {
        "module": "Modül 7: Capstone (Tam Entegre 96S EV Batarya Paketi Simülasyonu)",
        "script": "07_Tam_Entegre_Batarya_Paketi_Simulasyonu/integrated_bms_pack_sim.py",
        "output": "assets/integrated_pack_simulation.png",
    },
]


def print_banner():
    print("=" * 80)
    print(" ⚡ BATARYA SİSTEMLERİ MÜHENDİSLİĞİ (BMS ACADEMY) ⚡")
    print(" Bütünleşik Simülasyon ve Doğrulama Orkestratörü")
    print("=" * 80)


def run_unit_tests():
    print("\n[ADIM 1/2] Otomatik Birim Testleri Çalıştırılıyor (tests/test_bms_suite.py)...")
    t0 = time.time()
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    res = subprocess.run(
        [sys.executable, "tests/test_bms_suite.py"],
        cwd=SCRIPT_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    dt = time.time() - t0
    if res.returncode == 0:
        print(f"  [OK] Tüm birim testleri başarıyla geçti ({dt:.2f} saniye).")
        return True
    else:
        print(f"  [HATA] Birim testleri başarısız oldu:\n{res.stderr}")
        return False


def run_all_sims():
    print("\n[ADIM 2/2] Müfredat Simülasyonları Sırayla Koşturuluyor...\n")
    success_count = 0
    total_t0 = time.time()

    for idx, sim in enumerate(SIMULATIONS, 1):
        print(f"  ({idx:2d}/{len(SIMULATIONS)}) {sim['module']}")
        script_path = os.path.join(SCRIPT_DIR, sim["script"])

        t0 = time.time()
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        res = subprocess.run(
            [sys.executable, script_path],
            cwd=SCRIPT_DIR,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
        dt = time.time() - t0

        if res.returncode == 0:
            out_note = f" -> Çıktı: {sim['output']}" if sim["output"] else ""
            print(f"       [BAŞARILI] {dt:.2f}s {out_note}")
            success_count += 1
        else:
            print(f"       [HATA] ({dt:.2f}s):\n{res.stderr[:400]}")

    total_dt = time.time() - total_t0
    print("\n" + "=" * 80)
    print(f" ÖZET RAPOR: {success_count}/{len(SIMULATIONS)} simülasyon başarıyla tamamlandı ({total_dt:.1f} sn).")
    print(" Tüm analiz grafikleri 'assets/' klasöründe yüksek çözünürlükte güncellendi.")
    print("=" * 80)


if __name__ == "__main__":
    print_banner()
    if run_unit_tests():
        run_all_sims()
