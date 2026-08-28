"""Time entity for scheduling a Candy washing-machine program."""

from datetime import time
from typing import cast

from homeassistant.components.time import TimeEntity
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
    UNIQUE_ID_WASH_DELAY_CONTROL,
)
from .control import WashControlState


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities
) -> None:
    """Set up the washing-machine delayed-start control."""
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    coordinator = entry_data[DATA_KEY_COORDINATOR]
    if (
        not isinstance(coordinator.data, WashingMachineStatus)
        or DATA_KEY_WASH_CONTROL not in entry_data
    ):
        return
    async_add_entities(
        [
            CandyWashDelayTime(
                coordinator,
                config_entry.entry_id,
                entry_data[DATA_KEY_WASH_CONTROL],
            )
        ]
    )


class CandyWashDelayTime(CoordinatorEntity, TimeEntity):
    """Wall-clock time used by the separate schedule button."""

    _attr_has_entity_name = True
    _attr_translation_key = "wash_delay_control"
    _attr_icon = "mdi:timer-outline"

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        config_id: str,
        control: WashControlState,
    ) -> None:
        super().__init__(coordinator)
        self.config_id = config_id
        self.control = control

    @property
    def unique_id(self) -> str:
        return UNIQUE_ID_WASH_DELAY_CONTROL.format(self.config_id)

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

    @property
    def native_value(self) -> time | None:
        return self.control.scheduled_start_time

    async def async_set_value(self, value: time) -> None:
        self.control.select_start_time(value)
        self.coordinator.async_set_updated_data(self.coordinator.data)
