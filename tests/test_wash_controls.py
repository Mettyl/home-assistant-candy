"""Tests for washing-machine select and button entities."""

from datetime import datetime
from unittest.mock import patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry
from pytest_homeassistant_custom_component.common import load_fixture
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.candy.const import (
    CONF_ENABLE_WASH_CONTROL,
    DOMAIN,
    UNIQUE_ID_WASH_ANTI_CREASE,
    UNIQUE_ID_WASH_AQUAPLUS,
    UNIQUE_ID_WASH_DELAY_CONTROL,
    UNIQUE_ID_WASH_EXTRA_RINSES_CONTROL,
    UNIQUE_ID_WASH_GOOD_NIGHT,
    UNIQUE_ID_WASH_HYGIENE,
    UNIQUE_ID_WASH_PAUSE,
    UNIQUE_ID_WASH_PRE_WASH,
    UNIQUE_ID_WASH_PROGRAM_CONTROL,
    UNIQUE_ID_WASH_REFRESH_TOUCH,
    UNIQUE_ID_WASH_RESUME,
    UNIQUE_ID_WASH_SCHEDULE,
    UNIQUE_ID_WASH_SOIL_LEVEL_CONTROL,
    UNIQUE_ID_WASH_SPIN_SPEED_CONTROL,
    UNIQUE_ID_WASH_START,
    UNIQUE_ID_WASH_STOP,
    UNIQUE_ID_WASH_TEMPERATURE_CONTROL,
)

from .common import init_integration


def _entity_id(hass: HomeAssistant, platform: str, unique_id: str) -> str:
    registry = entity_registry.async_get(hass)
    entity_id = registry.async_get_entity_id(platform, DOMAIN, unique_id)
    assert entity_id
    return entity_id


async def test_wash_control_selects(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
):
    await init_integration(
        hass,
        aioclient_mock,
        load_fixture("washing_machine/idle.json"),
        enable_wash_control=True,
    )
    entry_id = hass.config_entries.async_entries(DOMAIN)[0].entry_id
    program_id = _entity_id(
        hass, "select", UNIQUE_ID_WASH_PROGRAM_CONTROL.format(entry_id)
    )
    temperature_id = _entity_id(
        hass, "select", UNIQUE_ID_WASH_TEMPERATURE_CONTROL.format(entry_id)
    )
    spin_id = _entity_id(
        hass, "select", UNIQUE_ID_WASH_SPIN_SPEED_CONTROL.format(entry_id)
    )
    soil_id = _entity_id(
        hass, "select", UNIQUE_ID_WASH_SOIL_LEVEL_CONTROL.format(entry_id)
    )
    rinses_id = _entity_id(
        hass, "select", UNIQUE_ID_WASH_EXTRA_RINSES_CONTROL.format(entry_id)
    )
    aquaplus_id = _entity_id(hass, "switch", UNIQUE_ID_WASH_AQUAPLUS.format(entry_id))
    delay_id = _entity_id(hass, "time", UNIQUE_ID_WASH_DELAY_CONTROL.format(entry_id))

    assert hass.states.get(program_id).state == "Special 39'"
    assert hass.states.get(temperature_id).state == "40 °C"
    assert hass.states.get(spin_id).state == "800 rpm"
    assert hass.states.get(soil_id).state == "Program default"
    assert hass.states.get(rinses_id).state == "Program default"
    assert hass.states.get(aquaplus_id).state == "off"
    assert hass.states.get(delay_id).state == "unknown"

    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": program_id, "option": "Rapid 14'"},
        blocking=True,
    )

    assert hass.states.get(program_id).state == "Rapid 14'"
    assert hass.states.get(temperature_id).state == "Program default"
    assert hass.states.get(spin_id).state == "Program default"
    assert hass.states.get(temperature_id).attributes["options"] == [
        "Program default",
        "Cold",
        "20 °C",
        "30 °C",
    ]
    assert hass.states.get(soil_id).attributes["options"] == ["Program default"]


