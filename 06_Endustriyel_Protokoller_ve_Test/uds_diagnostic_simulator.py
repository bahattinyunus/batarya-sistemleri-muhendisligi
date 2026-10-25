"""
uds_diagnostic_simulator.py
============================
ISO 14229 UDS (Unified Diagnostic Services) Protocol Simulator
for Battery Management System (BMS) over CAN-Bus

Implemented Services:
  0x10  DiagnosticSessionControl   — Default / Extended / Programming
  0x11  ECUReset                   — Hard / Soft reset
  0x22  ReadDataByIdentifier       — Read live BMS signals by DID
  0x2E  WriteDataByIdentifier      — Write calibration data by DID
  0x27  SecurityAccess             — Seed-Key challenge (27-bit XOR)
  0x14  ClearDiagnosticInformation — Clear DTCs
  0x19  ReadDTCInformation         — Read DTC snapshot / extended data
  0x31  RoutineControl             — Start / Stop / Results
  0x34/0x36/0x37 RequestDownload / TransferData / RequestTransferExit
        — OTA firmware update flow

CAN frame encoding follows ISO 15765-2 Transport Protocol (ISO-TP):
  Single Frame (SF):   7 bytes max
  Multi-Frame (MF):    First-Frame + Consecutive-Frame with Flow-Control
"""

import struct
import time
import hashlib
import os
import io
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from enum import IntEnum


# ---------------------------------------------------------------------------
# UDS Service IDs
# ---------------------------------------------------------------------------
class SID(IntEnum):
    DSC   = 0x10
    ECU_RESET = 0x11
    RDBI  = 0x22
    WDBI  = 0x2E
    SA    = 0x27
    CDTCI = 0x14
    RDTCI = 0x19
    RC    = 0x31
    RD    = 0x34
    TD    = 0x36
    RTE   = 0x37


class NRC(IntEnum):
    """Negative Response Codes (ISO 14229-1 Table A.1)"""
    GENERAL_REJECT              = 0x10
    SERVICE_NOT_SUPPORTED       = 0x11
    SUB_NOT_SUPPORTED           = 0x12
    INCORRECT_LENGTH            = 0x13
    CONDITIONS_NOT_CORRECT      = 0x22
    REQUEST_SEQUENCE_ERROR      = 0x24
    REQUEST_OUT_OF_RANGE        = 0x31
    SECURITY_ACCESS_DENIED      = 0x33
    INVALID_KEY                 = 0x35
    EXCEEDED_NUMBER_OF_ATTEMPTS = 0x36
    RESPONSE_PENDING            = 0x78


# ---------------------------------------------------------------------------
# BMS Simulated Data Store (ECU Internal State)
# ---------------------------------------------------------------------------
@dataclass
class BMSLiveData:
    soc_pct:          float = 78.4
    pack_voltage_v:   float = 396.2
    pack_current_a:   float = 42.1
    cell_min_v:       float = 3.781
    cell_max_v:       float = 3.819
    cell_delta_mv:    float = 38.0
    temp_max_c:       float = 32.5
    temp_min_c:       float = 28.1
    isolation_kohm:   float = 850.0
    soh_pct:          float = 94.2
    sop_dch_w:        float = 95000.0
    cycle_count:      int   = 1247
    vin:              str   = "WBABC12345BMS7890"
    sw_version:       str   = "BMS-FW-v3.2.1-ASILD"
    hw_part_number:   str   = "1234567-890-A"


@dataclass
class DTCRecord:
    code:       int
    name:       str
    status:     int   = 0x08   # 0x08 = confirmed, 0x09 = confirmed+mil on
    occ_count:  int   = 1
    freeze_soc: float = 0.0
    freeze_v:   float = 0.0
    freeze_t:   float = 0.0


