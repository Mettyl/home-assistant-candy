import asyncio
from collections import OrderedDict
import json
from json import JSONDecodeError
import logging
from typing import Union
from urllib.parse import urlencode

import aiohttp
from aiohttp import ClientSession
from aiolimiter import AsyncLimiter
import backoff

from ..const import WASH_REFRESH_TOUCH_PROGRAM, WASH_REFRESH_TOUCH_PROGRAM_CODE
from .decryption import Encryption, decrypt, encrypt, find_key
from .model import (
    DishwasherStatus,
    MachineState,
    OvenStatus,
    TumbleDryerStatus,
    WashingMachineStatus,
)

_LOGGER = logging.getLogger(__name__)

# Some devices reportedly can't handle too frequent requests and respond with BAD_REQUEST
# This global limiter makes sure we don't call the API too fast
# https://github.com/ofalvai/home-assistant-candy/issues/61
_LIMITER = AsyncLimiter(max_rate=1, time_period=3)


class CandyClient:
    def __init__(
        self,
        session: ClientSession,
        device_ip: str,
        encryption_key: str,
        use_encryption: bool,
    ):
        self.session = (
            session  # Session is the default HA session, shouldn't be cleaned up
        )
        self.device_ip = device_ip
        self.encryption_key = encryption_key
        self.use_encryption = use_encryption

    @backoff.on_exception(
        backoff.expo, aiohttp.ClientError, max_tries=3, logger=__name__
    )
    @backoff.on_exception(backoff.expo, TimeoutError, max_tries=3, logger=__name__)
    async def status_with_retry(
        self,
    ) -> Union[WashingMachineStatus, TumbleDryerStatus, DishwasherStatus, OvenStatus]:
        return await self.status()

    async def status(
        self,
    ) -> Union[WashingMachineStatus, TumbleDryerStatus, DishwasherStatus, OvenStatus]:
        url = _status_url(self.device_ip, self.use_encryption)
        async with _LIMITER, self.session.get(url) as resp:
            if self.use_encryption:
                resp_hex = (
                    await resp.text()
                )  # Response is hex encoded, either encrypted or not
                if self.encryption_key != "":
                    decrypted_text = decrypt(
                        self.encryption_key.encode(), bytes.fromhex(resp_hex)
                    )
                else:
                    # Response is just hex encoded without encryption (details in detect_encryption())
                    decrypted_text = bytes.fromhex(resp_hex)
                resp_json = json.loads(decrypted_text)
            else:
                resp_json = await resp.json(content_type="text/html")

            _LOGGER.debug(resp_json)

            if "statusTD" in resp_json:
                status = TumbleDryerStatus.from_json(resp_json["statusTD"])
            elif "statusLavatrice" in resp_json:
                status = WashingMachineStatus.from_json(resp_json["statusLavatrice"])
            elif "statusForno" in resp_json:
                status = OvenStatus.from_json(resp_json["statusForno"])
            elif "statusDWash" in resp_json:
                status = DishwasherStatus.from_json(resp_json["statusDWash"])
            else:
                raise Exception(
                    "Unable to detect machine type from API response", resp_json
                )

            return status

    async def start_washing_machine(
        self,
        *,
        program: int,
        program_code: int,
        selection_level: int | None = None,
        temperature: int | None = None,
        spin_speed: int | None = None,
        delay_minutes: int = 0,
    ) -> dict[str, str]:
        """Start a washing-machine program while it is in remote-control mode.

        ``spin_speed`` uses the native protocol value (for example, 8 means
        800 rpm). Optional target fields are omitted when unknown so the
        appliance can apply the defaults for the selected program.
        """
        status = await self.status()
        if not isinstance(status, WashingMachineStatus):
            raise TypeError("The connected appliance is not a washing machine")
        if not status.remote_control:
            raise ValueError(
                "Remote control is disabled; turn the program selector to Wi-Fi"
            )
        if status.machine_state is not MachineState.IDLE:
            raise ValueError("The washing machine is not idle")

        payload = build_washing_machine_start_payload(
            program=program,
            program_code=program_code,
            selection_level=selection_level,
            temperature=temperature,
            spin_speed=spin_speed,
            delay_minutes=delay_minutes,
        )
        _LOGGER.debug("Sending washing-machine start payload: %s", payload)
        return await self._write(payload)

    async def stop_washing_machine(self, *, program: int) -> dict[str, str]:
        """Stop the current remotely controlled washing-machine program."""
        payload = build_washing_machine_stop_payload(program=program)
        _LOGGER.debug("Sending washing-machine stop payload: %s", payload)
        return await self._write(payload)

    async def pause_washing_machine(self) -> dict[str, str]:
        """Pause the current remotely controlled washing-machine program."""
        status = await self.status()
        if not isinstance(status, WashingMachineStatus):
            raise TypeError("The connected appliance is not a washing machine")
        if not status.remote_control:
            raise ValueError(
                "Remote control is disabled; turn the program selector to Wi-Fi"
            )
        if status.machine_state is not MachineState.RUNNING:
            raise ValueError("The washing machine is not running")

        payload = build_washing_machine_pause_payload(paused=True)
        _LOGGER.debug("Sending washing-machine pause payload: %s", payload)
        return await self._write(payload)

    async def resume_washing_machine(self) -> dict[str, str]:
        """Resume the current remotely paused washing-machine program."""
        status = await self.status()
        if not isinstance(status, WashingMachineStatus):
            raise TypeError("The connected appliance is not a washing machine")
        if not status.remote_control:
            raise ValueError(
                "Remote control is disabled; turn the program selector to Wi-Fi"
            )
        if status.machine_state is not MachineState.PAUSED:
            raise ValueError("The washing machine is not paused")

        payload = build_washing_machine_pause_payload(paused=False)
        _LOGGER.debug("Sending washing-machine resume payload: %s", payload)
        return await self._write(payload)

    async def start_refresh_touch(self) -> dict[str, str]:
        """Start Refresh Touch after a naturally completed wash cycle."""
        status = await self.status()
        if not isinstance(status, WashingMachineStatus):
            raise TypeError("The connected appliance is not a washing machine")
        if not status.remote_control:
            raise ValueError(
                "Remote control is disabled; turn the program selector to Wi-Fi"
            )
        if status.machine_state not in (
            MachineState.FINISHED1,
            MachineState.FINISHED2,
        ):
            raise ValueError("Refresh Touch is only available after a completed wash")

        payload = build_washing_machine_refresh_touch_payload()
        _LOGGER.debug("Sending Refresh Touch payload: %s", payload)
        return await self._write(payload)

    async def _write(self, payload: str) -> dict[str, str]:
        """Send a command payload to the appliance write endpoint."""
        url = f"http://{self.device_ip}/http-write.json"
        if self.use_encryption:
            raw_payload = payload.encode()
            if self.encryption_key:
                raw_payload = encrypt(self.encryption_key.encode(), raw_payload)
            params = {"encrypted": "1", "data": raw_payload.hex()}
        else:
            params = {"encrypted": "0"}
            for field in payload.split("&"):
                name, _, value = field.partition("=")
                params[name] = value

        async with _LIMITER, self.session.get(url, params=params) as resp:
            resp.raise_for_status()
            response_text = await resp.text()
            if not response_text.strip():
                # Some Wi-Fi modules accept start commands but close the
                # connection without a response body. The subsequent status
                # refresh is the authoritative confirmation.
                return {"response": "NO_RESPONSE"}
            response = _decode_write_response(
                response_text,
                self.encryption_key if self.use_encryption else "",
            )

        if response.get("response") != "SUCCESS":
            raise ValueError(f"Candy command failed: {response}")
        return response


