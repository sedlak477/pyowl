import logging
import math
import serial
from typing import Iterable, Optional, Literal, Union, overload

logger = logging.getLogger(__name__)

# Numeric SimpleFOC motor settings reachable through the firmware's 'M' command, keyed by their
# Commander code without the 'M' prefix. Values are in SimpleFOC units (rad, rad/s, V, A, s).
# See https://docs.simplefoc.com/commander_motor
MOTOR_SETTINGS: dict[str, str] = {
    **{
        f"{loop}{param}": f"{loop_name} {param_name}"
        for loop, loop_name in {
            "Q": "current q PID",
            "D": "current d PID",
            "V": "velocity PID",
            "A": "angle PID",
        }.items()
        for param, param_name in {
            "P": "P gain",
            "I": "I gain",
            "D": "D gain",
            "R": "output ramp",
            "L": "output limit",
            "F": "low pass filter time constant",
        }.items()
    },
    "LV": "velocity limit",
    "LU": "voltage limit",
    "LC": "current limit",
    "R": "phase resistance",
    "I": "phase inductance",
    "ID": "d axis inductance",
    "IQ": "q axis inductance",
    "K": "KV rating",
    "SM": "sensor zero offset",
    "SE": "sensor electrical zero offset",
    "WC": "centered PWM modulation",
}

# Settings read by default in get_setting(): the position/velocity loop and the motion limits
DEFAULT_SNAPSHOT = ["AP", "AI", "AD", "AR", "AL", "VP", "VI", "VD", "VR", "VL", "VF", "LV", "LU"]