# ---------------------------------------------------------------------------
# ISO-TP Transport Layer
# ---------------------------------------------------------------------------
class ISOTPEncoder:
    """Encodes/decodes ISO 15765-2 CAN transport protocol frames."""

    @staticmethod
    def encode(payload: bytes, can_id: int = 0x7E4) -> List[str]:
        """Returns list of CAN frame hex strings for given payload."""
        frames = []
        if len(payload) <= 7:
            # Single Frame
            pci = (0x00 << 4) | len(payload)
            data = bytes([pci]) + payload + bytes(7 - len(payload))
            frames.append(f"ID=0x{can_id:03X}  [{' '.join(f'{b:02X}' for b in data)}]  "
                          f"<Single Frame: {len(payload)} bytes>")
        else:
            # First Frame
            ff_len = len(payload)
            pci0 = 0x10 | ((ff_len >> 8) & 0x0F)
            pci1 = ff_len & 0xFF
            chunk0 = payload[:6]
            data0 = bytes([pci0, pci1]) + chunk0
            frames.append(f"ID=0x{can_id:03X}  [{' '.join(f'{b:02X}' for b in data0)}]  "
                          f"<First Frame: total={ff_len} bytes>")
            # Flow Control (simulated from ECU)
            frames.append(f"ID=0x{can_id^1:03X}  [30 00 0A 00 00 00 00 00]  "
                          f"<Flow Control: ContinueToSend, BS=0, STmin=10ms>")
            # Consecutive Frames
            remaining = payload[6:]
            sn = 1
            while remaining:
                chunk = remaining[:7]
                remaining = remaining[7:]
                pci_cf = 0x20 | (sn & 0x0F)
                data_cf = bytes([pci_cf]) + chunk + bytes(7 - len(chunk))
                frames.append(f"ID=0x{can_id:03X}  [{' '.join(f'{b:02X}' for b in data_cf)}]  "
                              f"<Consecutive Frame #{sn}>")
                sn = (sn + 1) & 0x0F
        return frames


