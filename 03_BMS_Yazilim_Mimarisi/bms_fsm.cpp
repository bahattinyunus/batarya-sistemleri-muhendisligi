#include <iostream>
#include <array>
#include <string>
#include <cstdint>

// Automotive-style Diagnostic Trouble Codes (DTC)
enum class DTC : uint16_t {
    NONE = 0x0000,
    OVER_VOLTAGE = 0x9001,
    UNDER_VOLTAGE = 0x9002,
    OVER_TEMPERATURE = 0x9003,
    OVER_CURRENT = 0x9004
};

// BMS Finite State Machine States
enum class BMS_State {
    INIT,
    STANDBY,
    CHARGE,
    DISCHARGE,
    FAULT
};

// Simple helper to get string name of state
const char* stateToString(BMS_State state) {
    switch (state) {
        case BMS_State::INIT:      return "INIT";
        case BMS_State::STANDBY:   return "STANDBY";
        case BMS_State::CHARGE:    return "CHARGE";
        case BMS_State::DISCHARGE: return "DISCHARGE";
        case BMS_State::FAULT:     return "FAULT";
        default:                   return "UNKNOWN";
    }
}

// Simple helper to get string name of DTC
const char* dtcToString(DTC code) {
    switch (code) {
        case DTC::NONE:             return "No Fault";
        case DTC::OVER_VOLTAGE:     return "DTC 0x9001 - CELL OVER VOLTAGE";
        case DTC::UNDER_VOLTAGE:    return "DTC 0x9002 - CELL UNDER VOLTAGE";
        case DTC::OVER_TEMPERATURE: return "DTC 0x9003 - CELL OVER TEMPERATURE";
        case DTC::OVER_CURRENT:     return "DTC 0x9004 - PACK OVER CURRENT";
        default:                    return "UNKNOWN FAULT";
    }
}

class BMS_FSM {
private:
    BMS_State currentState;
    DTC activeDTC;

    // Safety Thresholds
    const float MAX_CELL_V = 4.25f; // Volts
    const float MIN_CELL_V = 2.80f; // Volts
    const float MAX_TEMP_C = 60.0f; // Celsius
    const float MAX_CURR_A = 120.0f; // Amperes

    // Debounce parameters (fault must persist for N steps to trigger FAULT state)
    const uint8_t FAULT_DEBOUNCE_LIMIT = 3;
    uint8_t overVoltageCounter = 0;
    uint8_t underVoltageCounter = 0;
    uint8_t overTempCounter = 0;
    uint8_t overCurrentCounter = 0;

    // Output status of physical contactors
    bool contactorsClosed = false;

    void openContactors() {
        if (contactorsClosed) {
            std::cout << "[HARDWARE] >>> KONTAKTORLER ACILDI! (Sistem Enerjisi Kesildi) <<<\n";
            contactorsClosed = false;
        }
    }

    void closeContactors() {
        if (!contactorsClosed) {
            std::cout << "[HARDWARE] >>> KONTAKTORLER KAPATILDI! (Enerji Akisi Saglandi) <<<\n";
            contactorsClosed = true;
        }
    }

public:
    BMS_FSM() : currentState(BMS_State::INIT), activeDTC(DTC::NONE) {}

