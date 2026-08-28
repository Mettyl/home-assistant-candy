"""Switch entities for Candy washing-machine options."""

from dataclasses import dataclass
from typing import cast

from homeassistant.components.switch import SwitchEntity
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
    UNIQUE_ID_WASH_ANTI_CREASE,
    UNIQUE_ID_WASH_AQUAPLUS,
    UNIQUE_ID_WASH_GOOD_NIGHT,
    UNIQUE_ID_WASH_HYGIENE,
    UNIQUE_ID_WASH_PRE_WASH,
)
from .control import (
    WASH_OPTION_ANTI_CREASE,
    WASH_OPTION_AQUAPLUS,
    WASH_OPTION_GOOD_NIGHT,
    WASH_OPTION_HYGIENE,
    WASH_OPTION_PRE_WASH,
    WashControlState,
)


@dataclass(frozen=True)
class WashOptionDescription:
    """Describe a model-specific independent washing option."""

    translation_key: str
    unique_id: str
    icon: str
    option: int


WASH_OPTION_DESCRIPTIONS = (
    WashOptionDescription(
        "wash_pre_wash", UNIQUE_ID_WASH_PRE_WASH, "mdi:waves", WASH_OPTION_PRE_WASH
    ),
    WashOptionDescription(
        "wash_hygiene", UNIQUE_ID_WASH_HYGIENE, "mdi:shield-check", WASH_OPTION_HYGIENE
    ),
    WashOptionDescription(
        "wash_anti_crease",
        UNIQUE_ID_WASH_ANTI_CREASE,
        "mdi:iron-outline",
        WASH_OPTION_ANTI_CREASE,
    ),
    WashOptionDescription(
        "wash_good_night",
        UNIQUE_ID_WASH_GOOD_NIGHT,
        "mdi:weather-night",
        WASH_OPTION_GOOD_NIGHT,
    ),
    WashOptionDescription(
        "wash_aquaplus",
        UNIQUE_ID_WASH_AQUAPLUS,
        "mdi:water-plus",
        WASH_OPTION_AQUAPLUS,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities
) -> None:
    """Set up verified washing-option switches."""
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    coordinator = entry_data[DATA_KEY_COORDINATOR]
    if (
        not isinstance(coordinator.data, WashingMachineStatus)
        or DATA_KEY_WASH_CONTROL not in entry_data
    ):
        return
    control = entry_data[DATA_KEY_WASH_CONTROL]
    async_add_entities(
        CandyWashOptionSwitch(coordinator, config_entry.entry_id, control, description)
        for description in WASH_OPTION_DESCRIPTIONS
    )


class CandyWashOptionSwitch(CoordinatorEntity, SwitchEntity):
    """Configure one independently combinable washing option."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        config_id: str,
        control: WashControlState,
        description: WashOptionDescription,
    ) -> None:
        super().__init__(coordinator)
        self.config_id = config_id
        self.control = control
        self.description = description
        self._attr_translation_key = description.translation_key
        self._attr_icon = description.icon

    @property
    def unique_id(self) -> str:
        return self.description.unique_id.format(self.config_id)

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
            and self.control.supports_option(self.description.option)
        )

    @property
    def is_on(self) -> bool:
        return bool(self.control.option_mask & self.description.option)

    async def async_turn_on(self, **kwargs) -> None:
        self.control.set_option(self.description.option, True)
        self.coordinator.async_set_updated_data(self.coordinator.data)

    async def async_turn_off(self, **kwargs) -> None:
        self.control.set_option(self.description.option, False)
        self.coordinator.async_set_updated_data(self.coordinator.data)
