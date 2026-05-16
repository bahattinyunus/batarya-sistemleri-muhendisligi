# Modül 3: BMS Yazılım Mimarisi

BMS gümülyü yazılımı, deterministik ve gerçek zamanlı bir kontrol döngüsü gerektirir. Bu modül, güvenli yazılım mimarilerini ele alır.

## 📚 Teorik Konular

1.  **Gömülü Yazılım Katmanları:**
    *   **MCAL:** Microcontroller Abstraction Layer.
    *   **HAL:** Hardware Abstraction Layer.
    *   **Application Layer:** Algoritma ve mantıksal kararların verildiği katman.
2.  **Sonlu Durum Makineleri (FSM):** BMS'in çalışma durumlarının (Init, Standby, Charge, Discharge, Fault) yönetimi.
3.  **MISRA C++:** Kritik sistemlerde güvenli kod yazım kuralları.
4.  **RTOS Kullanımı:** FreeRTOS veya Bare-metal deterministik döngüler.

## 💻 Uygulama: Deterministik BMS FSM

Aşağıdaki C++ örneği, basit bir BMS durum makinesini temsil eder.

### `bms_fsm.cpp`
Bu kod, durumlar arası geçişleri ve hata yönetimini gösterir.

---

## 🛠 Kullanılan Araçlar
- STM32CubeIDE
- GCC Arm Embedded Toolchain
- Google Test (gTest)
