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
| **[Modül 1](./01_Hucre_Modelleme_ve_Karakterizasyon)** | Hücre Modelleme & Karakterizasyon | LFP, NMC, LTO Karşılaştırmaları, 1-RC (Thevenin) & 2-RC Durum-Uzay Modelleri, OCV-SoC Polinomları | [`cell_model_1RC.py`](./01_Hucre_Modelleme_ve_Karakterizasyon/cell_model_1RC.py): Dynamic Stress Test (DST) ile n-derece OCV hücre simülasyonu.<br>[`cell_model_2RC_hysteresis.py`](./01_Hucre_Modelleme_ve_Karakterizasyon/cell_model_2RC_hysteresis.py): 2-RC, LFP düz plato OCV, Plett histerezis, Arrhenius sıcaklık etkisi ve HPPC. |
| **[Modül 2](./02_Guc_Elektronigi_ve_Donanim)** | Güç Elektroniği & Donanım Tasarımı | AFE SPI Daisy Chain Haberleşmesi, Şönt vs. Hall Akım Sensörleri Hata Analizi, Pasif & Aktif Balans Hesapları | [`precharge_simulation.py`](./02_Guc_Elektronigi_ve_Donanim/precharge_simulation.py): DC-Link ön şarj geçici durum RC simülasyonu ve inrush akım analizi.<br>[`cell_balancing_simulation.py`](./02_Guc_Elektronigi_ve_Donanim/cell_balancing_simulation.py): Pasif vs aktif dengeleme ve ISO 6469-3 IMD izolasyon analizi. |
| **[Modül 3](./03_BMS_Yazilim_Mimarisi)** | BMS Gömülü Yazılım Mimarisi | AUTOSAR Katmanlı Mimarisi, RTOS Görev (Task) Zamanlamaları, MISRA C++ Güvenli Kodlama Standartları | [`bms_fsm.cpp`](./03_BMS_Yazilim_Mimarisi/bms_fsm.cpp): C++11 standartlarında, DTC loglama ve hata debounce filtreli deterministik FSM; PRECHARGE, BALANCING, kontaktör yapışma testi ve NvM freeze-frame içerir. |
| **[Modül 4](./04_Tahmin_Algoritmalari)** | Kestirim Algoritmaları | Coulomb Counting Drift Analizi, 2D Extended Kalman Filter (EKF) Matematiksel Adımları, RLS ile SoH & SoP | [`ekf_soc_estimator.py`](./04_Tahmin_Algoritmalari/ekf_soc_estimator.py): NumPy matris işlemleri ve Jacobian türevleriyle gürültü filtreleyen EKF SoC takipçisi.<br>[`rls_soh_sop_estimator.py`](./04_Tahmin_Algoritmalari/rls_soh_sop_estimator.py): RLS ile R0 kestirimi, SoH ve çok kısıtlı SoP. |
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
        python 01_Hucre_Modelleme_ve_Karakterizasyon/cell_model_2RC_hysteresis.py
       ```
   *   **Modül 2 - Ön Şarj Analizi:**
       ```bash
       python 02_Guc_Elektronigi_ve_Donanim/precharge_simulation.py
        python 02_Guc_Elektronigi_ve_Donanim/cell_balancing_simulation.py
       ```
   *   **Modül 4 - Kalman Filtresi SoC Tahmini:**
       ```bash
       python 04_Tahmin_Algoritmalari/ekf_soc_estimator.py
        python 04_Tahmin_Algoritmalari/rls_soh_sop_estimator.py
       ```
   *   **Modül 5 - Termal PID Kontrolü:**
       ```bash
       python 05_Guvenlik_ve_Termal_Yonetim/thermal_pid_control.py
       ```
   *   **Modül 6 - CAN Haberleşme Simülasyonu:**
       ```bash
       python 06_Endustriyel_Protokoller_ve_Test/bms_can_simulator.py
       ```


### 5. 2-RC + Histerezis, HPPC ve Arrhenius Etkisi (Modül 1)
![HPPC](assets/hppc_2rc_hysteresis.png)

### 6. Pasif vs Aktif Dengeleme (Modül 2)
![Dengeleme](assets/cell_balancing_comparison.png)

### 7. RLS ile SoH ve SoP Kestirimi (Modül 4)
![RLS](assets/rls_soh_sop_estimation.png)

---

## 🔬 İleri Nesil Batarya Teknolojileri ve BMS Trendleri

Geleneksel batarya yönetim sistemleri (BMS), araç üzerindeki gömülü donanımların (MCU/ASIC) sınırlı işlemci ve hafıza kapasitesi nedeniyle basit eşdeğer devre modellerine (ECM) ve Coulomb counting yöntemlerine dayanır. Ancak modern elektrikli araçlar ve şebeke tipi depolama sistemleri (ESS), bataryaların sınırlarını zorlamak ve güvenliği artırmak için yeni nesil teknolojileri entegre etmektedir.

```mermaid
graph TD
    subgraph Bulut Katmanı (Cloud-BMS / Dijital İkiz)
        DFN[Fiziksel DFN Elektrokimyasal Model]
        ML[AI/ML Kestirim: LSTM & Gaussian Process]
        OTA[Parametre Güncelleme - OTA]
    end

    subgraph Hücre İçi Algılama (In-situ Sensing)
        FBG[FBG Optik Fiber Sensörler: Sıcaklık & Şişme Basıncı]
        EIS[Online EIS: Dendrit ve Gaz Algılama]
    end

    subgraph Gömülü Edge Katmanı (Vehicle-AFE/MCU)
        ECM[1-RC Eşdeğer Devre Modeli]
        EKF[Extended Kalman Filter]
    end

    FBG -- "Hassas Gerilme/Sıcaklık" --> ECM
    EIS -- "İç Direnç Spektrumu" --> EKF
    ECM & EKF -- "Telemetri Verileri (4G/5G)" --> DFN & ML
    OTA -- "Güncellenmiş R, C, OCV Matrisleri" --> EKF