def build_washing_machine_start_payload(
    *,
    program: int,
    program_code: int,
    selection_level: int | None = None,
    temperature: int | None = None,
    spin_speed: int | None = None,
    delay_minutes: int = 0,
) -> str:
    """Build the local Simply-Fi command payload for starting a wash."""
    _validate_command_value("program", program, 1, 255)
    _validate_command_value("program_code", program_code, 0, 999)
    _validate_command_value("delay_minutes", delay_minutes, 0, 1440)
    if selection_level is not None:
        _validate_command_value("selection_level", selection_level, 0, 255)
    if temperature is not None:
        _validate_command_value("temperature", temperature, 0, 90)
    if spin_speed is not None:
        _validate_command_value("spin_speed", spin_speed, 0, 20)

    fields: OrderedDict[str, int] = OrderedDict(
        (("Write", 1), ("StSt", 1), ("DelVl", delay_minutes))
    )
    fields["PrNm"] = program
    fields["PrCode"] = program_code
    if temperature is not None:
        fields["TmpTgt"] = temperature
    if selection_level is not None:
        fields["SLevTgt"] = selection_level
    if spin_speed is not None:
        fields["SpdTgt"] = spin_speed
    return urlencode(fields)


def build_washing_machine_stop_payload(*, program: int) -> str:
    """Build the app-compatible payload for stopping an active wash."""
    _validate_command_value("program", program, 1, 255)
    return urlencode(
        OrderedDict((("Write", 1), ("StSt", 0), ("DelMd", 0), ("PrNm", program)))
    )


def build_washing_machine_pause_payload(*, paused: bool) -> str:
    """Build the pause/resume payload used by the official Simply-Fi app."""
    return urlencode(OrderedDict((("Pa", int(paused)),)))


