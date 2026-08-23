from unittest.mock import AsyncMock

from homeassistant.helpers.aiohttp_client import async_get_clientsession
import pytest
from pytest_homeassistant_custom_component.common import load_fixture

from custom_components.candy.client import (
    CandyClient,
    Encryption,
    build_washing_machine_pause_payload,
    build_washing_machine_refresh_touch_payload,
    build_washing_machine_start_payload,
    build_washing_machine_stop_payload,
    detect_encryption,
    encode_write_payload,
)
from custom_components.candy.client.model import (
    DishwasherStatus,
    MachineState,
    WashingMachineStatus,
    WashProgramState,
)

from .common import (
    TEST_ENCRYPTED_HEX_RESPONSE,
    TEST_ENCRYPTION_KEY,
    TEST_ENCRYPTION_KEY_EMPTY,
    TEST_IP,
    TEST_UNENCRYPTED_HEX_RESPONSE,
)


@pytest.mark.parametrize("expected_lingering_tasks", [True])
async def test_idle(hass, aioclient_mock):
    """Test parsing the status when turning on the machine and selecting WiFi mode."""

    aioclient_mock.get(
        f"http://{TEST_IP}/http-read.json",
        text=load_fixture("washing_machine/idle.json"),
    )

    client = CandyClient(
        async_get_clientsession(hass),
        device_ip=TEST_IP,
        encryption_key=TEST_ENCRYPTION_KEY_EMPTY,
        use_encryption=False,
    )
    status = await client.status()

    assert isinstance(status, WashingMachineStatus)
    assert status.machine_state is MachineState.IDLE
    assert status.program_state is WashProgramState.STOPPED
    assert status.spin_speed == 800
    assert status.temp == 40
    assert status.selection_level == 0


def test_build_washing_machine_start_payload():
    payload = build_washing_machine_start_payload(
        program=7,
        program_code=7,
        selection_level=1,
        temperature=30,
        spin_speed=8,
    )

    assert payload == (
        "Write=1&StSt=1&DelVl=0&PrNm=7&PrCode=7&TmpTgt=30&SLevTgt=1&SpdTgt=8"
    )


def test_build_washing_machine_start_payload_validates_values():
    with pytest.raises(ValueError, match="selection_level"):
        build_washing_machine_start_payload(
            program=7,
            program_code=7,
            selection_level=256,
        )


def test_build_washing_machine_delayed_start_payload_uses_minutes():
    payload = build_washing_machine_start_payload(
        program=14,
        program_code=65,
        selection_level=1,
        delay_minutes=435,
    )

    assert payload == "Write=1&StSt=1&DelVl=435&PrNm=14&PrCode=65&SLevTgt=1"


def test_build_washing_machine_delayed_start_validates_minutes():
    with pytest.raises(ValueError, match="delay_minutes"):
        build_washing_machine_start_payload(
            program=14,
            program_code=65,
            delay_minutes=1441,
        )


def test_build_washing_machine_stop_payload():
    assert (
        build_washing_machine_stop_payload(program=13)
        == "Write=1&StSt=0&DelMd=0&PrNm=13"
    )


def test_build_washing_machine_pause_and_resume_payloads():
    assert build_washing_machine_pause_payload(paused=True) == "Pa=1"
    assert build_washing_machine_pause_payload(paused=False) == "Pa=0"


def test_build_washing_machine_refresh_touch_payload():
    assert build_washing_machine_refresh_touch_payload() == (
        "Write=1&StSt=1&DelVl=0&PrNm=16&PrCode=41&TmpTgt=0&"
        "SLevTgt=0&SpdTgt=0&DispTestOn=1"
    )


def test_encode_write_payload_round_trip():
    payload = "Write=1&StSt=0&PrNm=7"

    encrypted_hex = encode_write_payload(payload, TEST_ENCRYPTION_KEY)

    encrypted = bytes.fromhex(encrypted_hex)
    key = TEST_ENCRYPTION_KEY.encode()
    decrypted = bytes(
        byte ^ key[index % len(key)] for index, byte in enumerate(encrypted)
    )
    assert decrypted.decode() == payload


