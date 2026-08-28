"""Tests for model-specific washing-machine control presets."""

from datetime import time

from custom_components.candy.client.model import WashingMachineStatus
from custom_components.candy.control import (
    DEFAULT_OPTION,
    WASH_OPTION_ANTI_CREASE,
    WASH_OPTION_AQUAPLUS,
    WASH_OPTION_GOOD_NIGHT,
    WASH_OPTION_HYGIENE,
    WASH_OPTION_PRE_WASH,
    WASH_OPTION_RINSE_MASK,
    WashControlState,
)


def _status(**overrides) -> WashingMachineStatus:
    data = {
        "WiFiStatus": "1",
        "MachMd": "1",
        "Pr": "7",
        "PrPh": "0",
        "PrCode": "7",
        "SLevel": "1",
        "Temp": "30",
        "SpinSp": "8",
        "RemTime": "840",
    }
    data.update(overrides)
    return WashingMachineStatus.from_json(data)


def test_rapid_variants_are_distinguished_by_selection_level():
    names = [
        WashControlState.from_status(_status(SLevel=str(level))).preset.name
        for level in (1, 2, 3)
    ]

    assert names == ["Rapid 14'", "Rapid 30'", "Rapid 44'"]


def test_program_selection_resets_overrides():
    control = WashControlState.from_status(_status())
    control.select_temperature("20 °C")
    control.select_spin_speed("400 rpm")

    control.select_program("Cotton")

    assert control.temperature is None
    assert control.spin_speed is None
    assert control.temperature_options == [
        DEFAULT_OPTION,
        "Cold",
        "20 °C",
        "30 °C",
        "40 °C",
        "60 °C",
        "90 °C",
    ]


def test_cotton_offers_verified_soil_levels():
    control = WashControlState.from_status(_status())
    control.select_program("Cotton")

    assert control.soil_level_options == [
        DEFAULT_OPTION,
        "Light",
        "Normal",
        "Heavy",
    ]

    control.select_soil_level("Light")
    assert control.selected_soil_level == 1


def test_synthetics_uses_verified_program_and_options():
    control = WashControlState.from_status(
        _status(Pr="11", PrCode="3", SLevel="3", Temp="40", SpinSp="10")
    )

    assert control.preset.name == "Synthetics"
    assert control.temperature_options == [
        DEFAULT_OPTION,
        "Cold",
        "20 °C",
        "30 °C",
        "40 °C",
        "60 °C",
    ]
    assert control.spin_speed_options == [
        DEFAULT_OPTION,
        "No spin",
        "400 rpm",
        "600 rpm",
        "800 rpm",
        "1000 rpm",
    ]
    assert control.soil_level_options == [
        DEFAULT_OPTION,
        "Light",
        "Normal",
        "Heavy",
    ]
    assert control.preset.supported_option_mask == (
        WASH_OPTION_PRE_WASH
        | WASH_OPTION_ANTI_CREASE
        | WASH_OPTION_GOOD_NIGHT
        | WASH_OPTION_RINSE_MASK
        | WASH_OPTION_AQUAPLUS
    )


def test_washing_options_combine_and_reset_with_program():
    control = WashControlState.from_status(_status())
    control.select_program("Cotton")

    assert control.supports_option(WASH_OPTION_HYGIENE)
    assert not control.supports_option(WASH_OPTION_ANTI_CREASE)

    control.set_option(WASH_OPTION_PRE_WASH, True)
    control.set_option(WASH_OPTION_GOOD_NIGHT, True)
    control.select_extra_rinses("+2 rinses")

    assert control.option_mask == 41
    assert control.extra_rinse_option == "+2 rinses"

    control.select_extra_rinses("+1 rinse")
    assert control.option_mask == 25

    control.select_program("Eco 40-60")
    assert control.option_mask == 0
    assert control.extra_rinse_option == DEFAULT_OPTION
    assert not control.supports_option(WASH_OPTION_PRE_WASH)


def test_unverified_program_uses_fixed_default_soil_level():
    control = WashControlState.from_status(_status())

    assert control.soil_level_options == [DEFAULT_OPTION]
    assert control.selected_soil_level == 1


def test_scheduled_start_time_is_stored_without_seconds():
    control = WashControlState.from_status(_status())
    control.select_start_time(time(7, 15, 42))

    assert control.scheduled_start_time == time(7, 15)


def test_eco_offers_40_and_60_degrees():
    control = WashControlState.from_status(
        _status(Pr="13", PrCode="2", SLevel="3", Temp="0", SpinSp="12")
    )

    assert control.temperature_options == ["Program default", "40 °C", "60 °C"]


def test_pending_selection_survives_idle_poll_and_syncs_after_start():
    control = WashControlState.from_status(_status())
    control.select_program("Eco 40-60")
    control.select_temperature("40 °C")

    assert not control.sync_from_status(_status())
    assert control.preset.name == "Eco 40-60"
    assert control.temperature == 40

    running_eco = _status(
        MachMd="2", Pr="13", PrCode="2", SLevel="3", Temp="40", SpinSp="12"
    )
    assert control.sync_from_status(running_eco)
    assert control.preset.name == "Eco 40-60"
    assert control.temperature == 40
    assert control.spin_speed == 12