def build_washing_machine_refresh_touch_payload() -> str:
    """Build the locally observed RO41274DWMSE/1-S Refresh Touch command."""
    payload = build_washing_machine_start_payload(
        program=WASH_REFRESH_TOUCH_PROGRAM,
        program_code=WASH_REFRESH_TOUCH_PROGRAM_CODE,
        selection_level=0,
        temperature=0,
        spin_speed=0,
    )
    return f"{payload}&DispTestOn=1"


def encode_write_payload(payload: str, encryption_key: str) -> str:
    """Return the hexadecimal data parameter used by encrypted writes."""
    raw_payload = payload.encode()
    if encryption_key:
        raw_payload = encrypt(encryption_key.encode(), raw_payload)
    return raw_payload.hex()


def _decode_write_response(response_text: str, encryption_key: str) -> dict[str, str]:
    """Decode a plaintext or hex/XOR encoded write response."""
    response_text = response_text.strip()
    try:
        parsed = json.loads(response_text)
    except JSONDecodeError:
        try:
            response_bytes = bytes.fromhex(response_text)
        except ValueError as err:
            raise ValueError("Invalid response from Candy write endpoint") from err
        if encryption_key:
            response_bytes = decrypt(encryption_key.encode(), response_bytes)
        try:
            parsed = json.loads(response_bytes)
        except (JSONDecodeError, UnicodeDecodeError) as err:
            raise ValueError("Invalid response from Candy write endpoint") from err

    if not isinstance(parsed, dict):
        raise TypeError("Invalid response from Candy write endpoint")
    return parsed


def _validate_command_value(name: str, value: int, minimum: int, maximum: int) -> None:
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")


async def detect_encryption(
    session: aiohttp.ClientSession, device_ip: str
) -> tuple[Encryption, str | None]:
    # noinspection PyBroadException
    try:
        _LOGGER.info("Trying to get a response without encryption (encrypted=0)...")
        url = _status_url(device_ip, use_encryption=False)
        async with _LIMITER, session.get(url) as resp:
            resp_json = await resp.json(content_type="text/html")
            assert resp_json.get("response") != "BAD REQUEST"
            _LOGGER.info(
                "Received unencrypted JSON response, no need to use key for decryption"
            )
            return Encryption.NO_ENCRYPTION, None
    except Exception as err:  # pylint: disable=broad-except
        _LOGGER.debug(err)
        _LOGGER.info(
            "Failed to get a valid response without encryption, let's try with encrypted=1..."
        )
        url = _status_url(device_ip, use_encryption=True)
        async with _LIMITER, session.get(url) as resp:
            resp_hex = await resp.text()  # Response is hex encoded encrypted data
            try:
                json.loads(bytes.fromhex(resp_hex))
            except JSONDecodeError as json_err:
                _LOGGER.info(
                    "Brute force decryption key from the encrypted response..."
                )
                _LOGGER.debug("Response: %s", resp_hex)
                key = find_key(bytes.fromhex(resp_hex))
                if key is None:
                    raise ValueError("Couldn't brute force key") from json_err

                _LOGGER.info("Using key with encrypted=1 for future requests")
                return Encryption.ENCRYPTION, key
            else:
                _LOGGER.info(
                    "Response is not encrypted (despite encryption=1 in request), no need to brute force "
                    "the key"
                )
                return Encryption.ENCRYPTION_WITHOUT_KEY, None


def _status_url(device_ip: str, use_encryption: bool) -> str:
    return f"http://{device_ip}/http-read.json?encrypted={1 if use_encryption else 0}"


# Maps JSON root keys to human-readable device type labels
_DEVICE_TYPE_LABELS: dict[str, str] = {
    "statusLavatrice": "Washing Machine",
    "statusTD": "Tumble Dryer",
    "statusDWash": "Dishwasher",
    "statusForno": "Oven",
}


async def discover_devices(
    session: aiohttp.ClientSession, subnet: str, timeout: float = 1.0
) -> dict[str, str]:
    """Scan a /24 subnet for Candy Simply-Fi devices.

    Returns a dict mapping IP address -> device type label for each device found.
    """

    async def _probe(ip: str) -> tuple[str, str] | None:
        url = f"http://{ip}/http-read.json?encrypted=0"
        try:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=timeout)
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json(content_type=None)
                for key, label in _DEVICE_TYPE_LABELS.items():
                    if key in data:
                        return ip, label
        except Exception:  # pylint: disable=broad-except
            pass
        return None

    base = ".".join(subnet.split(".")[:3])
    tasks = [_probe(f"{base}.{i}") for i in range(1, 255)]
    results = await asyncio.gather(*tasks)

    return {
        ip: label
        for result in results
        if result and (ip := result[0]) and (label := result[1])
    }
