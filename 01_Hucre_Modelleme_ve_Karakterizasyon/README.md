# Modül 1: Hücre Modelleme ve Karakterizasyon

Bu modül, batarya hücrelerinin elektrokimyasal ve elektriksel davranışlarını matematiksel ifadelere dökerek simüle etme yöntemlerini kapsar. Batarya Yönetim Sistemlerinin (BMS) temelini oluşturan hücre modelleri, gerçek zamanlı tahmin algoritmalarının (SoC, SoH) doğruluğu için kritik bir öneme sahiptir.

---

## 📚 1. Hücre Kimyaları Karşılaştırma Analizi

Farklı batarya kimyaları, elektrokimyasal yapıları gereği farklı nominal voltaj, kararlılık ve ömür kriterlerine sahiptir. BMS tasarımı yapılırken hücre kimyasına göre koruma ve kontrol limitleri belirlenir.

| Hücre Kimyası | Nominal Gerilim (V) | Hücre Çalışma Aralığı (V) | Enerji Yoğunluğu (Wh/kg) | Çevrim Ömrü (Döngü) | Termal Kaçak Başlangıcı (°C) | C-Rate Kapasitesi (Şarj/Deşarj) | Temel Avantajlar / Dezavantajlar |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **NMC** (Nikel Manganez Kobalt) | 3.6 - 3.7 | 2.5 - 4.2 | 150 - 250 | 1,000 - 2,000 | ~210 °C | Orta (1C / 3C) | **(+):** Yüksek enerji yoğunluğu, hafiflik.<br>**(-):** Kobalt kullanımı, termal hassasiyet. |
| **LFP** (Lityum Demir Fosfat) | 3.2 | 2.0 - 3.65 | 90 - 160 | 3,000 - 6,000+ | ~270 °C | Yüksek (1C / 10C) | **(+):** Üstün termal kararlılık, uzun ömür, güvenli.<br>**(-):** Düşük enerji yoğunluğu, düz OCV eğrisi. |
| **LTO** (Lityum Titanat) | 2.4 | 1.5 - 2.8 | 70 - 110 | 10,000 - 20,000+ | ~300+ °C | Çok Yüksek (10C / 30C) | **(+):** Ultra hızlı şarj, ekstrem ömür, soğukta çalışma.<br>**(-):** Çok düşük enerji yoğunluğu, yüksek maliyet. |
| **NCA** (Nikel Kobalt Alüminyum) | 3.6 | 2.5 - 4.2 | 200 - 260 | 1,000 - 1,500 | ~150 °C | Orta (1C / 3C) | **(+):** Çok yüksek enerji yoğunluğu.<br>**(-):** En kararsız kimya, yüksek termal kaçak riski. |
| **Na-Ion** (Sodyum İyon) | 3.0 - 3.1 | 1.5 - 4.1 | 100 - 150 | 2,000 - 4,000+ | ~260 °C | Yüksek (3C / 5C) | **(+):** Çok düşük maliyet, bol hammadde, soğukta üstün performans.<br>**(-):** Lityuma göre daha düşük enerji yoğunluğu, yüksek faz geçiş direnç değişimi. |

---

## ⚡ 2. Eşdeğer Devre Modelleri (Equivalent Circuit Models - ECM)

Elektriksel eşdeğer devreler, hücrenin elektrokimyasal dinamiklerini direnç (R) ve kapasitör (C) elemanları kullanarak temsil eder. Bu modeller gerçek zamanlı BMS gömülü yazılımlarında çalıştırılabilecek kadar hızlı ve pratiktir.

```mermaid
graph LR
    subgraph 1-RC Thevenin Modeli
        A[+] --- R0[R0 - Ohmik Direnç]
        R0 --- B[Parallel R1 & C1]
        subgraph RC Grubu
            B --- R1[R1 - Polarizasyon Direnci]
            B --- C1[C1 - Polarizasyon Kapasitesi]
        end
        R1 --- C[OCV - Açık Devre Gerilimi]
        C1 --- C
        C --- D[-]
    end
```