async def test_start_uses_selected_values(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
):
    await init_integration(
        hass,
        aioclient_mock,
        load_fixture("washing_machine/idle.json"),
        enable_wash_control=True,
    )
    entry_id = hass.config_entries.async_entries(DOMAIN)[0].entry_id
    program_id = _entity_id(
        hass, "select", UNIQUE_ID_WASH_PROGRAM_CONTROL.format(entry_id)
    )
    temperature_id = _entity_id(
        hass, "select", UNIQUE_ID_WASH_TEMPERATURE_CONTROL.format(entry_id)
    )
    spin_id = _entity_id(
        hass, "select", UNIQUE_ID_WASH_SPIN_SPEED_CONTROL.format(entry_id)
    )
    soil_id = _entity_id(
        hass, "select", UNIQUE_ID_WASH_SOIL_LEVEL_CONTROL.format(entry_id)
    )
    rinses_id = _entity_id(
        hass, "select", UNIQUE_ID_WASH_EXTRA_RINSES_CONTROL.format(entry_id)
    )
    pre_wash_id = _entity_id(hass, "switch", UNIQUE_ID_WASH_PRE_WASH.format(entry_id))
    good_night_id = _entity_id(
        hass, "switch", UNIQUE_ID_WASH_GOOD_NIGHT.format(entry_id)
    )
    delay_id = _entity_id(hass, "time", UNIQUE_ID_WASH_DELAY_CONTROL.format(entry_id))
    start_id = _entity_id(hass, "button", UNIQUE_ID_WASH_START.format(entry_id))

    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": program_id, "option": "Cotton"},
        blocking=True,
    )
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": temperature_id, "option": "30 °C"},
        blocking=True,
    )
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": spin_id, "option": "800 rpm"},
        blocking=True,
    )
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": soil_id, "option": "Light"},
        blocking=True,
    )
    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": pre_wash_id}, blocking=True
    )
    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": good_night_id}, blocking=True
    )
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": rinses_id, "option": "+2 rinses"},
        blocking=True,
    )
    await hass.services.async_call(
        "time",
        "set_value",
        {"entity_id": delay_id, "time": "07:15:00"},
        blocking=True,
    )

    with patch(
        "custom_components.candy.client.CandyClient.start_washing_machine"
    ) as start:
        await hass.services.async_call(
            "button", "press", {"entity_id": start_id}, blocking=True
        )

    start.assert_awaited_once_with(
        program=14,
        program_code=65,
        selection_level=1,
        temperature=30,
        spin_speed=8,
        option_mask=41,
        delay_minutes=0,
    )


async def test_schedule_uses_minutes_until_selected_wall_clock_time(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
):
    await init_integration(
        hass,
        aioclient_mock,
        load_fixture("washing_machine/idle.json"),
        enable_wash_control=True,
    )
    entry_id = hass.config_entries.async_entries(DOMAIN)[0].entry_id
    delay_id = _entity_id(hass, "time", UNIQUE_ID_WASH_DELAY_CONTROL.format(entry_id))
    schedule_id = _entity_id(hass, "button", UNIQUE_ID_WASH_SCHEDULE.format(entry_id))

    assert hass.states.get(schedule_id).state == "unavailable"

    await hass.services.async_call(
        "time",
        "set_value",
        {"entity_id": delay_id, "time": "07:15:00"},
        blocking=True,
    )

    assert hass.states.get(delay_id).state == "07:15:00"
    assert hass.states.get(schedule_id).state != "unavailable"

    with (
        patch(
            "custom_components.candy.button.dt_util.now",
            return_value=datetime.fromisoformat("2026-08-23T06:00:00+02:00"),
        ),
        patch(
            "custom_components.candy.client.CandyClient.start_washing_machine"
        ) as start,
    ):
        await hass.services.async_call(
            "button", "press", {"entity_id": schedule_id}, blocking=True
        )

    start.assert_awaited_once_with(
        program=1,
        program_code=136,
        selection_level=1,
        temperature=40,
        spin_speed=8,
        option_mask=0,
        delay_minutes=75,
    )


