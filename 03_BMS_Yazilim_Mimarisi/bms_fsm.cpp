#include <iostream>
#include <array>
#include <cstdint>
#include <iomanip>

// ============================================================================
// ISO 26262 & AUTOSAR-Compliant Deterministic BMS Finite State Machine (FSM)
// Conforms to MISRA C++:2008 guidelines (No dynamic heap allocation, no
// exceptions, fixed-width integers, deterministic execution).
// ============================================================================

// Automotive Diagnostic Trouble Codes (DTC - ISO 14229 UDS Format)
enum class DTC : uint16_t {
    NONE                  = 0x0000U,
    CELL_OVER_VOLTAGE     = 0x9001U,
    CELL_UNDER_VOLTAGE    = 0x9002U,
    CELL_OVER_TEMPERATURE = 0x9003U,
    PACK_OVER_CURRENT     = 0x9004U,
    CONTACTOR_WELD_FAULT  = 0x9005U,
    PRECHARGE_TIMEOUT     = 0x9006U,
    ISOLATION_BREACH      = 0x9007U,
    WATCHDOG_TIMEOUT      = 0x9008U
};

// BMS Finite State Machine States
enum class BMS_State : uint8_t {
    INIT       = 0U,
    STANDBY    = 1U,
    PRECHARGE  = 2U,
    DISCHARGE  = 3U,
    CHARGE     = 4U,
    BALANCING  = 5U,
    FAULT      = 6U
};

// Contactor Hardware Output States
struct ContactorState {
    bool mainNegativeClosed;
    bool prechargeClosed;
    bool mainPositiveClosed;
};

// Freeze-Frame Snapshot stored in Non-Volatile Memory (NvM) on Fault
struct FreezeFrame {
    DTC      dtcCode;
    uint32_t timestampMs;
    float    cellVoltageV;
    float    packCurrentA;
    float    temperatureC;
    float    isolationKOhm;
};

const char* stateToString(BMS_State state) noexcept {
    switch (state) {
        case BMS_State::INIT:      return "INIT";
        case BMS_State::STANDBY:   return "STANDBY";
        case BMS_State::PRECHARGE: return "PRECHARGE";
        case BMS_State::DISCHARGE: return "DISCHARGE";
        case BMS_State::CHARGE:    return "CHARGE";
        case BMS_State::BALANCING: return "BALANCING";
        case BMS_State::FAULT:     return "FAULT";
        default:                   return "UNKNOWN";
    }
}

const char* dtcToString(DTC code) noexcept {
    switch (code) {
        case DTC::NONE:                  return "0x0000 - No Fault";
        case DTC::CELL_OVER_VOLTAGE:     return "0x9001 - CELL OVER VOLTAGE (ASIL-D)";
        case DTC::CELL_UNDER_VOLTAGE:    return "0x9002 - CELL UNDER VOLTAGE (ASIL-C)";
        case DTC::CELL_OVER_TEMPERATURE: return "0x9003 - CELL OVER TEMPERATURE (ASIL-D)";
        case DTC::PACK_OVER_CURRENT:     return "0x9004 - PACK OVER CURRENT (ASIL-C)";
        case DTC::CONTACTOR_WELD_FAULT:  return "0x9005 - CONTACTOR WELDED CLOSED (ASIL-D)";
        case DTC::PRECHARGE_TIMEOUT:     return "0x9006 - DC-LINK PRECHARGE TIMEOUT";
        case DTC::ISOLATION_BREACH:      return "0x9007 - HV ISOLATION FAULT (<100 Ohm/V)";
        case DTC::WATCHDOG_TIMEOUT:      return "0x9008 - WDGM ALIVE SUPERVISION FAULT";
        default:                         return "UNKNOWN DTC";
    }
}

class BMS_FSM {
private:
    BMS_State currentState;
    DTC activeDTC;
    ContactorState contactors;
    uint32_t systemTimeMs;
    uint16_t prechargeTimerMs;
    uint8_t watchdogAliveCounter;

    // Static Ring-Buffer for NvM Freeze-Frame Diagnostics (No heap usage)
    static constexpr std::size_t MAX_DTC_LOGS = 8U;
    std::array<FreezeFrame, MAX_DTC_LOGS> nvmFaultLog{};
    std::size_t faultLogCount = 0U;

