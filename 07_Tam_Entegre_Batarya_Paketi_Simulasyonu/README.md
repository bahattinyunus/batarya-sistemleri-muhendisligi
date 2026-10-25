# Modül 7: Tam Entegre 96S Batarya Paketi Simülasyonu (Capstone Integration)

Bu modül, önceki 6 modüldeki elektrokimyasal, elektriksel, termal, kontrol ve haberleşme algoritmalarını tek bir **bütünleşik elektrikli araç (EV) batarya sistemi** mimarisinde birleştiren zirve (capstone) simülasyonudur.

---

## 🚗 1. Sistem Mimarisi ve Paket Konfigürasyonu

Elektrikli araçlarda güç aktarım organı (powertrain) ve inverter gerilim gereksinimlerini karşılamak amacıyla hücreler seri ve paralel kombinasyonlarla paketlenir. Bu simülasyonda modern bir C/D-segment EV bataryası modellenmiştir:

*   **Paket Topolojisi:** 96S1P (96 hücre seri bağlı)
*   **Nominal Gerilim:** ~355 V – 403 V (Maksimum şarj gerilimi: 408 V)
*   **Nominal Kapasite:** 55 Ah (~21.5 kWh – 75 kWh ölçeklenebilir)
*   **Üretim Dağılımı (Cell-to-Cell Variation):** Seri bağlı 96 hücrenin kapasite ($Q_n$), ohmik direnç ($R_0$), polarizasyon parametreleri ($R_1, C_1$) ve başlangıç şarj durumları ($SoC_0$) Gauss ve homojen dağılımlarla simüle edilmiştir.

```mermaid
graph TD
    subgraph 96S Batarya Paketi
        C1[Hücre 1] --- C2[Hücre 2] --- CDots[...] --- C96[Hücre 96]
    end

    subgraph Donanım ve Aktüatör Katmanı
        PRE[Ön Şarj Direnci & Kontaktör PRE+]
        MAIN_POS[Ana Pozitif Kontaktör MAIN+]
        MAIN_NEG[Ana Negatif Kontaktör MAIN-]
        COOL[Sıvı Soğutma Pompası & Plaka]
        BAL[Pasif Dengeleme Şönt MOSFET'leri]
    end

    subgraph Kontrol & Kestirim Katmanı (BMS ECU)
        EKF[Genişletilmiş Kalman Filtresi - EKF SoC]
        PID[Aktif Termal PID Kontrolcü]
        FSM[Sonlu Durum Makinesi - Precharge/Safe State]
    end

    subgraph Araç Ağı
        CAN[CAN-Bus DBC: 0x351, 0x352, 0x353, 0x354]
    end

    C1 & C2 & C96 --> EKF
    C1 & C2 & C96 --> BAL
    C1 & C2 & C96 --> PID
    FSM --> MAIN_POS & MAIN_NEG & PRE
    PID --> COOL
    EKF & PID & FSM --> CAN
```

---

## ⏱ 2. Simüle Edilen Görev Döngüsü (EV Mission Profile)

40 dakikalık (2400 saniye) kapsamlı sürüş ve şarj döngüsü şu aşamalardan oluşur:

1.  **Ön Şarj Aşaması ($t = 0 - 20\text{ s}$):**
    *   İnvertör DC-Link kapasitörünün ($940\ \mu\text{F}$) taş direnç ($47\ \Omega$) üzerinden şarj edilmesi.
    *   $V_{\text{link}} \ge 0.95 \cdot V_{\text{pack}}$ sağlandığında `MAIN+` kapatılması ve `PRE+` açılması.
2.  **Dinamik WLTP Sürüş Fazı ($t = 20 - 900\text{ s}$):**
    *   Şehir içi seyir ($40\text{ A}$), agresif ivmelenme ve sollamalar ($175\text{ A}$), rejeneratif frenleme darbeleri ($-85\text{ A}$) ve trafik ışığı duraklamaları.
3.  **Otonom Dinlenme & Hücre Dengeleme Fazı ($t = 900 - 1500\text{ s}$):**
    *   Araç park halinde ($I = 0\text{ A}$). Hücre voltaj farkları ($\Delta V$) izlenerek ortalama üstü hücrelerin enerjisi $33\ \Omega$ pasif şönt dirençleri üzerinden deşarj edilerek paket dengelenir.
4.  **DC Yüksek Hızlı Şarj (DC Fast Charge - $t = 1500 - 2400\text{ s}$):**
    *   Sabit Akım (CC, $120\text{ A}$) ile hızlı şarj. SoC %80 sınırına ulaşıldığında hücreleri aşırı gerilimden korumak için akım orantılı olarak azaltılır (CV Taper).

---

## 🔬 3. Entegre Edilen Algoritmalar

*   **EKF Paket SoC Takipçisi:** Gürültülü ($\pm 60\text{ mV}$) voltaj ölçümü altında, kasıtlı olarak **%20 hatalı** başlatılan şarj durumunu kısa sürede gerçek değere yakınsar (Simülasyon sonu hata: $<\%0.05$).
*   **Aktif Termal PID Kontrolü:** Yüksek akımlı sürüş ve $120\text{ A}$ hızlı şarj esnasında hücrelerin ürettiği Joule ısısını ($I^2 R$) soğutma plakası debisini PID ile ayarlayarak $32^\circ\text{C}$ hedefinde dengeler.
*   **DBC Uyumlu CAN Yayın:** Paketin o anki durumu `0x351` (BMS_Status), `0x352` (BMS_Limits), `0x353` (BMS_CellVoltages) ve `0x354` (BMS_Thermal) CAN çerçeveleri olarak yayınlanır.

---

## 💻 Uygulama ve Çalıştırma

```bash
python 07_Tam_Entegre_Batarya_Paketi_Simulasyonu/integrated_bms_pack_sim.py
```

*Üretilen analiz grafiği `assets/integrated_pack_simulation.png` konumuna kaydedilir.*