### A. 1-RC (Thevenin) Modeli
Hücrenin ohmik direncini ($R_0$) ve yavaş polarizasyon dinamiklerini tek bir RC grubuyla modeller.

#### Matematiksel İfadeler:
Terminal gerilimi ($V_t$):
$$V_t(t) = V_{oc}(SoC) - I(t)R_0 - V_{rc}(t)$$

RC grubundaki voltaj düşümü ($V_{rc}$) diferansiyel denklemi:
$$\frac{dV_{rc}(t)}{dt} = -\frac{V_{rc}(t)}{R_1 C_1} + \frac{I(t)}{C_1}$$

### B. 2-RC Modeli
Şarj transferi ($R_1, C_1$) ve kütle difüzyonu ($R_2, C_2$) gibi iki farklı zaman sabitine sahip fiziksel olayı modelleyerek doğruluğu artırır.

#### Durum-Uzay (State-Space) Formülasyonu:
Durum vektörü $\mathbf{x} = [V_{rc1}, V_{rc2}, SoC]^T$ ve girdi $u = I$ olmak üzere:

$$\begin{bmatrix} \dot{V}_{rc1} \\ \dot{V}_{rc2} \\ \dot{SoC} \end{bmatrix} = \begin{bmatrix} -\frac{1}{R_1 C_1} & 0 & 0 \\ 0 & -\frac{1}{R_2 C_2} & 0 \\ 0 & 0 & 0 \end{bmatrix} \begin{bmatrix} V_{rc1} \\ V_{rc2} \\ SoC \end{bmatrix} + \begin{bmatrix} \frac{1}{C_1} \\ \frac{1}{C_2} \\ -\frac{1}{3600 \cdot Q_n} \end{bmatrix} I$$

$$\mathbf{y} = V_t = V_{oc}(SoC) - V_{rc1} - V_{rc2} - I \cdot R_0$$

*(Burada $Q_n$ hücre kapasitesi ($Ah$), deşarj akımı pozitif ($I > 0$) yön kabul edilmiştir.)*

---

## 📈 3. OCV-SoC Karakterizasyonu ve Histerezis

Hücrenin Açık Devre Voltajı ($V_{oc}$), Şarj Durumu ($SoC$) ile doğrudan ilişkilidir. Ancak bu ilişki doğrusal değildir ve sıcaklığa bağlıdır.

```mermaid
graph TD
    A[OCV-SoC Modelleme Yöntemleri] --> B[N-inci Derece Polinom Sığdırma]
    A --> C[Nernst-Margules Birleşik Model]
    A --> D[LUT - Look-up Table Yöntemi]
    
    B --> B1["Voc = a0 + a1*SoC + a2*SoC^2 + a3*SoC^3..."]
    C --> C1["Voc = K0 + K1*SoC + K2/SoC + K3*ln(SoC) + K4*ln(1-SoC)"]
```

### OCV Histerezisi (Plett One-State Hysteresis Model)
Aynı SoC değerinde, hücrenin şarj edildikten sonraki durağan voltajı ($V_{oc,\text{charge}}$), deşarj edildikten sonraki durağan voltajından ($V_{oc,\text{discharge}}$) her zaman bir miktar yüksektir. Bu farka **histerezis** denir ve nikel tabanlı kimyalarda (NMC) az iken, LFP kimyalarında ($\pm 15\text{ mV} - 25\text{ mV}$) çok belirgindir.

Gregory Plett tarafından formüle edilen **Tek-Durumlu Histerezis (One-State Hysteresis)** diferansiyel denklemi:

$$\frac{dh(t)}{dt} = -\left|\frac{\gamma \cdot \eta \cdot I(t)}{3600 \cdot Q_n}\right| \left(h(t) + \text{sgn}(I(t))\right)$$

Ayrık zaman (Zero-Order Hold - ZOH) çözümü ($I > 0$ deşarj yönü kabulüyle):
$$h_{k+1} = \exp\left(-\left|\frac{\gamma I_k \Delta t}{3600 Q_n}\right|\right) h_k - \left[1 - \exp\left(-\left|\frac{\gamma I_k \Delta t}{3600 Q_n}\right|\right)\right] \text{sgn}(I_k)$$