# ---------------------------------------------------------------------------
# UDS Server (BMS ECU)
# ---------------------------------------------------------------------------
class BMS_UDS_Server:
    """
    Simulates the UDS server running inside the BMS ECU.
    Processes requests and generates ISO 14229-conformant responses.
    """

    POSITIVE_RESPONSE_OFFSET = 0x40

    # Data Identifier (DID) map
    DID_MAP: Dict[int, str] = {
        0xF190: "vin",
        0xF187: "hw_part_number",
        0xF189: "sw_version",
        0x4001: "soc_pct",
        0x4002: "pack_voltage_v",
        0x4003: "pack_current_a",
        0x4004: "cell_min_v",
        0x4005: "cell_max_v",
        0x4006: "cell_delta_mv",
        0x4007: "temp_max_c",
        0x4008: "temp_min_c",
        0x4009: "isolation_kohm",
        0x400A: "soh_pct",
        0x400B: "sop_dch_w",
        0x400C: "cycle_count",
    }

    # Writeable DIDs (calibration — requires Security Access)
    WRITEABLE_DIDS = {0x4010, 0x4011}  # e.g., SOC calibration offset, temp offset

    def __init__(self):
        self.data      = BMSLiveData()
        self.session   = "default"           # default / extended / programming
        self.unlocked  = False
        self.seed_cache: Optional[int] = None
        self.attempt_count = 0

        self.dtcs: List[DTCRecord] = [
            DTCRecord(0x900100, "CELL_OVER_VOLTAGE",     0x08, 2, 98.7, 422.1, 31.0),
            DTCRecord(0x900300, "CELL_OVER_TEMPERATURE", 0x09, 1, 45.3, 388.5, 63.2),
        ]

        self.routine_results: Dict[int, bytes] = {}
        self.ota_buffer      = bytearray()
        self.ota_block_seq   = 0
        self.ota_expected_size = 0

    # --- Helpers -----------------------------------------------------------
    def _neg(self, sid: int, nrc: NRC) -> bytes:
        return bytes([0x7F, sid, int(nrc)])

    def _pos(self, sid: int, data: bytes = b'') -> bytes:
        return bytes([sid + self.POSITIVE_RESPONSE_OFFSET]) + data

    def _encode_did_value(self, did: int) -> bytes:
        attr = self.DID_MAP.get(did)
        if attr is None:
            return b''
        val = getattr(self.data, attr)
        if isinstance(val, str):
            return val.encode('ascii')
        if isinstance(val, float):
            return struct.pack('>f', val)
        if isinstance(val, int):
            return struct.pack('>I', val)
        return b''

    # --- Service handlers --------------------------------------------------
    def _svc_dsc(self, req: bytes) -> bytes:
        if len(req) < 2:
            return self._neg(SID.DSC, NRC.INCORRECT_LENGTH)
        sub = req[1]
        mapping = {0x01: "default", 0x03: "extended", 0x02: "programming"}
        if sub not in mapping:
            return self._neg(SID.DSC, NRC.SUB_NOT_SUPPORTED)
        self.session = mapping[sub]
        if sub != 0x03:
            self.unlocked = False   # Programming session exit → lock
        return self._pos(SID.DSC, bytes([sub, 0x00, 0x19, 0x01, 0xF4]))

    def _svc_ecu_reset(self, req: bytes) -> bytes:
        if len(req) < 2:
            return self._neg(SID.ECU_RESET, NRC.INCORRECT_LENGTH)
        sub = req[1]
        self.session  = "default"
        self.unlocked = False
        self.attempt_count = 0
        return self._pos(SID.ECU_RESET, bytes([sub]))

    def _svc_rdbi(self, req: bytes) -> bytes:
        if len(req) < 3:
            return self._neg(SID.RDBI, NRC.INCORRECT_LENGTH)
        did = struct.unpack('>H', req[1:3])[0]
        encoded = self._encode_did_value(did)
        if not encoded:
            return self._neg(SID.RDBI, NRC.REQUEST_OUT_OF_RANGE)
        return self._pos(SID.RDBI, req[1:3] + encoded)

    def _svc_wdbi(self, req: bytes) -> bytes:
        if self.session not in ("extended", "programming"):
            return self._neg(SID.WDBI, NRC.CONDITIONS_NOT_CORRECT)
        if not self.unlocked:
            return self._neg(SID.WDBI, NRC.SECURITY_ACCESS_DENIED)
        if len(req) < 3:
            return self._neg(SID.WDBI, NRC.INCORRECT_LENGTH)
        did = struct.unpack('>H', req[1:3])[0]
        if did not in self.WRITEABLE_DIDS:
            return self._neg(SID.WDBI, NRC.REQUEST_OUT_OF_RANGE)
        return self._pos(SID.WDBI, req[1:3])

    def _svc_sa(self, req: bytes) -> bytes:
        if self.session not in ("extended", "programming"):
            return self._neg(SID.SA, NRC.CONDITIONS_NOT_CORRECT)
        if len(req) < 2:
            return self._neg(SID.SA, NRC.INCORRECT_LENGTH)
        sub = req[1]

        if sub == 0x01:  # Request Seed
            if self.attempt_count >= 5:
                return self._neg(SID.SA, NRC.EXCEEDED_NUMBER_OF_ATTEMPTS)
            self.seed_cache = int.from_bytes(os.urandom(4), 'big')
            return self._pos(SID.SA, bytes([0x02]) + self.seed_cache.to_bytes(4, 'big'))

        elif sub == 0x02:  # Send Key
            if self.seed_cache is None:
                return self._neg(SID.SA, NRC.REQUEST_SEQUENCE_ERROR)
            if len(req) < 6:
                return self._neg(SID.SA, NRC.INCORRECT_LENGTH)
            received_key = int.from_bytes(req[2:6], 'big')
            expected_key = (self.seed_cache ^ 0xBEEF1234) & 0xFFFFFFFF
            if received_key == expected_key:
                self.unlocked = True
                self.attempt_count = 0
                self.seed_cache = None
                return self._pos(SID.SA, bytes([0x02]))
            else:
                self.attempt_count += 1
                return self._neg(SID.SA, NRC.INVALID_KEY)
        return self._neg(SID.SA, NRC.SUB_NOT_SUPPORTED)

    def _svc_cdtci(self, req: bytes) -> bytes:
        if self.session != "extended":
            return self._neg(SID.CDTCI, NRC.CONDITIONS_NOT_CORRECT)
        self.dtcs.clear()
        return self._pos(SID.CDTCI)

    def _svc_rdtci(self, req: bytes) -> bytes:
        if len(req) < 2:
            return self._neg(SID.RDTCI, NRC.INCORRECT_LENGTH)
        sub = req[1]
        if sub == 0x02:  # reportDTCByStatusMask
            mask = req[2] if len(req) > 2 else 0xFF
            result = bytearray([sub])
            for dtc in self.dtcs:
                if dtc.status & mask:
                    result += dtc.code.to_bytes(3, 'big') + bytes([dtc.status])
            return self._pos(SID.RDTCI, bytes(result))
        elif sub == 0x06:  # reportDTCExtendedDataRecordByDTCNumber
            if len(req) < 5:
                return self._neg(SID.RDTCI, NRC.INCORRECT_LENGTH)
            target_code = int.from_bytes(req[2:5], 'big')
            for dtc in self.dtcs:
                if dtc.code == target_code:
                    payload = (
                        dtc.code.to_bytes(3, 'big') +
                        bytes([dtc.status, dtc.occ_count]) +
                        struct.pack('>fff', dtc.freeze_soc, dtc.freeze_v, dtc.freeze_t)
                    )
                    return self._pos(SID.RDTCI, bytes([sub]) + payload)
            return self._neg(SID.RDTCI, NRC.REQUEST_OUT_OF_RANGE)
        return self._neg(SID.RDTCI, NRC.SUB_NOT_SUPPORTED)

    def _svc_rc(self, req: bytes) -> bytes:
        if len(req) < 4:
            return self._neg(SID.RC, NRC.INCORRECT_LENGTH)
        sub = req[1]
        routine_id = struct.unpack('>H', req[2:4])[0]
        if sub == 0x01:  # startRoutine
            if routine_id == 0xE001:    # Cell Balancing Check
                result = b'\x01' + b'\x00' * 4   # 4 cells need balancing
                self.routine_results[routine_id] = result
                return self._pos(SID.RC, bytes([sub]) + req[2:4] + bytes([0x00]))
            elif routine_id == 0xE002:  # Pre-drive Check
                self.routine_results[routine_id] = b'\x01'  # OK
                return self._pos(SID.RC, bytes([sub]) + req[2:4] + bytes([0x00]))
            elif routine_id == 0xE003:  # Flash CRC verification
                if not self.unlocked:
                    return self._neg(SID.RC, NRC.SECURITY_ACCESS_DENIED)
                crc_ok = b'\x01'
                self.routine_results[routine_id] = crc_ok
                return self._pos(SID.RC, bytes([sub]) + req[2:4] + bytes([0x00]))
        elif sub == 0x03:  # requestRoutineResults
            result = self.routine_results.get(routine_id, b'\xFF')
            return self._pos(SID.RC, bytes([sub]) + req[2:4] + result)
        return self._neg(SID.RC, NRC.SUB_NOT_SUPPORTED)

    def _svc_rd(self, req: bytes) -> bytes:  # RequestDownload (OTA init)
        if self.session != "programming":
            return self._neg(SID.RD, NRC.CONDITIONS_NOT_CORRECT)
        if not self.unlocked:
            return self._neg(SID.RD, NRC.SECURITY_ACCESS_DENIED)
        # Parse memory address + size (simplified: 4-byte each)
        if len(req) < 11:
            return self._neg(SID.RD, NRC.INCORRECT_LENGTH)
        self.ota_expected_size = struct.unpack('>I', req[7:11])[0]
        self.ota_buffer = bytearray()
        self.ota_block_seq = 1
        max_block = 0x0400  # 1024 bytes per block
        return self._pos(SID.RD, bytes([0x40]) + struct.pack('>H', max_block))

    def _svc_td(self, req: bytes) -> bytes:  # TransferData (OTA chunk)
        if self.session != "programming":
            return self._neg(SID.TD, NRC.CONDITIONS_NOT_CORRECT)
        if len(req) < 3:
            return self._neg(SID.TD, NRC.INCORRECT_LENGTH)
        block_seq = req[1]
        if block_seq != self.ota_block_seq:
            return self._neg(SID.TD, NRC.REQUEST_SEQUENCE_ERROR)
        self.ota_buffer.extend(req[2:])
        self.ota_block_seq = (self.ota_block_seq + 1) & 0xFF
        return self._pos(SID.TD, bytes([block_seq]))

    def _svc_rte(self, req: bytes) -> bytes:  # RequestTransferExit
        if self.session != "programming":
            return self._neg(SID.RTE, NRC.CONDITIONS_NOT_CORRECT)
        received = len(self.ota_buffer)
        crc = hashlib.md5(self.ota_buffer).hexdigest()[:8].upper()
        return self._pos(SID.RTE, f"OK:{received}B:CRC={crc}".encode())

    # --- Main dispatch ------------------------------------------------------
    def process(self, request: bytes) -> bytes:
        if not request:
            return self._neg(0x00, NRC.GENERAL_REJECT)
        sid = request[0]
        handlers = {
            SID.DSC:      self._svc_dsc,
            SID.ECU_RESET:self._svc_ecu_reset,
            SID.RDBI:     self._svc_rdbi,
            SID.WDBI:     self._svc_wdbi,
            SID.SA:       self._svc_sa,
            SID.CDTCI:    self._svc_cdtci,
            SID.RDTCI:    self._svc_rdtci,
            SID.RC:       self._svc_rc,
            SID.RD:       self._svc_rd,
            SID.TD:       self._svc_td,
            SID.RTE:      self._svc_rte,
        }
        handler = handlers.get(sid)
        if handler is None:
            return self._neg(sid, NRC.SERVICE_NOT_SUPPORTED)
        return handler(request)