```

### 1. Bulut Tabanlı (Cloud-BMS) ve Dijital İkiz (Digital Twin) Mimarisi
Gömülü denetleyicilerin işlem gücü yetersizliğini aşmak için modern elektrikli araçlar, batarya verilerini 4G/5G telemetri üzerinden buluta aktarır. 
*   **Dijital İkiz:** Bulut üzerinde batarya paketinin fiziksel ve kimyasal bazlı yüksek sadakatli bir kopyası çalıştırılır. Burada **Doyle-Fuller-Newman (DFN)** gibi karmaşık elektrokimyasal modeller gerçek zamanlı simüle edilir.
*   **Makine Öğrenimi (AI/ML):** **LSTM (Long Short-Term Memory)** ve **Gaussian Process Regression (GPR)** gibi yapay zeka modelleri, bataryanın geçmiş kullanım profillerini analiz ederek Kalan Faydalı Ömrünü (RUL - Remaining Useful Life) ve yaşlanma trendlerini (SoH) sıfıra yakın hata payı ile kestirir. Bu modellerden elde edilen güncel direnç, kapasite ve termal parametreler Over-The-Air (OTA) güncellemeleriyle araç üzerindeki edge-BMS'e geri beslenir.

### 2. LFP Kimyasındaki OCV "Düz Platolu" (Flat-Curve) Kestirim Zorluğu
Lityum Demir Fosfat (LFP) piller, yüksek çevrim ömürleri ve termal kararlılıkları nedeniyle pazarda baskın hale gelmiştir. Ancak LFP pillerin şarj durumu ($SoC$) tahmininde BMS mühendisleri için ciddi bir zorluk bulunur:
*   **Düz OCV Eğrisi:** LFP pillerin Açık Devre Voltajı ($OCV$), %20 ile %90 SoC aralığında neredeyse tamamen düzdür (yatay plato). 
*   **Duyarlılık Problemi:** Voltmetre veya ADC üzerindeki **1 mV'luk** küçük bir ölçüm hatası veya gürültü, SoC tahmininde **%10 ila %15** arasında sapmalara yol açar.
*   **Çözümler:** Yeni nesil BMS algoritmaları, bu platoda sadece voltaja bakmak yerine **Histerezis modelleriyle entegre adaptif Kalman filtreleri**, **Fisher Bilgi Matrisi tabanlı sensör füzyonu** ve aracın kısa duraklama sürelerindeki gevşeme (relaxation) voltajlarını inceleyen makine öğrenimi tabanlı SoC sıfırlama (recalibration) yöntemlerini kullanır.

### 3. Sodyum-İyon (Na-Ion) Batarya Yönetimi
Lityuma alternatif olarak hızla ticarileşen Sodyum-İyon (Na-Ion) piller, düşük maliyet, ham madde bolluğu ve olağanüstü soğuk hava performansı sunar. Ancak SIB hücre yapısı BMS algoritmalarında özelleştirme gerektirir:
*   **Kimyasal Davranış Farkı:** Nominal voltajı lityuma göre daha düşüktür (~3.0 V) ve şarj/deşarj esnasında hücre içi direnç değişimi (impedance phase transitions) çok daha dramatiktir.
*   **BMS Adaptasyonu:** Hücrelerin şarj/deşarj ve balans limitleri Sodyum-İyon pilin kimyasal bozunma (failure modes) sınırlarına göre baştan tasarlanır.

### 4. Hücre İçi (In-situ) FBG (Fiber Bragg Grating) Optik Sensörleri
Geleneksel bataryalarda sıcaklık, hücrelerin dış yüzeyine yapıştırılan NTC/PTC dirençlerle ölçülür. Bu durum, hücre merkezinde oluşan termal kaçak precursor'larını (öncülerini) algılamada saniyelerce gecikmeye yol açar.
*   **FBG Sensörler:** Hücrelerin içerisine üretim esnasında saç teli inceliğinde fiber optik **Fiber Bragg Grating** sensörleri gömülür.
*   ** Strain ve Sıcaklık Ayrımı:** Optik fiber üzerinden gönderilen ışığın kırılma dalga boyu değişimleri analiz edilerek hücre içi lokal sıcaklık dereceleri ve elektrotların şişmesinden (electrode swelling) kaynaklanan mekanik stres/basınç değişimleri milisaniyeler düzeyinde doğrudan ve elektromanyetik parazitlerden (EMI) tamamen bağımsız olarak ölçülür.

### 5. Çevrimiçi (Online / In-situ) Elektrokimyasal Empedans Spektroskopisi (EIS)
EIS, laboratuvar ortamlarında batarya karakterizasyonu için kullanılan frekans taramalı bir empedans ölçüm tekniğidir. Günümüzde bu teknolojiyi araç üzerine entegre etmeye yönelik yoğun AR-GE çalışmaları yürütülmektedir.
*   **Çalışma Prensibi:** BMS, araç çalışırken bataryaya küçük genlikli alternatif akım (AC) sinyalleri enjekte eder ve hücrelerin voltaj faz tepkilerini ölçerek gerçek zamanlı empedans spektrumu (Nyquist Plot) oluşturur.
*   **Erken Hata Tespiti:** EIS sayesinde, anotta oluşan lityum dendriti büyümesi (lithium plating) ve hücre içi gaz salınımları (gas evolution) henüz voltaj ve sıcaklıkta hiçbir değişim yaratmadan mikro seviyede tespit edilir ve termal kaçak başlamadan engellenir.

---

## ⚖️ Lisans

Bu proje MIT Lisansı ile lisanslanmıştır. Detaylar için [`LICENSE`](./LICENSE) dosyasına bakınız.