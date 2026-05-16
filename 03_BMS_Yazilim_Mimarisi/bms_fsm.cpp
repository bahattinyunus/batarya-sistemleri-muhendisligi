#include <iostream>
#include <string>

enum class BMS_State {
    INIT,
    STANDBY,
    CHARGE,
    DISCHARGE,
    FAULT
};

class BMS_Controller {
private:
    BMS_State currentState;
    bool isOverVoltage;
    bool isUnderVoltage;

public:
    BMS_Controller() : currentState(BMS_State::INIT), isOverVoltage(false), isUnderVoltage(false) {}

    void process() {
        switch (currentState) {
            case BMS_State::INIT:
                std::cout << "[BMS] Initializing System...\n";
                currentState = BMS_State::STANDBY;
                break;

            case BMS_State::STANDBY:
                std::cout << "[BMS] System in Standby.\n";
                // Transition logic based on current/voltage
                break;

            case BMS_State::CHARGE:
                std::cout << "[BMS] Charging...\n";
                if (isOverVoltage) currentState = BMS_State::FAULT;
                break;

            case BMS_State::DISCHARGE:
                std::cout << "[BMS] Discharging...\n";
                if (isUnderVoltage) currentState = BMS_State::FAULT;
                break;

            case BMS_State::FAULT:
                std::cerr << "[BMS] CRITICAL FAULT DETECTED! Shutting down contactors.\n";
                break;
        }
    }

    void setFault(bool ov, bool uv) {
        isOverVoltage = ov;
        isUnderVoltage = uv;
    }
};

int main() {
    BMS_Controller bms;
    
    // Simple execution loop simulation
    for (int i = 0; i < 5; ++i) {
        bms.process();
        if (i == 3) bms.setFault(true, false); // Trigger fault
    }

    return 0;
}