$$V_t(k) = V_{oc}(SoC_k) + M(SoC_k) \cdot h_k - I_k R_0(T, SoC) - V_{rc1, k} - V_{rc2, k}$$

---

## 🌡 4. Arrhenius Yasası ve Sıcaklık-Bağımlı İç Direnç Modellemesi

Batarya hücrelerinin ohmik ($R_0$) ve polarizasyon ($R_1, R_2$) dirençleri ortam sıcaklığı düştükçe elektrolit iyonik iletkenliğinin azalması nedeniyle üstel olarak artar. Bu fiziksel davranış **Arrhenius Denklemi** ile modellenir:

$$R(T) = R_{\text{ref}} \cdot \exp\left[\frac{E_a}{R_{\text{gas}}} \left(\frac{1}{T} - \frac{1}{T_{\text{ref}}}\right)\right]$$

*   $T$: Mutlak hücre sıcaklığı ($\text{K}$), $T_{\text{ref}} = 298.15\text{ K}$ ($25^\circ\text{C}$)
*   $E_a$: Aktivasyon enerjisi ($\approx 20\,000 - 35\,000\text{ J/mol}$)
*   $R_{\text{gas}} = 8.314\text{ J/(mol}\cdot\text{K)}$: Evrensel gaz sabiti

---

## 🧪 5. HPPC (Hybrid Pulse Power Characterization) Parametre Çıkarımı

Eşdeğer devre parametreleri ($R_0, R_1, C_1, R_2, C_2$) laboratuvarda farklı SoC ve sıcaklık noktalarında uygulanan **HPPC darbe testleri** ile belirlenir:

1.  **Anlık Gerilim Çökmesi ($\Delta t \to 0^+$):** Akım darbesi uygulandığı ilk milisaniyede kapasitörler kısa devre gibi davranır; ani gerilim düşümü doğrudan ohmik direnci verir:
    $$R_0 = \frac{|V_t(t_0^-) - V_t(t_0^+)|}{|I_{\text{pulse}}|}$$
2.  **Gevşeme (Relaxation) Eğrisi Sığdırma ($I = 0$):** Akım kesildikten sonraki dinlenme fazında terminal geriliminin $V_{oc}$'ye dönüş eğrisi çift üstel (bi-exponential) En Küçük Kareler (Non-linear Least Squares) yöntemiyle fit edilerek $\tau_1 = R_1 C_1$ ve $\tau_2 = R_2 C_2$ zaman sabitleri ayrıştırılır:
    $$V_t(t) - V_{oc} = -V_{rc1}(0) e^{-t/\tau_1} - V_{rc2}(0) e^{-t/\tau_2}$$

---

## 💻 Uygulama ve Simülasyon

Modül klasöründeki kodları inceleyerek teorik modellerin Python simülasyonlarını çalıştırabilirsiniz:
*   [cell_model_1RC.py](./cell_model_1RC.py): Gerçekçi 6. derece NMC OCV polinomu ve dinamik deşarj döngüsüyle (DST) hücre voltaj tepkisini veren 1-RC simülasyonu.
*   [cell_model_2RC_hysteresis.py](./cell_model_2RC_hysteresis.py): LFP düz platolu OCV eğrisi, Plett histerezis zarflaması, Arrhenius sıcaklık bağımlılığı ($25^\circ\text{C}$ vs $0^\circ\text{C}$) ve 2-RC (hızlı yük transferi + yavaş difüzyon) HPPC darbe cevabı simülasyonu.

---

## 🛠 Kullanılan Araçlar
*   **PyBaMM:** Elektrokimyasal düzeyde pil fiziksel simülasyonları için mükemmel bir Python kütüphanesi.
*   **MATLAB/Simulink:** Batarya Hücre Karakterizasyonu ve Parameter Estimation Toolbox yardımıyla R, C parametrelerinin deneysel veriyle fit edilmesi.
