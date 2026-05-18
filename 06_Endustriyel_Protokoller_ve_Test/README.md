# Modül 6: Endüstriyel Protokoller, Test ve Doğrulama

Bir Batarya Yönetim Sistemi (BMS), araç içerisindeki VCU (Araç Kontrol Ünitesi), inverter, şarj aleti (OBC) veya endüstriyel enerji depolama tesislerinde (ESS) PLC ile sürekli iletişim halindedir. Bu modül, endüstriyel haberleşme protokollerini, diagnostik altyapılarını ve sistem doğrulama (HIL) yöntemlerini kapsar.

---

## 🔌 1. CAN-Bus (Controller Area Network) Haberleşmesi

BMS haberleşmesinin omurgasını CAN-Bus oluşturur. Gelişen teknolojiyle birlikte daha yüksek veri genişliği sunan CAN-FD standardına geçiş yapılmaktadır.

| Haberleşme Standardı | Maksimum Veri Hızı | Maksimum Veri Alanı (Payload) | Arbitrasyon (Önceliklendirme) | Temel Kullanım Alanı |
| :--- | :--- | :--- | :--- | :--- |
| **CAN 2.0B** (Klasik CAN) | 1 Mbps | 8 Byte | Bit bazlı (ID önceliği) | Geleneksel araç içi haberleşme, BMS-İnverter arası |
| **CAN-FD** (Flexible Data-rate) | 8+ Mbps | 64 Byte | Bit bazlı + Veri hızı artışı | Çok hücreli (96S+) bataryalarda tüm voltaj verilerini tek çerçevede gönderme |

*   **Arbitrasyon Mekanizması:** Düşük CAN ID'ye sahip olan mesaj (örn. `0x080` - Kritik Hata Mesajı), yüksek ID'ye sahip mesaja (örn. `0x351` - SoC Durum Mesajı) göre hatta önceliğe sahiptir. Bu, acil durum mesajlarının gecikmesini önler.

---

## 📝 2. DBC (Database CAN) Dosyası ve Mesaj Paketleme

CAN hattında veriler ham byte'lar halinde taşınır. Bu ham verileri anlamlı fiziksel birimlere (Gerilim, Akım, SoC) dönüştürmek için **DBC** dosyaları kullanılır.

### Örnek BMS CAN Mesaj Yapısı (ID: `0x351` - BMS_Status)
*   **Periyot:** 100 ms (10 Hz)
*   **Uzunluk:** 8 Byte (64 bit)

```
Bit:   [0 .. 15]        [16 .. 31]         [32 .. 47]        [48 .. 63]
Veri:  SoC (%)         Gerilim (V)        Akım (A)           Hata Durumu
Tip:   U16             U16                S16 (Signed)       U16 (Bitmask)
```

#### Sinyal Çözümleme Matematiksel Dönüşümü:
$$\text{Fiziksel Değer} = (\text{Ham Değer} \cdot \text{Scale}) + \text{Offset}$$

*   **SoC Sinyali (Bit 0):** Scale = 0.1, Offset = 0, Range = [0.0 - 100.0] %
*   **Akım Sinyali (Bit 32):** Scale = 0.1, Offset = -3276.8, Range = [-3276.8 - 3276.7] A *(Negatif değerler şarj, pozitif değerler deşarj akımıdır.)*

---

## 🖥 3. HIL (Hardware-in-the-Loop) Test Altyapısı

BMS yazılımının gerçek araç üzerinde test edilmesi aşırı şarj, kısa devre veya aşırı ısınma gibi durumlarda patlama riski taşıdığı için imkansızdır. Bu nedenle doğrulamalar **HIL** kabinlerinde yapılır.

```mermaid
graph LR
    subgraph HIL Test Kabini (Gerçek Zamanlı Simülatör)
        Sim[Araç ve Batarya Fiziksel Simülasyonu]
        CellEm[Hücre Voltaj Emülatörü - İzole DC]
        FIU[Fault Injection Unit - Hata Enjeksiyonu]
    end

    subgraph Gerçek BMS Cihazı (DUT - Device Under Test)
        BMS[BMS Kontrol Kartı]
    end

    CellEm -- "Fiziksel Hücre Voltajları" --> BMS
    BMS -- "Kontaktör Kontrolü & CAN" --> Sim
    FIU -- "Kablo Kopması / Kısa Devre" --> BMS
    
    style Sim fill:#f9f,stroke:#333
    style CellEm fill:#ffb,stroke:#333
    style BMS fill:#bbf,stroke:#333,stroke-width:2px
```

*   **Hücre Emülatörleri:** Bataryanın her bir hücresi gibi davranan, mikrodenetleyici tarafından kontrol edilebilen izole güç kaynaklarıdır.
*   **Hata Enjeksiyon Ünitesi (FIU):** Yazılım çalışırken fiziksel olarak kabloları kopartır, kısa devreler oluşturur veya sensör hatları üzerine gürültü ekleyerek BMS koruma fonksiyonlarının doğruluğunu test eder.

---

## 🩺 4. UDS (Unified Diagnostic Services - ISO 14229) Teşhis Protokolü

BMS, araç servis istasyonuna bağlandığında veya üretim hattında teşhis edilmek istendiğinde UDS protokolü kullanılır. Haberleşme CAN-Bus üzerindeki istek-cevap şemasıyla yürür.

### Önemli UDS Servisleri ve BMS Karşılıkları:
1.  **Diagnostic Session Control (`0x10`):** Extended (`0x03`) veya Programming (`0x02`) oturumlarına geçerek kritik yazılım güncellemeleri veya kalibrasyon yüklemeleri yapılır.
2.  **Read Data By Identifier (`0x22`):** Belirli ID kodlarıyla veri okunur. Örn:
    *   `Identifier 0xF190`: Araç Şasi Numarası (VIN)
    *   `Identifier 0x4001`: Hücre Voltaj Değerleri listesi
3.  **Read DTC Information (`0x19`):** BMS kalıcı hafızasına (EEPROM) kaydedilmiş geçmiş hata kodları (Diagnostic Trouble Codes - DTC) okunur.
4.  **Clear Diagnostic Information (`0x14`):** Kaydedilmiş hataları silerek sistemin normal çalışmaya dönmesini sağlar (eğer fiziksel arıza giderildiyse).

---

## 💻 Uygulama ve Simülasyon

*   [bms_can_simulator.py](./bms_can_simulator.py): BMS'in akım, gerilim ve SoC sinyallerini Little Endian / Intel formatında 8-byte ham CAN paketlerine kodlayan ve çözen Python simülasyonu.