async def test_encrypted_write(hass, aioclient_mock):
    payload = "Write=1&StSt=0&PrNm=7"
    request_data = encode_write_payload(payload, TEST_ENCRYPTION_KEY)
    response_data = encode_write_payload('{"response":"SUCCESS"}', TEST_ENCRYPTION_KEY)
    aioclient_mock.get(
        f"http://{TEST_IP}/http-write.json?encrypted=1&data={request_data}",
        text=response_data,
    )
    client = CandyClient(
        async_get_clientsession(hass),
        device_ip=TEST_IP,
        encryption_key=TEST_ENCRYPTION_KEY,
        use_encryption=True,
    )

    response = await client._write(payload)

    assert response == {"response": "SUCCESS"}


async def test_unencrypted_write(hass, aioclient_mock):
    payload = "Write=1&StSt=0&PrNm=7"
    aioclient_mock.get(
        f"http://{TEST_IP}/http-write.json?encrypted=0&Write=1&StSt=0&PrNm=7",
        json={"response": "SUCCESS"},
    )
    client = CandyClient(
        async_get_clientsession(hass),
        device_ip=TEST_IP,
        encryption_key="",
        use_encryption=False,
    )

    response = await client._write(payload)

    assert response == {"response": "SUCCESS"}


async def test_encrypted_write_accepts_empty_response(hass, aioclient_mock):
    payload = "Write=1&StSt=1&PrNm=7&PrCode=7"
    request_data = encode_write_payload(payload, TEST_ENCRYPTION_KEY)
    aioclient_mock.get(
        f"http://{TEST_IP}/http-write.json?encrypted=1&data={request_data}",
        text="",
    )
    client = CandyClient(
        async_get_clientsession(hass),
        device_ip=TEST_IP,
        encryption_key=TEST_ENCRYPTION_KEY,
        use_encryption=True,
    )

    response = await client._write(payload)

    assert response == {"response": "NO_RESPONSE"}


async def test_start_requires_remote_control(hass):
    status = WashingMachineStatus.from_json(
        {
            "WiFiStatus": "0",
            "MachMd": "1",
            "Pr": "7",
            "PrPh": "0",
            "PrCode": "7",
            "SLevel": "1",
            "Temp": "30",
            "SpinSp": "8",
            "RemTime": "840",
        }
    )
    client = CandyClient(
        async_get_clientsession(hass),
        device_ip=TEST_IP,
        encryption_key=TEST_ENCRYPTION_KEY,
        use_encryption=True,
    )
    client.status = AsyncMock(return_value=status)

    with pytest.raises(ValueError, match="Remote control is disabled"):
        await client.start_washing_machine(program=7, program_code=7)


async def test_refresh_touch_requires_completed_wash(hass):
    status = WashingMachineStatus.from_json(
        {
            "WiFiStatus": "1",
            "MachMd": "1",
            "Pr": "14",
            "PrPh": "0",
            "PrCode": "65",
            "SLevel": "3",
            "Temp": "60",
            "SpinSp": "10",
            "RemTime": "0",
        }
    )
    client = CandyClient(
        async_get_clientsession(hass),
        device_ip=TEST_IP,
        encryption_key=TEST_ENCRYPTION_KEY,
        use_encryption=True,
    )
    client.status = AsyncMock(return_value=status)

    with pytest.raises(ValueError, match="only available after a completed wash"):
        await client.start_refresh_touch()


async def test_refresh_touch_sends_observed_command(hass):
    status = WashingMachineStatus.from_json(
        {
            "WiFiStatus": "1",
            "MachMd": "7",
            "Pr": "14",
            "PrPh": "0",
            "PrCode": "0",
            "SLevel": "3",
            "Temp": "60",
            "SpinSp": "10",
            "RemTime": "240",
        }
    )
    client = CandyClient(
        async_get_clientsession(hass),
        device_ip=TEST_IP,
        encryption_key=TEST_ENCRYPTION_KEY,
        use_encryption=True,
    )
    client.status = AsyncMock(return_value=status)
    client._write = AsyncMock(return_value={"response": "SUCCESS"})

    response = await client.start_refresh_touch()

    assert response == {"response": "SUCCESS"}
    client._write.assert_awaited_once_with(
        build_washing_machine_refresh_touch_payload()
    )


