import struct

class BMS_CAN_Simulator:
    """
    Simulates BMS CAN-Bus message packet framing (encoding and decoding).
    Target Message: BMS_Status (ID: 0x351)
    Cycle: 100ms
    Length: 8 Bytes
    
    Signals layout (Little Endian / Intel):
    - SoC: Bits 0-15 (16-bit U16, Scale: 0.1, Offset: 0.0) -> Range: 0 to 100.0 %
    - Voltage: Bits 16-31 (16-bit U16, Scale: 0.1, Offset: 0.0) -> Range: 0 to 6553.5 V
    - Current: Bits 32-47 (16-bit S16, Scale: 0.1, Offset: 0.0) -> Range: -3276.8 to 3276.7 A
    - Faultmask: Bits 48-63 (16-bit U16, Scale: 1.0, Offset: 0.0) -> Bitmask of DTCs
    """
    def __init__(self):
        pass

    def encode_message(self, soc, voltage, current, faultmask):
        """
        Packs physical engineering units into an 8-byte raw CAN frame payload.
        Conforming to typical automotive C-code bitwise structures.
        """
        # Apply scaling and offsets
        raw_soc = int(round(soc / 0.1))
        raw_voltage = int(round(voltage / 0.1))
        raw_current = int(round(current / 0.1))
        raw_fault = int(faultmask)

        # Clip values to fit their bitwidths
        raw_soc = max(0, min(65535, raw_soc))
        raw_voltage = max(0, min(65535, raw_voltage))
        raw_current = max(-32768, min(32767, raw_current))
        raw_fault = max(0, min(65535, raw_fault))

        # Format as Little Endian:
        # H = uint16, h = int16
        # '<HHhH' -> Little endian: U16, U16, S16, U16
        payload = struct.pack('<HHhH', raw_soc, raw_voltage, raw_current, raw_fault)
        return payload

    def decode_message(self, payload):
        """
        Unpacks an 8-byte raw CAN frame payload back to physical engineering units.
        """
        if len(payload) != 8:
            raise ValueError("CAN Payload must be exactly 8 bytes long.")

        # Unpack Little Endian binary structure
        raw_soc, raw_voltage, raw_current, raw_fault = struct.unpack('<HHhH', payload)

        # Re-apply scale and offset
        soc = raw_soc * 0.1
        voltage = raw_voltage * 0.1
        current = raw_current * 0.1
        faultmask = raw_fault

        return soc, voltage, current, faultmask

# --- Execution Simulation ---
if __name__ == "__main__":
    sim = BMS_CAN_Simulator()
    
    print("=== BMS CAN Haberleşme Paket Simülatörü ===")
    
    # Test Case 1: Normal Operation (Discharging)
    test_soc1 = 82.4       # %
    test_v1 = 398.2        # V
    test_i1 = 45.5         # A (Discharging)
    test_fault1 = 0x0000   # No faults
    
    print("\n--- Senaryo 1: Normal Deşarj Hali ---")
    payload1 = sim.encode_message(test_soc1, test_v1, test_i1, test_fault1)
    
    # Print raw payload in Hex
    hex_string1 = " ".join([f"0x{b:02X}" for b in payload1])
    print(f"Sinyaller: SoC={test_soc1}%, V={test_v1}V, I={test_i1}A, Faults={test_fault1}")
    print(f"CAN Payload (Hex): [ {hex_string1} ]")
    
    # Decode to verify
    d_soc1, d_v1, d_i1, d_f1 = sim.decode_message(payload1)
    print("Kod Çözüldü (Yorumlandı):")
    print(f" -> SoC:      {d_soc1:.1f} %  (Hata: {abs(d_soc1 - test_soc1):.3f}%)")
    print(f" -> Gerilim:  {d_v1:.1f} V  (Hata: {abs(d_v1 - test_v1):.3f}V)")
    print(f" -> Akım:     {d_i1:.1f} A  (Hata: {abs(d_i1 - test_i1):.3f}A)")
    print(f" -> Hata Kod: 0x{d_f1:04X}")

    # Test Case 2: Charging with Active Fault
    test_soc2 = 98.7       # %
    test_v2 = 422.5        # V (High voltage)
    test_i2 = -15.0        # A (Charging, negative)
    test_fault2 = 0x9001   # CELL OVER VOLTAGE active DTC
    
    print("\n--- Senaryo 2: Sarj Esnasinda Kritik Hata Hali ---")
    payload2 = sim.encode_message(test_soc2, test_v2, test_i2, test_fault2)
    
    hex_string2 = " ".join([f"0x{b:02X}" for b in payload2])
    print(f"Sinyaller: SoC={test_soc2}%, V={test_v2}V, I={test_i2}A, Faults=0x{test_fault2:04X}")
    print(f"CAN Payload (Hex): [ {hex_string2} ]")
    
    # Decode to verify
    d_soc2, d_v2, d_i2, d_f2 = sim.decode_message(payload2)
    print("Kod Çözüldü (Yorumlandı):")
    print(f" -> SoC:      {d_soc2:.1f} %  (Hata: {abs(d_soc2 - test_soc2):.3f}%)")
    print(f" -> Gerilim:  {d_v2:.1f} V  (Hata: {abs(d_v2 - test_v2):.3f}V)")
    print(f" -> Akım:     {d_i2:.1f} A  (Hata: {abs(d_i2 - test_i2):.3f}A)")
    print(f" -> Hata Kod: 0x{d_f2:04X} (CELL OVER VOLTAGE DETECTED!)")
    print("---------------------------------------------")
