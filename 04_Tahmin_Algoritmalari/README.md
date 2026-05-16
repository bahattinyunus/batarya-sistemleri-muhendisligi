# Modül 4: Kestirim Algoritmaları

Batarya iç durumları (SoC, SoH, SoP) doğrudan ölçülemez; sensör verilerinden tahmin edilmelidir.

## 📚 Teorik Konular

1.  **State of Charge (SoC) Tahmini:**
    *   **Coulomb Counting:** Akım entegrasyonu (drift riski taşır).
    *   **EKF (Extended Kalman Filter):** Hücre modelini kullanarak gürültülü sensör verilerinden optimal tahmin.
2.  **State of Health (SoH) Tahmini:** Kapasite kaybı ve iç direnç değişimlerinin takibi.
3.  **State of Power (SoP):** Bataryanın o anki fiziksel sınırları dahilinde verebileceği maksimum gücün hesaplanması.

## 💻 Uygulama: Extended Kalman Filter (EKF)

Aşağıdaki Python kodu, SoC tahmini için temel bir EKF yapısını gösterir.

### `ekf_soc_estimator.py`
Bu dosya, gürültülü voltaj ölçümlerini filtreleyerek doğru SoC tahminine ulaşır.

---

## 🛠 Kullanılan Araçlar
- Python (NumPy, SciPy)
- FilterPy Library