async def test_options_follow_selected_program(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
):
    await init_integration(
        hass,
        aioclient_mock,
        load_fixture("washing_machine/idle.json"),
        enable_wash_control=True,
    )
    entry_id = hass.config_entries.async_entries(DOMAIN)[0].entry_id
    program_id = _entity_id(
        hass, "select", UNIQUE_ID_WASH_PROGRAM_CONTROL.format(entry_id)
    )
    rinses_id = _entity_id(
        hass, "select", UNIQUE_ID_WASH_EXTRA_RINSES_CONTROL.format(entry_id)
    )
    option_ids = {
        "pre_wash": _entity_id(
            hass, "switch", UNIQUE_ID_WASH_PRE_WASH.format(entry_id)
        ),
        "hygiene": _entity_id(hass, "switch", UNIQUE_ID_WASH_HYGIENE.format(entry_id)),
        "anti_crease": _entity_id(
            hass, "switch", UNIQUE_ID_WASH_ANTI_CREASE.format(entry_id)
        ),
        "good_night": _entity_id(
            hass, "switch", UNIQUE_ID_WASH_GOOD_NIGHT.format(entry_id)
        ),
        "aquaplus": _entity_id(
            hass, "switch", UNIQUE_ID_WASH_AQUAPLUS.format(entry_id)
        ),
    }

    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": program_id, "option": "Cotton"},
        blocking=True,
    )
    assert hass.states.get(option_ids["pre_wash"]).state == "off"
    assert hass.states.get(option_ids["hygiene"]).state == "off"
    assert hass.states.get(option_ids["anti_crease"]).state == "unavailable"
    assert hass.states.get(option_ids["good_night"]).state == "off"
    assert hass.states.get(option_ids["aquaplus"]).state == "off"
    assert hass.states.get(rinses_id).state == "Program default"

    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": program_id, "option": "Synthetics"},
        blocking=True,
    )
    assert hass.states.get(option_ids["hygiene"]).state == "unavailable"
    assert hass.states.get(option_ids["anti_crease"]).state == "off"

    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": program_id, "option": "Eco 40-60"},
        blocking=True,
    )
    assert all(
        hass.states.get(entity_id).state == "unavailable"
        for entity_id in option_ids.values()
    )
    assert hass.states.get(rinses_id).state == "Program default"


async def test_stop_uses_running_program(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
):
    running = (
        load_fixture("washing_machine/running_wash.json")
        .replace('"PrCode": "71"', '"PrCode": "7"')
        .replace('"SLevel": "2"', '"SLevel": "1"')
    )
    await init_integration(hass, aioclient_mock, running, enable_wash_control=True)
    entry_id = hass.config_entries.async_entries(DOMAIN)[0].entry_id
    start_id = _entity_id(hass, "button", UNIQUE_ID_WASH_START.format(entry_id))
    stop_id = _entity_id(hass, "button", UNIQUE_ID_WASH_STOP.format(entry_id))

    assert hass.states.get(start_id).state == "unavailable"
    assert hass.states.get(stop_id).state != "unavailable"

    with patch(
        "custom_components.candy.client.CandyClient.stop_washing_machine"
    ) as stop:
        await hass.services.async_call(
            "button", "press", {"entity_id": stop_id}, blocking=True
        )

    stop.assert_awaited_once_with(program=7)


async def test_pause_is_available_only_while_running(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
):
    running = (
        load_fixture("washing_machine/running_wash.json")
        .replace('"PrCode": "71"', '"PrCode": "7"')
        .replace('"SLevel": "2"', '"SLevel": "1"')
    )
    await init_integration(hass, aioclient_mock, running, enable_wash_control=True)
    entry_id = hass.config_entries.async_entries(DOMAIN)[0].entry_id
    pause_id = _entity_id(hass, "button", UNIQUE_ID_WASH_PAUSE.format(entry_id))
    resume_id = _entity_id(hass, "button", UNIQUE_ID_WASH_RESUME.format(entry_id))

    assert hass.states.get(pause_id).state != "unavailable"
    assert hass.states.get(resume_id).state == "unavailable"

    with patch(
        "custom_components.candy.client.CandyClient.pause_washing_machine"
    ) as pause:
        await hass.services.async_call(
            "button", "press", {"entity_id": pause_id}, blocking=True
        )

    pause.assert_awaited_once_with()