# ---------------------------------------------------------------------------
# Pretty Printer Helper
# ---------------------------------------------------------------------------
class UDSTraceLogger:
    def __init__(self):
        self.encoder = ISOTPEncoder()

    def log(self, direction: str, raw: bytes, description: str = ""):
        hex_str = " ".join(f"{b:02X}" for b in raw)
        iso_tp_frames = self.encoder.encode(raw, can_id=0x7E4 if direction == "REQ" else 0x7EC)
        print(f"\n  ┌─{'Request' if direction=='REQ' else 'Response'}{'─'*(56-len(description))} {description}")
        for frame in iso_tp_frames:
            arrow = "  ├─► " if direction == "REQ" else "  ├─◄ "
            print(f"{arrow}{frame}")
        print(f"  └─ UDS Raw: [{hex_str}]  ({len(raw)} bytes)")


# ---------------------------------------------------------------------------
# Full Diagnostic Session Demonstration
# ---------------------------------------------------------------------------
def run_full_uds_session():
    server = BMS_UDS_Server()
    logger = UDSTraceLogger()

    def transaction(req: bytes, desc: str):
        logger.log("REQ", req, desc)
        resp = server.process(req)
        logger.log("RSP", resp, "")
        return resp

    print("=" * 68)
    print(" ISO 14229 UDS Diyagnostik Protokol Simülatörü — BMS ECU (7E4h)")
    print("=" * 68)

    # 1. Default → Extended session
    transaction(bytes([0x10, 0x03]), "SID 0x10 — ExtendedDiagnosticSession (0x03)")

    # 2. Read VIN
    transaction(bytes([0x22, 0xF1, 0x90]), "SID 0x22 RDBI — DID 0xF190 Araç VIN")

    # 3. Read live BMS data
    for did, name in [(0x4001, "SoC"), (0x4002, "Paket Gerilimi"),
                      (0x4007, "Maks Sıcaklık"), (0x400A, "SoH")]:
        transaction(struct.pack('>BH', 0x22, did), f"SID 0x22 RDBI — DID 0x{did:04X} {name}")

    # 4. Read DTCs
    transaction(bytes([0x19, 0x02, 0xFF]), "SID 0x19 RDTCI — Tüm Aktif DTC'ler (mask=0xFF)")

    # 5. Read extended DTC data
    transaction(bytes([0x19, 0x06, 0x90, 0x01, 0x00]),
                "SID 0x19 RDTCI — DTC 0x900100 Freeze-Frame")

    # 6. Security Access — Request Seed
    resp_seed = transaction(bytes([0x27, 0x01]), "SID 0x27 SecurityAccess — Tohum Talebi")
    if resp_seed[0] == 0x67 and len(resp_seed) >= 6:
        seed = int.from_bytes(resp_seed[2:6], 'big')
        key  = (seed ^ 0xBEEF1234) & 0xFFFFFFFF
        transaction(bytes([0x27, 0x02]) + key.to_bytes(4, 'big'),
                    f"SID 0x27 SecurityAccess — Anahtar Gönder (seed=0x{seed:08X} ⊕ 0xBEEF1234)")
    else:
        print("  [WARN] Security seed alınamadı.")

    # 7. Routine Control — Cell Balancing Check
    transaction(bytes([0x31, 0x01, 0xE0, 0x01]), "SID 0x31 RoutineControl — Hücre Dengeleme Kontrolü")
    transaction(bytes([0x31, 0x03, 0xE0, 0x01]), "SID 0x31 RoutineControl — Sonuç Oku")

    # 8. ClearDTCs
    transaction(bytes([0x14, 0xFF, 0xFF, 0xFF]), "SID 0x14 ClearDiagnosticInformation — Tüm DTC Sil")

    # 9. Verify DTCs cleared
    transaction(bytes([0x19, 0x02, 0xFF]), "SID 0x19 RDTCI — DTC Temizleme Doğrulama")

    # 10. Transition to Programming session & OTA flow
    transaction(bytes([0x10, 0x02]), "SID 0x10 — ProgrammingSession (0x02)")
    resp_seed2 = transaction(bytes([0x27, 0x01]), "SID 0x27 SecurityAccess — Programming Tohum")
    if resp_seed2[0] == 0x67 and len(resp_seed2) >= 6:
        seed2 = int.from_bytes(resp_seed2[2:6], 'big')
        key2  = (seed2 ^ 0xBEEF1234) & 0xFFFFFFFF
        transaction(bytes([0x27, 0x02]) + key2.to_bytes(4, 'big'),
                    "SID 0x27 SecurityAccess — Programming Kilidi Aç")

    # RequestDownload: address=0x08000000, size=512 bytes, dataFormatId=0x00
    rd_req = bytes([0x34, 0x00, 0x44]) + b'\x08\x00\x00\x00' + b'\x00\x00\x02\x00'
    transaction(rd_req, "SID 0x34 RequestDownload — OTA Firmware Güncelleme Başlat")

    # Transfer 3 blocks of 128 bytes each
    fake_fw = bytes([i % 256 for i in range(128)])  # 128-byte simulated firmware chunk
    for blk in range(1, 4):
        td_req = bytes([0x36, blk]) + fake_fw[:64]
        transaction(td_req, f"SID 0x36 TransferData — Blok #{blk}")

    transaction(bytes([0x37]), "SID 0x37 RequestTransferExit — OTA Aktarım Tamamla")

    # 11. ECU Reset (soft)
    transaction(bytes([0x11, 0x03]), "SID 0x11 ECUReset — Soft Reset (Uygula & Yeniden Başlat)")

    print("\n" + "=" * 68)
    print(" UDS Diyagnostik Oturumu Tamamlandı.")
    print("=" * 68)


if __name__ == "__main__":
    run_full_uds_session()
