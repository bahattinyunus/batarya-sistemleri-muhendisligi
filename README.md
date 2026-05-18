# Batarya Sistemleri Mühendisliği (BMS Academy)

<p align="center">
  <img src="assets/header.png" alt="BMS Academy Header Banner" width="100%">
</p>

## 🚀 Proje Hakkında

Bu depo, modern **Batarya Yönetim Sistemleri (BMS)**, **Güç Elektroniği**, **Kestirim Algoritmaları** ve **Batarya Paket Tasarımı** üzerine hazırlanmış; akademik derinliğe sahip ve endüstri standartlarında (ISO 26262, AUTOSAR, MISRA) pratik uygulamalar içeren kapsamlı bir uzmanlık kütüphanesidir. 

Hücrenin elektrokimyasal modellemesinden başlayarak, güç elektroniği donanım tasarımlarına, gerçek zamanlı deterministik gömülü yazılımlara, Extended Kalman Filtreleri ile SoC/SoH kestirimine ve aktif termal PID kontrollerine kadar uzanan uçtan uca bir mühendislik müfredatı sunar.

---

## 📂 Müfredat ve Uygulama Yapısı

Aşağıdaki modüller, bir Batarya Sistem Mühendisinin uzmanlaşması gereken temel disiplinleri temsil eder. Her modül kendi içinde teorik dokümantasyonlar ve yüksek sadakatli (high-fidelity) simülasyon kodları barındırır:

| Modül | Teknik Odak Alanı | Akademik İçerik | Uygulama & Kod İçeriği |
| :--- | :--- | :--- | :--- |
| **[Modül 1](./01_Hucre_Modelleme_ve_Karakterizasyon)** | Hücre Modelleme & Karakterizasyon | LFP, NMC, LTO Karşılaştırmaları, 1-RC (Thevenin) & 2-RC Durum-Uzay Modelleri, OCV-SoC Polinomları | [`cell_model_1RC.py`](./01_Hucre_Modelleme_ve_Karakterizasyon/cell_model_1RC.py): Dynamic Stress Test (DST) ile n-derece OCV hücre simülasyonu. |
| **[Modül 2](./02_Guc_Elektronigi_ve_Donanim)** | Güç Elektroniği & Donanım Tasarımı | AFE SPI Daisy Chain Haberleşmesi, Şönt vs. Hall Akım Sensörleri Hata Analizi, Pasif & Aktif Balans Hesapları | [`precharge_simulation.py`](./02_Guc_Elektronigi_ve_Donanim/precharge_simulation.py): DC-Link ön şarj geçici durum RC simülasyonu ve inrush akım analizi. |
| **[Modül 3](./03_BMS_Yazilim_Mimarisi)** | BMS Gömülü Yazılım Mimarisi | AUTOSAR Katmanlı Mimarisi, RTOS Görev (Task) Zamanlamaları, MISRA C++ Güvenli Kodlama Standartları | [`bms_fsm.cpp`](./03_BMS_Yazilim_Mimarisi/bms_fsm.cpp): C++11 standartlarında, DTC loglama ve hata debounce filtreli deterministik FSM. |
| **[Modül 4](./04_Tahmin_Algoritmalari)** | Kestirim Algoritmaları | Coulomb Counting Drift Analizi, 2D Extended Kalman Filter (EKF) Matematiksel Adımları, RLS ile SoH & SoP | [`ekf_soc_estimator.py`](./04_Tahmin_Algoritmalari/ekf_soc_estimator.py): NumPy matris işlemleri ve Jacobian türevleriyle gürültü filtreleyen EKF SoC takipçisi. |
| **[Modül 5](./05_Guvenlik_ve_Termal_Yonetim)** | Fonksiyonel Güvenlik & Termal | ISO 26262 ASIL-D HARA Analizi, Termal Kaçak (Thermal Runaway) Aşamaları, Steinhart-Hart NTC Modelleme | [`thermal_pid_control.py`](./05_Guvenlik_ve_Termal_Yonetim/thermal_pid_control.py): Hücre Joule ısınmasını aktif PID kontrolcü ile soğutan termal denge simülasyonu. |
| **[Modül 6](./06_Endustriyel_Protokoller_ve_Test)** | Endüstriyel Protokoller & HIL | CAN 2.0B / CAN-FD, DBC Mesaj Paketleme & Sinyal Çözümleme, UDS (ISO 14229), HIL Test ve FIU Altyapısı | [`bms_can_simulator.py`](./06_Endustriyel_Protokoller_ve_Test/bms_can_simulator.py): 8-byte raw CAN paketlerini bit seviyesinde kodlayan (encode) ve çözen (decode) simülasyon. |

