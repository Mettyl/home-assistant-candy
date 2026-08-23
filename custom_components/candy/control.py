"""Model-specific washing-machine control presets."""

from dataclasses import dataclass
from datetime import time

from .client.model import MachineState, WashingMachineStatus

DEFAULT_OPTION = "Program default"
COLD_OPTION = "Cold"
NO_SPIN_OPTION = "No spin"
SOIL_LEVEL_OPTIONS = {1: "Light", 2: "Normal", 3: "Heavy"}


@dataclass(frozen=True)
class WashProgramPreset:
    """A verified local-control recipe for RO41274DWMSE/1-S."""

    name: str
    program: int
    program_code: int
    selection_level: int
    default_temperature: int
    default_spin_speed: int
    temperatures: tuple[int, ...]
    spin_speeds: tuple[int, ...]
    soil_levels: tuple[int, ...] = ()


# Only recipes observed on the user's RO41274DWMSE/1-S are included. Program
# codes differ between Candy families, so unverified selector positions must not
# be guessed here.
WASH_PROGRAMS: tuple[WashProgramPreset, ...] = (
    WashProgramPreset("Special 39'", 1, 136, 1, 30, 8, (0, 20, 30, 40), (0, 4, 6, 8)),
    WashProgramPreset("Rapid 14'", 7, 7, 1, 30, 8, (0, 20, 30), (0, 4, 6, 8)),
    WashProgramPreset("Rapid 30'", 7, 7, 2, 30, 8, (0, 20, 30), (0, 4, 6, 8)),
    WashProgramPreset("Rapid 44'", 7, 7, 3, 30, 8, (0, 20, 30, 40), (0, 4, 6, 8)),
    WashProgramPreset("20 °C", 12, 11, 2, 20, 10, (20,), (0, 4, 6, 8, 10)),
    WashProgramPreset("Eco 40-60", 13, 2, 3, 0, 12, (40, 60), (0, 4, 6, 8, 10, 12)),
    WashProgramPreset(
        "Cotton",
        14,
        65,
        3,
        60,
        12,
        (0, 20, 30, 40, 60, 90),
        (0, 4, 6, 8, 10, 12),
        (1, 2, 3),
    ),
)

PROGRAMS_BY_NAME = {program.name: program for program in WASH_PROGRAMS}


def temperature_option(value: int) -> str:
    """Format a native temperature as a select option."""
    return COLD_OPTION if value == 0 else f"{value} °C"


def spin_speed_option(value: int) -> str:
    """Format a native spin-speed value as a select option."""
    return NO_SPIN_OPTION if value == 0 else f"{value * 100} rpm"


class WashControlState:
    """Selections shared by the washing-machine control entities."""

    def __init__(self, preset: WashProgramPreset):
        self.preset = preset
        self.temperature: int | None = None
        self.spin_speed: int | None = None
        self.soil_level: int | None = None
        self.scheduled_start_time: time | None = None
        self.dirty = False

    @classmethod
    def from_status(cls, status: WashingMachineStatus) -> "WashControlState":
        """Select a matching verified preset, falling back to the first one."""
        preset = _preset_from_status(status) or WASH_PROGRAMS[0]
        state = cls(preset)
        state._apply_status_values(status)
        return state

    def sync_from_status(self, status: WashingMachineStatus) -> bool:
        """Synchronize selections after a command or an external state change.

        Pending user choices are preserved while the machine is idle. Once a
        cycle starts, the device response becomes authoritative.
        """
        if self.dirty and status.machine_state is MachineState.IDLE:
            return False
        preset = _preset_from_status(status)
        if preset is None:
            return False
        self.preset = preset
        self._apply_status_values(status)
        self.dirty = False
        return True

    def _apply_status_values(self, status: WashingMachineStatus) -> None:
        """Apply actual target values reported by the appliance."""
        self.temperature = (
            status.temp if status.temp in self.preset.temperatures else None
        )
        native_spin_speed = status.spin_speed // 100
        self.spin_speed = (
            native_spin_speed if native_spin_speed in self.preset.spin_speeds else None
        )
        self.soil_level = (
            status.selection_level
            if status.selection_level in self.preset.soil_levels
            else None
        )

    def select_program(self, name: str) -> None:
        """Select a preset and reset optional overrides to program defaults."""
        self.preset = PROGRAMS_BY_NAME[name]
        self.temperature = None
        self.spin_speed = None
        self.soil_level = None
        self.dirty = True

    @property
    def temperature_options(self) -> list[str]:
        """Return valid temperature choices for the selected program."""
        return [
            DEFAULT_OPTION,
            *(temperature_option(v) for v in self.preset.temperatures),
        ]

    @property
    def spin_speed_options(self) -> list[str]:
        """Return valid spin choices for the selected program."""
        return [
            DEFAULT_OPTION,
            *(spin_speed_option(v) for v in self.preset.spin_speeds),
        ]

    @property
    def soil_level_options(self) -> list[str]:
        """Return verified soil-level choices for the selected program."""
        return [
            DEFAULT_OPTION,
            *(SOIL_LEVEL_OPTIONS[value] for value in self.preset.soil_levels),
        ]

    @property
    def selected_soil_level(self) -> int:
        """Return the override or the verified program default."""
        return self.soil_level or self.preset.selection_level

    def select_temperature(self, option: str) -> None:
        """Set the temperature override from a select option."""
        if option == DEFAULT_OPTION:
            self.temperature = None
            self.dirty = True
            return
        values = {
            temperature_option(value): value for value in self.preset.temperatures
        }
        self.temperature = values[option]
        self.dirty = True

    def select_spin_speed(self, option: str) -> None:
        """Set the spin override from a select option."""
        if option == DEFAULT_OPTION:
            self.spin_speed = None
            self.dirty = True
            return
        values = {spin_speed_option(value): value for value in self.preset.spin_speeds}
        self.spin_speed = values[option]
        self.dirty = True

    def select_soil_level(self, option: str) -> None:
        """Set a verified soil-level override from a select option."""
        if option == DEFAULT_OPTION:
            self.soil_level = None
            self.dirty = True
            return
        values = {
            label: value
            for value, label in SOIL_LEVEL_OPTIONS.items()
            if value in self.preset.soil_levels
        }
        self.soil_level = values[option]
        self.dirty = True

    def select_start_time(self, value: time) -> None:
        """Set the wall-clock time used by the separate schedule button."""
        self.scheduled_start_time = value.replace(second=0, microsecond=0)
        self.dirty = True


def _preset_from_status(status: WashingMachineStatus) -> WashProgramPreset | None:
    """Resolve a verified preset from the appliance's actual status."""
    matching_programs = [
        candidate
        for candidate in WASH_PROGRAMS
        if candidate.program == status.program
        and (
            candidate.program_code == status.program_code
            or (
                status.machine_state in (MachineState.FINISHED1, MachineState.FINISHED2)
                and status.program_code in (None, 0)
            )
        )
    ]
    return next(
        (
            candidate
            for candidate in matching_programs
            if candidate.selection_level == status.selection_level
        ),
        matching_programs[0] if matching_programs else None,
    )
