# Modül 1: Hücre Modelleme ve Karakterizasyon

Bu modül, bir batarya hücresinin fiziksel ve kimyasal davranışlarını matematiksel modellere dönüştürmeyi amaçlar.

## 📚 Teorik Konular

1.  **Hücre Kimyası:** Li-ion, LFP, NMC ve LTO kimyalarının karakteristikleri.
2.  **Eşdeğer Devre Modelleri (ECM):**
    *   **Rint Modeli:** Sadece iç direnç.
    *   **Thevenin (1-RC) Modeli:** Geçici tepkileri modellemek için bir RC çifti.
    *   **2-RC Modeli:** Daha yüksek doğruluk için difüzyon etkilerini ekleme.
3.  **OCV-SoC Karakterizasyonu:** Açık devre voltajı ile şarj durumu arasındaki ilişki.

## 💻 Uygulama: 1-RC Thevenin Modeli

Aşağıdaki Python kodu, bir batarya hücresinin 1-RC Thevenin modelini kullanarak terminal voltajını simüle eder.

### `cell_model_1RC.py`
Bu dosya, verilen akım profiline göre hücrenin voltaj cevabını hesaplar.

---

## 🛠 Kullanılan Araçlar
- Python (NumPy, Matplotlib)
- PyBaMM
- MATLAB/Simulink