class OWL:
    """
    Interface for controlling the OWL platform via serial communication.
    """

    def __init__(
        self,
        port: str,
        baudrate: int = 115200,
        timeout: float = 10.0,
        **kwargs
    ):
        """
        Initialize the OWL interface.
        
        Args:
            port: Serial port name (e.g., '/dev/ttyUSB0' or 'COM3')
            baudrate: Serial communication speed (default: 115200)
            timeout: Read timeout in seconds (default: 10.0)
            **kwargs: Additional arguments passed to serial.Serial
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.kwargs = kwargs
        self._serial: Optional[serial.Serial] = None

    def open(self) -> None:
        """Open the serial connection."""
        if self._serial is None:
            self._serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                **self.kwargs
            )
    
    def close(self) -> None:
        """Close the serial connection."""
        if self._serial is not None and self._serial.is_open:
            self._serial.close()
            self._serial = None

    def __enter__(self) -> 'OWL':
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def write(self, data: bytes) -> int:
        """
        Write bytes to the serial port.
        
        Args:
            data: The bytes to write.
            
        Returns:
            Number of bytes written.
            
        Raises:
            RuntimeError: If serial port is not open.
        """
        if self._serial is None or not self._serial.is_open:
            raise RuntimeError("Serial port is not open")
        return self._serial.write(data)

    def read(self, size: int = 1) -> bytes:
        """
        Read bytes from the serial port.
        
        Args:
            size: Number of bytes to read.
            
        Returns:
            Bytes read.
            
        Raises:
            RuntimeError: If serial port is not open.
        """
        if self._serial is None or not self._serial.is_open:
            raise RuntimeError("Serial port is not open")
        return self._serial.read(size)
        
    def read_line(self, num_lines: int = 1) -> str:
        """
        Read a line from existing serial connection.
        
        Args:
            num_lines: Number of lines to read.
        
        Returns:
            Decoded string line stripped of whitespace.

        Raises:
            TimeoutError: If no line arrived within the read timeout.
        """
        if self._serial is None or not self._serial.is_open:
            raise RuntimeError("Serial port is not open")

        lines = ""
        for _ in range(num_lines):
            line = self._serial.readline()
            if not line:
                raise TimeoutError(f"No response from the OWL within {self._serial.timeout} s")
            lines += line.decode('utf-8', errors='replace').strip()
        return lines

    def raw_command(self, command: str, num_lines: int = 1) -> str:
        """
        Send raw text command and read response.
        It is recommended to use the higher level functions, such as set_target(), get_target(), etc., instead.
        
        Args:
            command: The command string to send.
            num_lines: Number of lines to read after sending the command.
            
        Returns:
            The response string.

        Raises:
            TimeoutError: If the OWL did not respond within the read timeout.
        """
        cmd_bytes = f"{command}\n".encode('utf-8')
        if self._serial is not None and self._serial.is_open:
            # Drop stale lines, e.g. a goto reply that arrived after its timeout, so they are not taken as this reply
            self._serial.reset_input_buffer()
        self.write(cmd_bytes)
        return self.read_line(num_lines)

    def set_target(self, target: float, unit: Literal["rad", "deg"] = "rad") -> None:
        """
        Set the target position.
        
        Args:
            target: The target position.
            unit: Unit of the target angle ("rad" for radians, "deg" for degrees). Default is "rad".
        """
        if unit == "deg":
            target = math.radians(target)
        self.raw_command(f"T{target:.3f}")

    def get_target(self, unit: Literal["rad", "deg"] = "rad") -> float:
        """
        Get the target position.
        
        Args:
            unit: Unit of the returned angle ("rad" for radians, "deg" for degrees). Default is "rad".
        
        Returns:
            The target position in the specified unit.
        """
        angle = float(self.raw_command("T"))
        if unit == "deg":
            return math.degrees(angle)
        return angle

    def get_absolute_angle(self, unit: Literal["rad", "deg"] = "rad") -> float:
        """
        Get the current absolute angle.
        The absolute angle is the angle since the last reset.
        
        Args:
            unit: Unit of the returned angle ("rad" for radians, "deg" for degrees). Default is "rad".
        
        Returns:
            The current absolute angle in the specified unit.
        """
        angle = float(self.raw_command("A"))
        if unit == "deg":
            return math.degrees(angle)
        return angle
    
    def get_mechanical_angle(self, unit: Literal["rad", "deg"] = "rad") -> float:
        """
        Get the current mechanical angle.
        The mechanical angle is the angle within the current revolution.
        
        Args:
            unit: Unit of the returned angle ("rad" for radians, "deg" for degrees). Default is "rad".
        
        Returns:
            The current mechanical angle in the specified unit.
        """
        angle = float(self.raw_command("R"))
        if unit == "deg":
            return math.degrees(angle)
        return angle

    def get_motor_voltage(self) -> float:
        """
        Get the motor voltage.
        
        Returns:
            The motor voltage in volts.
        """
        return float(self.raw_command("V"))

    def set_LED(self, on: bool) -> None:
        """
        Set the user LED state.
        
        Args:
            on: Whether the LED should be on.
        """
        self.raw_command(f"L{1 if on else 0}")

    def buzz(self, duration: int) -> None:
        """
        Buzz the buzzer for a specified duration.
        
        Args:
            duration: Duration of the buzz in milliseconds.
        """
        self.raw_command(f"B{duration}")

    def goto(self, target: float, unit: Literal["rad", "deg"] = "rad") -> None:
        """
        Move the OWL to a target position.
        Blocks until the target is reached.
        
        Args:
            target: The target position.
            unit: Unit of the target angle ("rad" for radians, "deg" for degrees). Default is "rad".

        Raises:
            TimeoutError: If the target was not reached within the read timeout, e.g. because the motor stalled.
        """
        if unit == "deg":
            target = math.radians(target)
        self.raw_command(f"G{target:.3f}")


    def _motor_setting(self, name: str, value: Optional[float] = None) -> float:
        name = name.upper()
        if name not in MOTOR_SETTINGS:
            raise ValueError(f"Unknown motor setting '{name}', expected one of {', '.join(MOTOR_SETTINGS)}")
        response = self.raw_command(f"M{name}" if value is None else f"M{name}{value}")
        # Replies look like 'PID vel| P: 0.500' (user friendly) or 'MVP0.500' (machine readable)
        try:
            return float(response.rsplit(":", 1)[-1].removeprefix(f"M{name}"))
        except ValueError:
            raise RuntimeError(f"Unexpected response to motor setting '{name}': {response!r}") from None

    @overload
    def get_setting(self, name: str) -> float: ...
    @overload
    def get_setting(self, name: Optional[Iterable[str]] = None) -> dict[str, float]: ...

    def get_setting(self, name: Union[str, Iterable[str], None] = None) -> Union[float, dict[str, float]]:
        """
        Get one or more motor settings.
        The firmware reports values with 3 decimal places.

        Args:
            name: SimpleFOC motor command code without the 'M' prefix, e.g. "VP" (see MOTOR_SETTINGS),
                or several codes. Default is the angle and velocity PID settings and the limits (DEFAULT_SNAPSHOT).

        Returns:
            The current value for a single code, otherwise a dict of code to current value.
        """
        if isinstance(name, str):
            return self._motor_setting(name)
        return {n.upper(): self._motor_setting(n) for n in (DEFAULT_SNAPSHOT if name is None else name)}

    @overload
    def set_setting(self, name: str, value: float) -> float: ...
    @overload
    def set_setting(self, name: dict[str, float]) -> dict[str, float]: ...

    def set_setting(self, name: Union[str, dict[str, float]], value: Optional[float] = None) -> Union[float, dict[str, float]]:
        """
        Set one or more motor settings.
        Settings are kept in RAM only and reset when the OWL restarts.

        Args:
            name: SimpleFOC motor command code without the 'M' prefix, e.g. "VP" (see MOTOR_SETTINGS),
                or a dict of codes to new values, which are set in order.
            value: The new value when setting a single code.

        Returns:
            The value read back from the OWL for a single code, otherwise a dict of code to read back value.
        """
        if isinstance(name, str):
            if value is None:
                raise TypeError("set_setting() needs a value when setting a single code")
            return self._motor_setting(name, value)
        return {n.upper(): self._motor_setting(n, v) for n, v in name.items()}