async def test_pause_requires_running_state_and_sends_official_command(hass):
    running = WashingMachineStatus.from_json(
        {
            "WiFiStatus": "1",
            "MachMd": "2",
            "Pr": "7",
            "PrPh": "2",
            "PrCode": "7",
            "SLevel": "1",
            "Temp": "30",
            "SpinSp": "8",
            "RemTime": "840",
        }
    )
    client = CandyClient(
        async_get_clientsession(hass),
        device_ip=TEST_IP,
        encryption_key=TEST_ENCRYPTION_KEY,
        use_encryption=True,
    )
    client.status = AsyncMock(return_value=running)
    client._write = AsyncMock(return_value={"response": "SUCCESS"})

    await client.pause_washing_machine()

    client._write.assert_awaited_once_with("Pa=1")


async def test_resume_requires_paused_state_and_sends_official_command(hass):
    paused = WashingMachineStatus.from_json(
        {
            "WiFiStatus": "1",
            "MachMd": "3",
            "Pr": "7",
            "PrPh": "2",
            "PrCode": "7",
            "SLevel": "1",
            "Temp": "30",
            "SpinSp": "8",
            "RemTime": "840",
        }
    )
    client = CandyClient(
        async_get_clientsession(hass),
        device_ip=TEST_IP,
        encryption_key=TEST_ENCRYPTION_KEY,
        use_encryption=True,
    )
    client.status = AsyncMock(return_value=paused)
    client._write = AsyncMock(return_value={"response": "SUCCESS"})

    await client.resume_washing_machine()

    client._write.assert_awaited_once_with("Pa=0")


async def test_delayed_start_wait(hass, aioclient_mock):
    """Test parsing the status when machine is waiting for a delayed start wash cycle."""
    aioclient_mock.get(
        f"http://{TEST_IP}/http-read.json",
        text=load_fixture("washing_machine/delayed_start_wait.json"),
    )

    client = CandyClient(
        async_get_clientsession(hass),
        device_ip=TEST_IP,
        encryption_key=TEST_ENCRYPTION_KEY_EMPTY,
        use_encryption=False,
    )
    status = await client.status()

    assert isinstance(status, WashingMachineStatus)
    assert status.machine_state is MachineState.DELAYED_START_PROGRAMMED
    assert status.program_state is WashProgramState.STOPPED
    assert status.remaining_minutes == 50


async def test_no_fillr_property(hass, aioclient_mock):
    """Test parsing the status when response doesn't contain the FillR property."""
    aioclient_mock.get(
        f"http://{TEST_IP}/http-read.json",
        text=load_fixture("washing_machine/no_fillr.json"),
    )

    client = CandyClient(
        async_get_clientsession(hass),
        device_ip=TEST_IP,
        encryption_key=TEST_ENCRYPTION_KEY_EMPTY,
        use_encryption=False,
    )
    status = await client.status()

    assert isinstance(status, WashingMachineStatus)
    assert status.machine_state is MachineState.IDLE
    assert status.fill_percent is None


async def test_detect_no_encryption(hass, aioclient_mock):
    aioclient_mock.get(
        f"http://{TEST_IP}/http-read.json?encrypted=0",
        text=load_fixture("washing_machine/idle.json"),
    )

    encryption_type, key = await detect_encryption(
        async_get_clientsession(hass), TEST_IP
    )

    assert encryption_type is Encryption.NO_ENCRYPTION
    assert key is None


async def test_detect_encryption_key(hass, aioclient_mock):
    aioclient_mock.get(
        f"http://{TEST_IP}/http-read.json?encrypted=0", json={"response": "BAD REQUEST"}
    )

    aioclient_mock.get(
        f"http://{TEST_IP}/http-read.json?encrypted=1", text=TEST_ENCRYPTED_HEX_RESPONSE
    )

    encryption_type, key = await detect_encryption(
        async_get_clientsession(hass), TEST_IP
    )

    assert encryption_type is Encryption.ENCRYPTION
    assert key == TEST_ENCRYPTION_KEY