    // Safety Calibration Thresholds
    static constexpr float MAX_CELL_V          = 4.25f;
    static constexpr float MIN_CELL_V          = 2.80f;
    static constexpr float MAX_TEMP_C          = 60.0f;
    static constexpr float MAX_CURR_A          = 120.0f;
    static constexpr float MIN_ISO_KOHM        = 40.0f;  // 100 Ohm/V @ 400V
    static constexpr float WELD_THRESHOLD_V    = 40.0f;
    static constexpr uint16_t MAX_PRECHARGE_MS = 300U;

    // Asymmetric Up/Down Debounce Limit
    static constexpr int8_t DEBOUNCE_TRIP_LIMIT = 3;
    int8_t ovDebounceCounter  = 0;
    int8_t uvDebounceCounter  = 0;
    int8_t otDebounceCounter  = 0;
    int8_t ocDebounceCounter  = 0;
    int8_t isoDebounceCounter = 0;

    void openAllContactors() noexcept {
        if (contactors.mainNegativeClosed || contactors.prechargeClosed || contactors.mainPositiveClosed) {
            contactors.mainPositiveClosed = false;
            contactors.prechargeClosed    = false;
            contactors.mainNegativeClosed = false;
            std::cout << "  [HW-ACTUATOR] >>> TUM KONTAKTORLER ACILDI! (Safe State - HV Izole Edildi) <<<\n";
        }
    }

    void recordFreezeFrame(DTC code, float vCell, float current, float temp, float isoKOhm) noexcept {
        if (faultLogCount < MAX_DTC_LOGS) {
            nvmFaultLog[faultLogCount] = FreezeFrame{code, systemTimeMs, vCell, current, temp, isoKOhm};
            ++faultLogCount;
        }
    }

    static void updateDebounce(bool faultCondition, int8_t& counter) noexcept {
        if (faultCondition) {
            if (counter < DEBOUNCE_TRIP_LIMIT) {
                ++counter;
            }
        } else {
            if (counter > 0) {
                --counter;
            }
        }
    }

public:
    BMS_FSM() noexcept
        : currentState(BMS_State::INIT),
          activeDTC(DTC::NONE),
          contactors{false, false, false},
          systemTimeMs(0U),
          prechargeTimerMs(0U),
          watchdogAliveCounter(0U) {}