---

## 🛠 Kullanılan Teknolojiler ve Kütüphaneler

*   **Modelleme & Matematik:** Python (NumPy, SciPy, Matplotlib), **PyBaMM** (Python Battery Mathematical Modelling).
*   **Gömülü Geliştirme Standartları:** C++11/14, MCAL/HAL Katmanları, FreeRTOS / OSEK OS mimarileri.
*   **Donanım & Tasarım:** Altium Designer, LTspice (Analog Sinyal ve Güç Elektronik Benzetimleri).
*   **Test & Kalibrasyon:** UDS (ISO 14229) protokolleri, Vector CANoe/CANalyzer, dSPACE HIL Sistemleri.

---

## 📈 Simülasyon Çıktıları ve Analizler

Depoda yer alan yüksek doğruluklu simülasyonların ürettiği grafik ve analiz çıktıları aşağıda verilmiştir:

### 1. Hücre Dinamik Tepki Simülasyonu (Modül 1)
Dynamic Stress Test (DST) benzeri dinamik şarj/deşarj akım profili altında hücrenin terminal voltajı ($V_t$), açık devre voltajı ($OCV$) ve polarizasyon kapasitör voltajı ($V_{rc}$) geçici durum tepkileri:
![Hücre Simülasyonu](assets/simulation_results.png)

### 2. Yüksek Voltaj Ön Şarj (Pre-charge) Analizi (Modül 2)
Inverter DC-Link kapasitörlerinin ($820\ \mu\text{F}$) ön şarj taş direnci ($47\ \Omega$) üzerinden şarj edilme eğrisi. Akım sınırlaması ve direnç üzerinde ısıya dönüşen kW seviyesindeki pik güç dağılımı:
![Pre-charge Simülasyonu](assets/precharge_simulation.png)

### 3. Extended Kalman Filter (EKF) ile SoC Kestirimi (Modül 4)
Şiddetli ADC ölçüm gürültüsü ve kasıtlı olarak **%35 hatalı** başlatılan SoC tahmininin EKF aracılığıyla saniyeler içerisinde gerçek değere nasıl yakınsadığı ve gürültüyü nasıl süzdüğü (Coulomb Counting ile karşılaştırmalı):
![EKF SoC Simülasyonu](assets/ekf_soc_estimation.png)

### 4. Aktif Soğutma PID Kontrol Simülasyonu (Modül 5)
Sürekli 45A deşarj altında hücrenin ürettiği Joule ısısının ($I^2 R$), aktif bir PID kontrolcü soğutma fanı debisiyle $35^\circ\text{C}$ hedef sıcaklıkta nasıl dengelendiği ve soğutma çabası:
![Termal PID Simülasyonu](assets/thermal_pid_control.png)

---

## 💻 Kurulum ve Çalıştırma Rehberi

Tüm simülasyonları ve analiz araçlarını yerel bilgisayarınızda çalıştırmak için aşağıdaki adımları takip edebilirsiniz:

1. **Depoyu Klonlayın:**
   ```bash
   git clone https://github.com/arch-yunus/batarya-sistemleri-muhendisligi.git
   cd batarya-sistemleri-muhendisligi
   ```

2. **Gerekli Python Paketlerini Yükleyin:**
   ```bash
   pip install numpy matplotlib
   ```

3. **Simülasyonları Çalıştırın:**
   *   **Modül 1 - Hücre Simülasyonu:**
       ```bash
       python 01_Hucre_Modelleme_ve_Karakterizasyon/cell_model_1RC.py
       ```
   *   **Modül 2 - Ön Şarj Analizi:**
       ```bash
       python 02_Guc_Elektronigi_ve_Donanim/precharge_simulation.py
       ```
   *   **Modül 4 - Kalman Filtresi SoC Tahmini:**
       ```bash
       python 04_Tahmin_Algoritmalari/ekf_soc_estimator.py
       ```
   *   **Modül 5 - Termal PID Kontrolü:**
       ```bash
       python 05_Guvenlik_ve_Termal_Yonetim/thermal_pid_control.py
       ```
   *   **Modül 6 - CAN Haberleşme Simülasyonu:**
       ```bash
       python 06_Endustriyel_Protokoller_ve_Test/bms_can_simulator.py
       ```

---

## ⚖️ Lisans

Bu proje MIT Lisansı ile lisanslanmıştır. Detaylar için [`LICENSE`](./LICENSE) dosyasına bakınız.