async def test_detect_encryption_without_key(hass, aioclient_mock):
    aioclient_mock.get(
        f"http://{TEST_IP}/http-read.json?encrypted=0", json={"response": "BAD REQUEST"}
    )

    aioclient_mock.get(
        f"http://{TEST_IP}/http-read.json?encrypted=1",
        text=TEST_UNENCRYPTED_HEX_RESPONSE,
    )

    encryption_type, key = await detect_encryption(
        async_get_clientsession(hass), TEST_IP
    )

    assert encryption_type is Encryption.ENCRYPTION_WITHOUT_KEY
    assert key is None


async def test_status_encryption_with_key(hass, aioclient_mock):
    aioclient_mock.get(
        f"http://{TEST_IP}/http-read.json",
        text="2F7C6B441B390C094C3C42093A023429764B1A403343714A6B3D503902342E073D535B6F086854653240386F2E0C23283714243F4B250A0D1A7313085D416B4C5E78686F6A3E191C570D662C1E0B657B76434361344071611A0454390C2026333D120E6F0368484A14443B44644114353503151E4D25084A026B016F416E4D485D53353F5C23163D562613774F53656D597B68441B0F1B071A73137D4F4F4A4B5D78431D4B251F1A592413774F337263787C6B4430683D104C3B50091F1A657B76414361344071611A0641280327282E263E11391B705A581A653C47646A6505311D00346A3E191A4C6B0B6F5D416B4C5E78686F6B2F153C5124546F5741767364534D403343714A7520423E3E022B35764B437C1B66756231401300041034133D1F12281B705A581A653C47646A650E24140F0956250A4A026B016F416E4D485D5333284A2F0C4A026B016F416E4D485D5322255C29133D486B0B6F5D416B4C5E78686F4B7B5A521A7B136160694E487603536F0368484A14443B4464413572764B437F1B6675623140133F59417D6365534D403343714A4A7C13774F53656D597B68441B384E4A026B016F416E4D485D53137A1B705A5B1A653C47646A65336C535B6F086854653240386F1F5A657B763F3401756854653240386F1F5272636E53506F3440711535434C",  # pylint: disable=line-too-long
    )

    client = CandyClient(
        async_get_clientsession(hass),
        device_ip=TEST_IP,
        encryption_key="TqaM9Jxh8I1MmcGA",
        use_encryption=True,
    )
    status = await client.status()

    assert isinstance(status, DishwasherStatus)


async def test_status_encryption_without_key(hass, aioclient_mock):
    aioclient_mock.get(
        f"http://{TEST_IP}/http-read.json",
        text="7B0D0A20202020227374617475734C6176617472696365223A7B0D0A2020202020202020202020202257694669537461747573223A2230222C0D0A20202020202020202020202022457272223A22323535222C0D0A202020202020202020202020224D6163684D64223A2232222C0D0A202020202020202020202020225072223A223133222C0D0A2020202020202020202020202250725068223A2235222C0D0A20202020202020202020202022534C6576656C223A22323535222C0D0A2020202020202020202020202254656D70223A2230222C0D0A202020202020202020202020225370696E5370223A2230222C0D0A202020202020202020202020224F707431223A2230222C0D0A202020202020202020202020224F707432223A2230222C0D0A202020202020202020202020224F707433223A2230222C0D0A202020202020202020202020224F707434223A2230222C0D0A202020202020202020202020224F707435223A2230222C0D0A202020202020202020202020224F707436223A2230222C0D0A202020202020202020202020224F707437223A2230222C0D0A202020202020202020202020224F707438223A2230222C0D0A20202020202020202020202022537465616D223A2230222C0D0A2020202020202020202020202244727954223A2230222C0D0A2020202020202020202020202244656C56616C223A22323535222C0D0A2020202020202020202020202252656D54696D65223A223130222C0D0A202020202020202020202020225265636970654964223A2230222C0D0A20202020202020202020202022436865636B55705374617465223A2230220D0A202020207D0D0A7D",  # pylint: disable=line-too-long
    )

    client = CandyClient(
        async_get_clientsession(hass),
        device_ip=TEST_IP,
        encryption_key="",
        use_encryption=True,
    )
    status = await client.status()

    assert isinstance(status, WashingMachineStatus)
