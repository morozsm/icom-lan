# Exceptions

All exceptions inherit from `IcomLanError` for easy catch-all handling.

## Hierarchy

```
IcomLanError
├── ConnectionError
├── AuthenticationError
├── CommandError
├── TimeoutError
└── AudioError
    ├── AudioCodecBackendError
    ├── AudioFormatError
    └── AudioTranscodeError
```

## Classes

### `IcomLanError`

```python
from icom_lan import IcomLanError
```

Base exception for all icom-lan errors. Catch this to handle any library error.

```python
try:
    async with IcomRadio(...) as radio:
        ...
except IcomLanError as e:
    print(f"icom-lan error: {e}")
```

### `ConnectionError`

```python
from icom_lan import ConnectionError
```

Raised when a connection to the radio fails or is lost.

- UDP socket creation failed
- Network unreachable
- Radio dropped the connection

!!! note
    This is `icom_lan.ConnectionError`, not the built-in `builtins.ConnectionError`. Import explicitly to avoid shadowing.

### `AuthenticationError`

```python
from icom_lan import AuthenticationError
```

Raised when authentication with the radio fails.

- Wrong username or password
- Account disabled
- Too many concurrent connections

### `CommandError`

```python
from icom_lan import CommandError
```

Raised when a CI-V command is rejected by the radio (NAK response).

- Frequency out of range
- Invalid mode for current state
- Feature not supported by radio model

### `TimeoutError`

```python
from icom_lan import TimeoutError
```

Raised when an operation doesn't complete within the timeout period.

- Discovery timed out (radio not found)
- CI-V command response not received
- Status packet not received during handshake

!!! note
    This is `icom_lan.TimeoutError`, not the built-in `builtins.TimeoutError`. Import explicitly to avoid shadowing.

### `AudioError`

```python
from icom_lan import AudioError
```

Base class for audio codec/transcoding failures.

### `AudioCodecBackendError`

```python
from icom_lan import AudioCodecBackendError
```

Raised when no Opus backend is available for PCM/Opus conversion.

- `opuslib` not installed
- backend failed initialization

Typical actionable message:
`Audio codec backend unavailable; install icom-lan[audio].`

### `AudioFormatError`

```python
from icom_lan import AudioFormatError
```

Raised when provided audio frame format is invalid.

- Unsupported sample rate/channel/frame duration
- Wrong PCM frame byte length
- Empty/invalid Opus frame input

### `AudioTranscodeError`

```python
from icom_lan import AudioTranscodeError
```

Raised when encode/decode fails in the codec backend.

## Usage Patterns

### Catch specific errors

```python
from icom_lan import IcomRadio
from icom_lan.exceptions import (
    ConnectionError,
    AuthenticationError,
    CommandError,
    TimeoutError,
)

try:
    async with IcomRadio("192.168.1.100", username="u", password="p") as radio:
        await radio.set_frequency(999_999_999)
except ConnectionError:
    print("Cannot reach the radio")
except AuthenticationError:
    print("Check your credentials")
except CommandError:
    print("Radio rejected the command")
except TimeoutError:
    print("Radio not responding")
```

### Retry pattern

```python
import asyncio
from icom_lan import IcomRadio, TimeoutError

async def get_frequency_with_retry(radio, retries=3):
    for attempt in range(retries):
        try:
            return await radio.get_frequency()
        except TimeoutError:
            if attempt == retries - 1:
                raise
            await asyncio.sleep(0.5)
```
