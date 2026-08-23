"""Select entities for Candy washing-machine controls."""

from abc import abstractmethod
from typing import cast

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .client.model import MachineState, WashingMachineStatus
from .const import (
    DATA_KEY_COORDINATOR,
    DATA_KEY_WASH_CONTROL,
    DEVICE_NAME_WASHING_MACHINE,
    DOMAIN,
    SUGGESTED_AREA_BATHROOM,
    UNIQUE_ID_WASH_PROGRAM_CONTROL,
    UNIQUE_ID_WASH_SOIL_LEVEL_CONTROL,
    UNIQUE_ID_WASH_SPIN_SPEED_CONTROL,
    UNIQUE_ID_WASH_TEMPERATURE_CONTROL,
)
from .control import (
    DEFAULT_OPTION,
    SOIL_LEVEL_OPTIONS,
    WASH_PROGRAMS,
    WashControlState,
    spin_speed_option,
    temperature_option,
)


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities
):
    """Set up controls for supported washing machines."""
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    coordinator = entry_data[DATA_KEY_COORDINATOR]
    if (
        not isinstance(coordinator.data, WashingMachineStatus)
        or DATA_KEY_WASH_CONTROL not in entry_data
    ):
        return
    control = entry_data[DATA_KEY_WASH_CONTROL]
    async_add_entities(
        [
            CandyWashProgramSelect(coordinator, config_entry.entry_id, control),
            CandyWashTemperatureSelect(coordinator, config_entry.entry_id, control),
            CandyWashSpinSpeedSelect(coordinator, config_entry.entry_id, control),
            CandyWashSoilLevelSelect(coordinator, config_entry.entry_id, control),
        ]
    )


class CandyWashControlSelect(CoordinatorEntity, SelectEntity):
    """Base class for washing-machine control selects."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        config_id: str,
        control: WashControlState,
    ):
        super().__init__(coordinator)
        self.config_id = config_id
        self.control = control

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.config_id)},
            name=DEVICE_NAME_WASHING_MACHINE,
            manufacturer="Candy",
            suggested_area=SUGGESTED_AREA_BATHROOM,
        )

    @property
    def available(self) -> bool:
        status = cast(WashingMachineStatus, self.coordinator.data)
        return (
            super().available
            and status.remote_control
            and status.machine_state is MachineState.IDLE
        )

    @abstractmethod
    async def async_select_option(self, option: str) -> None:
        """Select an option."""


class CandyWashProgramSelect(CandyWashControlSelect):
    _attr_translation_key = "wash_program_control"
    _attr_icon = "mdi:washing-machine-cog"

    @property
    def unique_id(self) -> str:
        return UNIQUE_ID_WASH_PROGRAM_CONTROL.format(self.config_id)

    @property
    def options(self) -> list[str]:
        return [program.name for program in WASH_PROGRAMS]

    @property
    def current_option(self) -> str:
        return self.control.preset.name

    async def async_select_option(self, option: str) -> None:
        self.control.select_program(option)
        self.coordinator.async_set_updated_data(self.coordinator.data)


class CandyWashTemperatureSelect(CandyWashControlSelect):
    _attr_translation_key = "wash_temperature_control"
    _attr_icon = "mdi:thermometer"

    @property
    def unique_id(self) -> str:
        return UNIQUE_ID_WASH_TEMPERATURE_CONTROL.format(self.config_id)

    @property
    def options(self) -> list[str]:
        return self.control.temperature_options

    @property
    def current_option(self) -> str:
        if self.control.temperature is None:
            return DEFAULT_OPTION
        return temperature_option(self.control.temperature)

    async def async_select_option(self, option: str) -> None:
        self.control.select_temperature(option)
        self.async_write_ha_state()


class CandyWashSpinSpeedSelect(CandyWashControlSelect):
    _attr_translation_key = "wash_spin_speed_control"
    _attr_icon = "mdi:rotate-right"

    @property
    def unique_id(self) -> str:
        return UNIQUE_ID_WASH_SPIN_SPEED_CONTROL.format(self.config_id)

    @property
    def options(self) -> list[str]:
        return self.control.spin_speed_options

    @property
    def current_option(self) -> str:
        if self.control.spin_speed is None:
            return DEFAULT_OPTION
        return spin_speed_option(self.control.spin_speed)

    async def async_select_option(self, option: str) -> None:
        self.control.select_spin_speed(option)
        self.async_write_ha_state()


class CandyWashSoilLevelSelect(CandyWashControlSelect):
    _attr_translation_key = "wash_soil_level_control"
    _attr_icon = "mdi:water-opacity"

    @property
    def unique_id(self) -> str:
        return UNIQUE_ID_WASH_SOIL_LEVEL_CONTROL.format(self.config_id)

    @property
    def options(self) -> list[str]:
        return self.control.soil_level_options

    @property
    def current_option(self) -> str:
        if self.control.soil_level is None:
            return DEFAULT_OPTION
        return SOIL_LEVEL_OPTIONS[self.control.soil_level]

    async def async_select_option(self, option: str) -> None:
        self.control.select_soil_level(option)
        self.async_write_ha_state()