async def test_resume_is_available_only_while_paused(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
):
    paused = (
        load_fixture("washing_machine/running_wash.json")
        .replace('"MachMd": "2"', '"MachMd": "3"')
        .replace('"PrCode": "71"', '"PrCode": "7"')
        .replace('"SLevel": "2"', '"SLevel": "1"')
    )
    await init_integration(hass, aioclient_mock, paused, enable_wash_control=True)
    entry_id = hass.config_entries.async_entries(DOMAIN)[0].entry_id
    pause_id = _entity_id(hass, "button", UNIQUE_ID_WASH_PAUSE.format(entry_id))
    resume_id = _entity_id(hass, "button", UNIQUE_ID_WASH_RESUME.format(entry_id))

    assert hass.states.get(pause_id).state == "unavailable"
    assert hass.states.get(resume_id).state != "unavailable"

    with patch(
        "custom_components.candy.client.CandyClient.resume_washing_machine"
    ) as resume:
        await hass.services.async_call(
            "button", "press", {"entity_id": resume_id}, blocking=True
        )

    resume.assert_awaited_once_with()


async def test_refresh_touch_is_available_after_completed_wash(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
):
    completed = (
        load_fixture("washing_machine/idle.json")
        .replace('"MachMd": "1"', '"MachMd": "7"')
        .replace('"Pr": "1"', '"Pr": "14"')
        .replace('"PrCode": "136"', '"PrCode": "0"')
        .replace('"SLevel": "0"', '"SLevel": "3"')
        .replace('"Temp": "40"', '"Temp": "60"')
        .replace('"SpinSp": "8"', '"SpinSp": "10"')
    )
    await init_integration(hass, aioclient_mock, completed, enable_wash_control=True)
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    refresh_id = _entity_id(
        hass, "button", UNIQUE_ID_WASH_REFRESH_TOUCH.format(entry.entry_id)
    )
    stop_id = _entity_id(hass, "button", UNIQUE_ID_WASH_STOP.format(entry.entry_id))

    assert entry.options[CONF_ENABLE_WASH_CONTROL] is True
    assert hass.states.get(refresh_id).state != "unavailable"
    assert hass.states.get(stop_id).state == "unavailable"

    with patch(
        "custom_components.candy.client.CandyClient.start_refresh_touch"
    ) as refresh:
        await hass.services.async_call(
            "button", "press", {"entity_id": refresh_id}, blocking=True
        )

    refresh.assert_awaited_once_with()


async def test_refresh_touch_can_be_stopped(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
):
    running_refresh = (
        load_fixture("washing_machine/running_wash.json")
        .replace('"Pr": "7"', '"Pr": "16"')
        .replace('"PrCode": "71"', '"PrCode": "41"')
        .replace('"SLevel": "2"', '"SLevel": "0"')
        .replace('"Temp": "30"', '"Temp": "0"')
        .replace('"SpinSp": "10"', '"SpinSp": "0"')
    )
    await init_integration(
        hass, aioclient_mock, running_refresh, enable_wash_control=True
    )
    entry_id = hass.config_entries.async_entries(DOMAIN)[0].entry_id
    refresh_id = _entity_id(
        hass, "button", UNIQUE_ID_WASH_REFRESH_TOUCH.format(entry_id)
    )
    stop_id = _entity_id(hass, "button", UNIQUE_ID_WASH_STOP.format(entry_id))

    assert hass.states.get(refresh_id).state == "unavailable"
    assert hass.states.get(stop_id).state != "unavailable"

    with patch(
        "custom_components.candy.client.CandyClient.stop_washing_machine"
    ) as stop:
        await hass.services.async_call(
            "button", "press", {"entity_id": stop_id}, blocking=True
        )

    stop.assert_awaited_once_with(program=16)


async def test_controls_not_created_without_explicit_opt_in(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
):
    await init_integration(
        hass, aioclient_mock, load_fixture("washing_machine/idle.json")
    )
    entry_id = hass.config_entries.async_entries(DOMAIN)[0].entry_id

    registry = entity_registry.async_get(hass)
    assert (
        registry.async_get_entity_id(
            "button", DOMAIN, UNIQUE_ID_WASH_START.format(entry_id)
        )
        is None
    )