    void tick(
        float cellVoltage,
        float packCurrent,
        float temperature,
        float packVoltage = 400.0f,
        float dcLinkVoltage = 0.0f,
        float isolationKOhm = 500.0f,
        float cellDeltaMv = 5.0f
    ) noexcept {
        systemTimeMs += 100U;
        ++watchdogAliveCounter;

        // --- 1. Asymmetric Fault Detection & Debouncing ---
        updateDebounce(cellVoltage > MAX_CELL_V, ovDebounceCounter);
        updateDebounce(cellVoltage < MIN_CELL_V, uvDebounceCounter);
        updateDebounce(temperature > MAX_TEMP_C, otDebounceCounter);
        updateDebounce((packCurrent > MAX_CURR_A) || (packCurrent < -MAX_CURR_A), ocDebounceCounter);
        updateDebounce(isolationKOhm < MIN_ISO_KOHM, isoDebounceCounter);

        if (currentState != BMS_State::FAULT) {
            if (ovDebounceCounter >= DEBOUNCE_TRIP_LIMIT) {
                triggerFault(DTC::CELL_OVER_VOLTAGE, cellVoltage, packCurrent, temperature, isolationKOhm);
            } else if (uvDebounceCounter >= DEBOUNCE_TRIP_LIMIT) {
                triggerFault(DTC::CELL_UNDER_VOLTAGE, cellVoltage, packCurrent, temperature, isolationKOhm);
            } else if (otDebounceCounter >= DEBOUNCE_TRIP_LIMIT) {
                triggerFault(DTC::CELL_OVER_TEMPERATURE, cellVoltage, packCurrent, temperature, isolationKOhm);
            } else if (ocDebounceCounter >= DEBOUNCE_TRIP_LIMIT) {
                triggerFault(DTC::PACK_OVER_CURRENT, cellVoltage, packCurrent, temperature, isolationKOhm);
            } else if (isoDebounceCounter >= DEBOUNCE_TRIP_LIMIT) {
                triggerFault(DTC::ISOLATION_BREACH, cellVoltage, packCurrent, temperature, isolationKOhm);
            }
        }

        // --- 2. State Machine Execution ---
        switch (currentState) {
            case BMS_State::INIT:
                std::cout << "[t=" << std::setw(4) << systemTimeMs << "ms] [INIT] Power-On Self Test (POST) & Contactor Weld Check...\n";
                // Verify DC-Link is de-energized while contactors are commanded open
                if (dcLinkVoltage > WELD_THRESHOLD_V) {
                    triggerFault(DTC::CONTACTOR_WELD_FAULT, cellVoltage, packCurrent, temperature, isolationKOhm);
                } else if (activeDTC == DTC::NONE) {
                    currentState = BMS_State::STANDBY;
                    std::cout << "  -> Oz-test ve Kontaktör Yapisma Testi BASARILI. Gecis: STANDBY\n";
                }
                break;

            case BMS_State::STANDBY:
                openAllContactors();
                std::cout << "[t=" << std::setw(4) << systemTimeMs << "ms] [STANDBY] HV Izole. V_cell=" << cellVoltage
                          << "V, T=" << temperature << "C, R_iso=" << isolationKOhm << "kOhm\n";

                if ((packCurrent > 1.0f) || (packCurrent < -1.0f)) {
                    currentState = BMS_State::PRECHARGE;
                    prechargeTimerMs = 0U;
                    contactors.mainNegativeClosed = true;
                    contactors.prechargeClosed    = true;
                    std::cout << "  -> Surus/Sarj Talebi Algilandi. MAIN- ve PRE+ Kapatildi. Gecis: PRECHARGE\n";
                } else if (cellDeltaMv > 15.0f) {
                    currentState = BMS_State::BALANCING;
                    std::cout << "  -> Hucre Gerilim Farki (" << cellDeltaMv << "mV > 15mV). Gecis: BALANCING\n";
                }
                break;

            case BMS_State::PRECHARGE:
                prechargeTimerMs += 100U;
                std::cout << "[t=" << std::setw(4) << systemTimeMs << "ms] [PRECHARGE] V_link=" << dcLinkVoltage
                          << "V / V_pack=" << packVoltage << "V (Sure: " << prechargeTimerMs << "ms)\n";

                if (dcLinkVoltage >= (0.95f * packVoltage)) {
                    contactors.mainPositiveClosed = true;
                    contactors.prechargeClosed    = false;
                    currentState = (packCurrent >= 0.0f) ? BMS_State::DISCHARGE : BMS_State::CHARGE;
                    std::cout << "  -> DC-Link %95 Seviyesine Ulasti! MAIN+ Kapatildi, PRE+ Acildi. Gecis: "
                              << stateToString(currentState) << "\n";
                } else if (prechargeTimerMs >= MAX_PRECHARGE_MS) {
                    triggerFault(DTC::PRECHARGE_TIMEOUT, cellVoltage, packCurrent, temperature, isolationKOhm);
                }
                break;

            case BMS_State::DISCHARGE:
                std::cout << "[t=" << std::setw(4) << systemTimeMs << "ms] [DISCHARGE] Aktif Desarj: V_cell=" << cellVoltage
                          << "V, I=" << packCurrent << "A, T=" << temperature << "C\n";
                if ((packCurrent >= -0.2f) && (packCurrent <= 0.2f)) {
                    currentState = BMS_State::STANDBY;
                    std::cout << "  -> Akim Sifirlandi. Gecis: STANDBY\n";
                }
                break;

            case BMS_State::CHARGE:
                std::cout << "[t=" << std::setw(4) << systemTimeMs << "ms] [CHARGE] Aktif Sarj: V_cell=" << cellVoltage
                          << "V, I=" << packCurrent << "A, T=" << temperature << "C\n";
                if ((packCurrent >= -0.2f) && (packCurrent <= 0.2f)) {
                    currentState = BMS_State::STANDBY;
                    std::cout << "  -> Sarj Tamamlandi. Gecis: STANDBY\n";
                }
                break;

            case BMS_State::BALANCING:
                std::cout << "[t=" << std::setw(4) << systemTimeMs << "ms] [BALANCING] Pasif Sönt MOSFET'ler Aktif. DeltaV="
                          << cellDeltaMv << "mV\n";
                if (cellDeltaMv <= 5.0f) {
                    currentState = BMS_State::STANDBY;
                    std::cout << "  -> Hucre Dengelendi (DeltaV <= 5mV). Gecis: STANDBY\n";
                }
                break;

            case BMS_State::FAULT:
                openAllContactors();
                std::cout << "[t=" << std::setw(4) << systemTimeMs << "ms] [FAULT] !!! SAFE STATE AKTIF !!! DTC: "
                          << dtcToString(activeDTC) << "\n";
                break;
        }
    }