    void tick(float cell_voltage, float current, float temperature) {
        // --- 1. Fault Detection with Debouncing ---
        // Over Voltage check
        if (cell_voltage > MAX_CELL_V) {
            if (++overVoltageCounter >= FAULT_DEBOUNCE_LIMIT) {
                activeDTC = DTC::OVER_VOLTAGE;
                currentState = BMS_State::FAULT;
            }
        } else {
            overVoltageCounter = 0;
        }

        // Under Voltage check
        if (cell_voltage < MIN_CELL_V) {
            if (++underVoltageCounter >= FAULT_DEBOUNCE_LIMIT) {
                activeDTC = DTC::UNDER_VOLTAGE;
                currentState = BMS_State::FAULT;
            }
        } else {
            underVoltageCounter = 0;
        }

        // Over Temperature check
        if (temperature > MAX_TEMP_C) {
            if (++overTempCounter >= FAULT_DEBOUNCE_LIMIT) {
                activeDTC = DTC::OVER_TEMPERATURE;
                currentState = BMS_State::FAULT;
            }
        } else {
            overTempCounter = 0;
        }

        // Over Current check
        if (current > MAX_CURR_A) {
            if (++overCurrentCounter >= FAULT_DEBOUNCE_LIMIT) {
                activeDTC = DTC::OVER_CURRENT;
                currentState = BMS_State::FAULT;
            }
        } else {
            overCurrentCounter = 0;
        }

        // --- 2. State Machine Logic ---
        switch (currentState) {
            case BMS_State::INIT:
                std::cout << "[BMS FSM] Durum: INIT. Sistem oz-testleri yapiliyor...\n";
                // Transition to standby immediately if no initial faults
                if (activeDTC == DTC::NONE) {
                    currentState = BMS_State::STANDBY;
                    std::cout << "[BMS FSM] Oz-test basarili. Gecis -> STANDBY\n";
                }
                break;

            case BMS_State::STANDBY:
                std::cout << "[BMS FSM] Durum: STANDBY. Hücreler izleniyor. Kontaktörler: ACIK.\n";
                openContactors();
                
                // Transition logic based on current direction
                if (current > 1.0f) {
                    currentState = BMS_State::DISCHARGE;
                    std::cout << "[BMS FSM] Yuksek deşarj akımı algılandı. Gecis -> DISCHARGE\n";
                } else if (current < -1.0f) {
                    currentState = BMS_State::CHARGE;
                    std::cout << "[BMS FSM] Şarj akımı algılandı. Gecis -> CHARGE\n";
                }
                break;

            case BMS_State::CHARGE:
                std::cout << "[BMS FSM] Durum: CHARGE. Sarj ediliyor. V_cell: " << cell_voltage << " V, I: " << current << " A. Kontaktörler: KAPALI.\n";
                closeContactors();
                
                // If charging stops
                if (current >= -0.1f && current <= 0.1f) {
                    currentState = BMS_State::STANDBY;
                    std::cout << "[BMS FSM] Akim kesildi. Gecis -> STANDBY\n";
                }
                break;

            case BMS_State::DISCHARGE:
                std::cout << "[BMS FSM] Durum: DISCHARGE. Desarj ediliyor. V_cell: " << cell_voltage << " V, I: " << current << " A. Kontaktörler: KAPALI.\n";
                closeContactors();
                
                // If discharging stops
                if (current >= -0.1f && current <= 0.1f) {
                    currentState = BMS_State::STANDBY;
                    std::cout << "[BMS FSM] Akim kesildi. Gecis -> STANDBY\n";
                }
                break;

            case BMS_State::FAULT:
                std::cout << "[BMS FSM] !!! CRITICAL FAULT !!! Durum: FAULT. Aktif Hata: " << dtcToString(activeDTC) << "\n";
                openContactors();
                break;
        }
        std::cout << "--------------------------------------------------\n";
    }

    BMS_State getState() const { return currentState; }
    DTC getActiveDTC() const { return activeDTC; }
};

int main() {
    BMS_FSM bms;
    
    // Simulating a real drive cycle steps
    // Parameters: cell_voltage, current, temperature
    
    std::cout << "=== BMS Sonlu Durum Makinesi (FSM) Simülasyonu Başlatıldı ===\n\n";

    // Step 1: Initialization
    bms.tick(3.8f, 0.0f, 25.0f);

    // Step 2: System in Standby
    bms.tick(3.78f, 0.0f, 26.0f);

    // Step 3: Vehicle starts discharging (Drawing 20A)
    bms.tick(3.72f, 20.0f, 28.0f);

    // Step 4: Discharging continues, temp increases
    bms.tick(3.68f, 50.0f, 35.0f);

    // Step 5: Cell temperature suddenly spikes above limit (60.0C)
    // First step over limit: Debounce = 1. No FAULT yet.
    std::cout << "[TEST SIM] Sicaklik 62C'ye yukseldi - Debounce Filtresi Calisiyor (1/3)\n";
    bms.tick(3.65f, 50.0f, 62.0f);

    // Second step over limit: Debounce = 2. No FAULT yet.
    std::cout << "[TEST SIM] Sicaklik yuksek seyrediyor - Debounce Filtresi Calisiyor (2/3)\n";
    bms.tick(3.64f, 50.0f, 62.5f);

    // Third step over limit: Debounce = 3 -> Triggers FAULT state, open contactors!
    std::cout << "[TEST SIM] Sicaklik limiti 3 periyottur asildi! FAULT tetiklenecek.\n";
    bms.tick(3.63f, 50.0f, 63.0f);

    // Step 6: System in FAULT state
    bms.tick(3.60f, 0.0f, 55.0f);

    return 0;
}
