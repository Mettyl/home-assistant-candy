"""Button entities for Candy washing-machine controls."""

from datetime import datetime, time, timedelta
import math
from typing import cast

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from homeassistant.util import dt as dt_util

from .client import CandyClient
from .client.model import MachineState, WashingMachineStatus
from .const import (
    DATA_KEY_CLIENT,
    DATA_KEY_COORDINATOR,
    DATA_KEY_WASH_CONTROL,
    DEVICE_NAME_WASHING_MACHINE,
    DOMAIN,
    SUGGESTED_AREA_BATHROOM,
    UNIQUE_ID_WASH_PAUSE,
    UNIQUE_ID_WASH_REFRESH_TOUCH,
    UNIQUE_ID_WASH_RESUME,
    UNIQUE_ID_WASH_SCHEDULE,
    UNIQUE_ID_WASH_START,
    UNIQUE_ID_WASH_STOP,
)
from .control import WashControlState


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
    async_add_entities(
        [
            CandyWashStartButton(
                coordinator,
                config_entry.entry_id,
                entry_data[DATA_KEY_CLIENT],
                entry_data[DATA_KEY_WASH_CONTROL],
            ),
            CandyWashScheduleButton(
                coordinator,
                config_entry.entry_id,
                entry_data[DATA_KEY_CLIENT],
                entry_data[DATA_KEY_WASH_CONTROL],
            ),
            CandyWashPauseButton(
                coordinator, config_entry.entry_id, entry_data[DATA_KEY_CLIENT]
            ),
            CandyWashResumeButton(
                coordinator, config_entry.entry_id, entry_data[DATA_KEY_CLIENT]
            ),
            CandyWashRefreshTouchButton(
                coordinator, config_entry.entry_id, entry_data[DATA_KEY_CLIENT]
            ),
            CandyWashStopButton(
                coordinator, config_entry.entry_id, entry_data[DATA_KEY_CLIENT]
            ),
        ]
    )


class CandyWashControlButton(CoordinatorEntity, ButtonEntity):
    """Base class for washing-machine control buttons."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        config_id: str,
        client: CandyClient,
    ):
        super().__init__(coordinator)
        self.config_id = config_id
        self.client = client

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.config_id)},
            name=DEVICE_NAME_WASHING_MACHINE,
            manufacturer="Candy",
            suggested_area=SUGGESTED_AREA_BATHROOM,
        )


class CandyWashStartButton(CandyWashControlButton):
    _attr_translation_key = "wash_start"
    _attr_icon = "mdi:play"

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        config_id: str,
        client: CandyClient,
        control: WashControlState,
    ):
        super().__init__(coordinator, config_id, client)
        self.control = control

    @property
    def unique_id(self) -> str:
        return UNIQUE_ID_WASH_START.format(self.config_id)

    @property
    def available(self) -> bool:
        status = cast(WashingMachineStatus, self.coordinator.data)
        return (
            super().available
            and status.remote_control
            and status.machine_state is MachineState.IDLE
        )

    async def async_press(self) -> None:
        preset = self.control.preset
        await self.client.start_washing_machine(
            program=preset.program,
            program_code=preset.program_code,
            selection_level=self.control.selected_soil_level,
            temperature=self.control.temperature,
            spin_speed=self.control.spin_speed,
            delay_minutes=0,
        )
        await self.coordinator.async_request_refresh()


class CandyWashScheduleButton(CandyWashControlButton):
    """Start a selected program at the next occurrence of a wall-clock time."""

    _attr_translation_key = "wash_schedule"
    _attr_icon = "mdi:calendar-clock"

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        config_id: str,
        client: CandyClient,
        control: WashControlState,
    ):
        super().__init__(coordinator, config_id, client)
        self.control = control

    @property
    def unique_id(self) -> str:
        return UNIQUE_ID_WASH_SCHEDULE.format(self.config_id)

    @property
    def available(self) -> bool:
        status = cast(WashingMachineStatus, self.coordinator.data)
        return (
            super().available
            and status.remote_control
            and status.machine_state is MachineState.IDLE
            and self.control.scheduled_start_time is not None
        )

    async def async_press(self) -> None:
        scheduled_time = self.control.scheduled_start_time
        if scheduled_time is None:
            raise ValueError("Set a scheduled start time first")
        preset = self.control.preset
        await self.client.start_washing_machine(
            program=preset.program,
            program_code=preset.program_code,
            selection_level=self.control.selected_soil_level,
            temperature=self.control.temperature,
            spin_speed=self.control.spin_speed,
            delay_minutes=minutes_until_start(dt_util.now(), scheduled_time),
        )
        await self.coordinator.async_request_refresh()


def minutes_until_start(now: datetime, scheduled_time: time) -> int:
    """Return whole protocol minutes until the next scheduled wall-clock time."""
    target = datetime.combine(now.date(), scheduled_time, tzinfo=now.tzinfo)
    if target <= now:
        target += timedelta(days=1)
    return math.ceil((target - now).total_seconds() / 60)


class CandyWashStopButton(CandyWashControlButton):
    _attr_translation_key = "wash_stop"
    _attr_icon = "mdi:stop"

    @property
    def unique_id(self) -> str:
        return UNIQUE_ID_WASH_STOP.format(self.config_id)

    @property
    def available(self) -> bool:
        status = cast(WashingMachineStatus, self.coordinator.data)
        return (
            super().available
            and status.remote_control
            and status.machine_state in (MachineState.RUNNING, MachineState.PAUSED)
        )

    async def async_press(self) -> None:
        status = cast(WashingMachineStatus, self.coordinator.data)
        await self.client.stop_washing_machine(program=status.program)
        await self.coordinator.async_request_refresh()


class CandyWashPauseButton(CandyWashControlButton):
    """Pause a running wash without cancelling it."""

    _attr_translation_key = "wash_pause"
    _attr_icon = "mdi:pause"

    @property
    def unique_id(self) -> str:
        return UNIQUE_ID_WASH_PAUSE.format(self.config_id)

    @property
    def available(self) -> bool:
        status = cast(WashingMachineStatus, self.coordinator.data)
        return (
            super().available
            and status.remote_control
            and status.machine_state is MachineState.RUNNING
        )

    async def async_press(self) -> None:
        await self.client.pause_washing_machine()
        await self.coordinator.async_request_refresh()


class CandyWashResumeButton(CandyWashControlButton):
    """Resume a remotely paused wash."""

    _attr_translation_key = "wash_resume"
    _attr_icon = "mdi:play-pause"

    @property
    def unique_id(self) -> str:
        return UNIQUE_ID_WASH_RESUME.format(self.config_id)

    @property
    def available(self) -> bool:
        status = cast(WashingMachineStatus, self.coordinator.data)
        return (
            super().available
            and status.remote_control
            and status.machine_state is MachineState.PAUSED
        )

    async def async_press(self) -> None:
        await self.client.resume_washing_machine()
        await self.coordinator.async_request_refresh()


class CandyWashRefreshTouchButton(CandyWashControlButton):
    """Start the post-cycle gentle drum movement program."""

    _attr_translation_key = "wash_refresh_touch"
    _attr_icon = "mdi:refresh"

    @property
    def unique_id(self) -> str:
        return UNIQUE_ID_WASH_REFRESH_TOUCH.format(self.config_id)

    @property
    def available(self) -> bool:
        status = cast(WashingMachineStatus, self.coordinator.data)
        return (
            super().available
            and status.remote_control
            and status.machine_state in (MachineState.FINISHED1, MachineState.FINISHED2)
        )

    async def async_press(self) -> None:
        await self.client.start_refresh_touch()
        await self.coordinator.async_request_refresh()
