# pyowl

This module provides high-level control for the OWL platform via serial communication.

## Installation

To install the package, we recommend using [uv](https://github.com/astral-sh/uv):

```bash
uv add git+https://github.com/LENS-TUGraz/pyowl.git
```

Alternatively, you can use standard pip:

```bash
pip install git+https://github.com/LENS-TUGraz/pyowl.git
```


## Usage

The recommended way to use `pyowl` is with a context manager, which handles cleanup automatically:

```python
from pyowl import OWL

with OWL(port='/dev/ttyUSB0') as owl:
    # Set target position (in radians)
    owl.set_target(3.14159)  # Set target to π radians
    owl.set_target(180, unit="deg")  # Set target to 180°
    
    # Get current target position
    target = owl.get_target()
    print(f"Target: {target} rad")
    
    # Get current absolute angle in radians
    absolute_angle = owl.get_absolute_angle()
    print(f"Absolute angle: {absolute_angle} rad")
    
    # Get current mechanical angle (within current revolution) in degrees
    mechanical_angle = owl.get_mechanical_angle(unit="deg")
    print(f"Mechanical angle: {mechanical_angle}°")
```

### Basic Example

When not using the context manager, you must manually ensure the connection is opened and closed:

```python
from pyowl import OWL

owl = OWL(port='/dev/ttyUSB0')
owl.open()

try:
    # Set target position
    owl.set_target(1.5708)  # Set target to π/2 radians
    
    # Get position information
    target = owl.get_target()
    absolute = owl.get_absolute_angle()
    mechanical = owl.get_mechanical_angle()
    
    print(f"Target: {target} rad")
    print(f"Absolute: {absolute} rad")
    print(f"Mechanical: {mechanical} rad")
finally:
    owl.close()
```


## API

### `OWL` Class

**Constructor**:
`OWL(port: str, baudrate: int = 115200, timeout: float = 10.0, **kwargs)`

- `port`: The serial port (e.g., `/dev/ttyUSB0` on Linux, `COM3` on Windows).
- `baudrate`: Serial baud rate (default: 115200).
- `timeout`: Read timeout in seconds (default: 10.0).
- `**kwargs`: Additional arguments passed to `serial.Serial`.

**Methods**:

- `open()`: Opens the serial connection.
- `close()`: Closes the serial connection.
- `write(data: bytes) -> int`: Writes raw bytes to the device. Returns the number of bytes written.
- `read(size: int = 1) -> bytes`: Reads raw bytes from the device.
- `read_line(num_lines: int = 1) -> str`: Reads one or more lines of text, decoded as UTF-8.
- `raw_command(command: str, num_lines: int = 1) -> str`: Sends a raw text command and reads the response. It is recommended to use the higher-level functions instead.
- `set_target(target: float, unit: Literal["rad", "deg"] = "rad") -> None`: Sets the target position.
- `get_target(unit: Literal["rad", "deg"] = "rad") -> float`: Gets the current target position.
- `get_absolute_angle(unit: Literal["rad", "deg"] = "rad") -> float`: Gets the current absolute angle (since last reset).
- `get_mechanical_angle(unit: Literal["rad", "deg"] = "rad") -> float`: Gets the current mechanical angle (within current revolution).
- `get_motor_voltage() -> float`: Gets the motor voltage in volts.
- `set_LED(on: bool) -> None`: Sets the user LED state.
- `buzz(duration: int) -> None`: Buzzes the buzzer for a specified duration in milliseconds.
- `goto(target: float, unit: Literal["rad", "deg"] = "rad") -> None`: Moves the OWL to a target position. Blocks until the target is reached.

## Related resources

[owl-firmware](https://github.com/sedlak477/owl-firmware): The firmware for the OWL platform.  
[owl-ranger](https://github.com/sedlak477/owl-ranger): A script for stepping through some orientations and recording measurements.  
[owl-hardware](https://github.com/sedlak477/owl-hardware): Hardware design files for the OWL platform.  
[Dataset](https://doi.org/10.3217/kh254-z8374): Orientation-diverse BLE Channel Sounding and UWB ranging measurements recorded with the OWL.

## AI Disclosure

Large parts of the project were created with the help of AI tooling.
