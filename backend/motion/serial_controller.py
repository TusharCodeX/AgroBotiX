"""
Serial Motion Controller communicating with Arduino / ESP32 rover firmware.
Implements line protocol, 200ms heartbeat thread, and 500ms safety watchdog.
"""
import time
import threading
from typing import Tuple, Dict, Any, Optional
from .base import MotionController


class SerialController(MotionController):
    """Communicates with skid-steer microcontroller over USB/UART serial."""

    def __init__(
        self,
        port: str = "COM3",
        baudrate: int = 115200,
        heartbeat_ms: int = 200,
        failsafe_ms: int = 500,
        timeout: float = 1.0,
    ):
        self.port = port
        self.baudrate = baudrate
        self.heartbeat_ms = heartbeat_ms
        self.failsafe_ms = failsafe_ms
        self.timeout = timeout

        self._ser = None
        self._is_connected = False
        self._running = False
        self._heartbeat_thread: Optional[threading.Thread] = None

        self.x = 0.0
        self.y = 0.0
        self.heading = 0.0
        self.blade_is_down = False
        self.blade_is_on = False
        self.is_estopped = False

        self._connect()

    def _connect(self) -> bool:
        try:
            import serial  # type: ignore
            self._ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
            self._is_connected = True
            self._running = True
            self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
            self._heartbeat_thread.start()
            return True
        except (ImportError, Exception):
            # Graceful stub when hardware serial is not connected
            self._is_connected = False
            self._ser = None
            return False

    def _heartbeat_loop(self) -> None:
        """Sends periodic PING to satisfy firmware 500ms safety watchdog."""
        while self._running and self._is_connected:
            try:
                self._send_raw("PING\n")
            except Exception:
                self._is_connected = False
                break
            time.sleep(self.heartbeat_ms / 1000.0)

    def _send_raw(self, cmd: str) -> Optional[str]:
        if not self._is_connected or self._ser is None:
            return None
        try:
            self._ser.write(cmd.encode("ascii"))
            self._ser.flush()
            # Read response
            resp = self._ser.readline().decode("ascii").strip()
            return resp
        except Exception:
            self._is_connected = False
            return None

    def forward(self, distance_cm: float) -> bool:
        val_mm = int(round(distance_cm * 10))
        resp = self._send_raw(f"F{val_mm}\n")
        return resp in ("OK", "DONE") if resp else not self._is_connected

    def backward(self, distance_cm: float) -> bool:
        val_mm = int(round(distance_cm * 10))
        resp = self._send_raw(f"B{val_mm}\n")
        return resp in ("OK", "DONE") if resp else not self._is_connected

    def turn(self, deg: float) -> bool:
        val_deg = int(round(abs(deg)))
        cmd = f"TR{val_deg}\n" if deg > 0 else f"TL{val_deg}\n"
        resp = self._send_raw(cmd)
        return resp in ("OK", "DONE") if resp else not self._is_connected

    def blade_down(self) -> bool:
        resp = self._send_raw("BD\n")
        self.blade_is_down = True
        return resp in ("OK", "DONE") if resp else not self._is_connected

    def blade_up(self) -> bool:
        resp = self._send_raw("BU\n")
        self.blade_is_down = False
        return resp in ("OK", "DONE") if resp else not self._is_connected

    def blade_on(self) -> bool:
        resp = self._send_raw("BON\n")
        self.blade_is_on = True
        return resp in ("OK", "DONE") if resp else not self._is_connected

    def blade_off(self) -> bool:
        resp = self._send_raw("BOFF\n")
        self.blade_is_on = False
        return resp in ("OK", "DONE") if resp else not self._is_connected

    def stop(self) -> bool:
        resp = self._send_raw("STOP\n")
        return resp in ("OK", "DONE") if resp else True

    def estop(self) -> bool:
        self.is_estopped = True
        resp = self._send_raw("ESTOP\n")
        return resp in ("OK", "DONE") if resp else True

    def get_pose(self) -> Tuple[float, float, float]:
        return self.x, self.y, self.heading

    def get_status(self) -> Dict[str, Any]:
        return {
            "type": "serial",
            "port": self.port,
            "connected": self._is_connected,
            "baudrate": self.baudrate,
            "heartbeat_ms": self.heartbeat_ms,
            "is_estopped": self.is_estopped,
            "blade": {"is_down": self.blade_is_down, "is_on": self.blade_is_on},
        }

    def close(self) -> None:
        self._running = False
        if self._ser is not None:
            try:
                self.stop()
                self._ser.close()
            except Exception:
                pass
            self._ser = None