    void triggerFault(DTC code, float vCell, float current, float temp, float isoKOhm) noexcept {
        activeDTC    = code;
        currentState = BMS_State::FAULT;
        openAllContactors();
        recordFreezeFrame(code, vCell, current, temp, isoKOhm);
    }

    // UDS Service 0x14: ClearDiagnosticInformation
    bool clearFaultUDS() noexcept {
        if (currentState == BMS_State::FAULT) {
            activeDTC          = DTC::NONE;
            ovDebounceCounter  = 0;
            uvDebounceCounter  = 0;
            otDebounceCounter  = 0;
            ocDebounceCounter  = 0;
            isoDebounceCounter = 0;
            currentState       = BMS_State::INIT;
            std::cout << "\n[UDS 0x14] ClearDiagnosticInformation kabul edildi. Sistem INIT durumuna dondu.\n\n";
            return true;
        }
        return false;
    }

    void printNvMFaultLog() const noexcept {
        std::cout << "\n================ NvM DTC FREEZE-FRAME BELLEK DOKUMU ================\n";
        for (std::size_t i = 0U; i < faultLogCount; ++i) {
            const auto& ff = nvmFaultLog[i];
            std::cout << " Kayit #" << (i + 1U) << " | t=" << ff.timestampMs << "ms | " << dtcToString(ff.dtcCode)
                      << "\n          | V_cell=" << ff.cellVoltageV << "V, I=" << ff.packCurrentA
                      << "A, T=" << ff.temperatureC << "C, R_iso=" << ff.isolationKOhm << "kOhm\n";
        }
        std::cout << "====================================================================\n";
    }

    BMS_State getState() const noexcept { return currentState; }
    DTC getActiveDTC() const noexcept { return activeDTC; }
};

int main() {
    BMS_FSM bms;

    std::cout << "=== AUTOSAR & ISO 26262 BMS Sonlu Durum Makinesi (FSM) Simulasyonu ===\n\n";

    // 1. INIT -> Weld Check OK (dcLinkVoltage = 0V) -> STANDBY
    bms.tick(3.82f, 0.0f, 25.0f, 400.0f, 0.0f, 500.0f, 4.0f);

    // 2. STANDBY -> Cell Imbalance detected (22mV) -> BALANCING -> Balanced -> STANDBY
    bms.tick(3.82f, 0.0f, 25.0f, 400.0f, 0.0f, 500.0f, 22.0f);
    bms.tick(3.81f, 0.0f, 25.5f, 400.0f, 0.0f, 500.0f, 4.0f);

    // 3. Drive request -> PRECHARGE sequence -> DC-Link charges to 385V (>=95%) -> DISCHARGE
    bms.tick(3.78f, 35.0f, 26.0f, 400.0f, 120.0f, 500.0f, 4.0f);
    bms.tick(3.76f, 35.0f, 27.0f, 400.0f, 388.0f, 500.0f, 4.0f);

    // 4. Normal Discharge operation
    bms.tick(3.72f, 65.0f, 32.0f, 395.0f, 395.0f, 480.0f, 5.0f);

    // 5. Over-Temperature Fault Injection with 3-step Debounce verification
    std::cout << "\n--- [FIU HATA ENJEKSIYONU] Sicaklik 63C'ye cikarildi (Debounce Testi 1..3) ---\n";
    bms.tick(3.68f, 65.0f, 62.5f, 392.0f, 392.0f, 480.0f, 5.0f); // Debounce 1/3
    bms.tick(3.66f, 65.0f, 63.0f, 390.0f, 390.0f, 480.0f, 5.0f); // Debounce 2/3
    bms.tick(3.65f, 65.0f, 64.0f, 389.0f, 389.0f, 480.0f, 5.0f); // Debounce 3/3 -> FAULT!

    // 6. System in Safe State (FAULT)
    bms.tick(3.65f, 0.0f, 45.0f, 389.0f, 0.0f, 480.0f, 5.0f);

    // 7. Print NvM Freeze-Frame Diagnostics & Clear Fault via UDS 0x14
    bms.printNvMFaultLog();
    bms.clearFaultUDS();
    bms.tick(3.70f, 0.0f, 30.0f, 392.0f, 0.0f, 500.0f, 4.0f);

    return 0;
}
