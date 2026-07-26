"""Tests for the H8120 ice maker (devices.types.ice_maker).

Before this SKU was wired, the ice maker fell through the appliance exclusions
in ``is_light_device`` and matched the ``supports_rgb`` fallback — because of
its *nightlight's* colorRgb — so it became a light entity whose on/off was the
appliance mains. "Turn off all the lights" automations cut power to it.

Capability payload below is the real one from a user's diagnostics dump.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.govee.models import (
    GoveeCapability,
    GoveeDevice,
    GoveeDeviceState,
)
from custom_components.govee.models.device import (
    CAPABILITY_COLOR_SETTING,
    CAPABILITY_EVENT,
    CAPABILITY_MODE,
    CAPABILITY_ON_OFF,
    CAPABILITY_RANGE,
    CAPABILITY_TOGGLE,
    CAPABILITY_WORK_MODE,
    DEVICE_TYPE_ICE_MAKER,
    INSTANCE_BRIGHTNESS,
    INSTANCE_CLEANING_COMPLETED_EVENT,
    INSTANCE_COLOR_RGB,
    INSTANCE_ICE_FULL_EVENT,
    INSTANCE_ICE_MAKING_TOGGLE,
    INSTANCE_LACK_WATER_EVENT,
    INSTANCE_NIGHT_LIGHT,
    INSTANCE_NIGHTLIGHT_SCENE,
    INSTANCE_POWER,
    INSTANCE_PRECOOL_TOGGLE,
    INSTANCE_RUN_INTERRUPT_EVENT,
    INSTANCE_WORK_MODE,
)

ICE_MAKER_ID = "AA:BB:CC:DD:EE:FF:81:20"


def _h8120() -> GoveeDevice:
    """Build an H8120 from its real discovery payload."""
    return GoveeDevice(
        device_id=ICE_MAKER_ID,
        sku="H8120",
        name="Ice Maker",
        device_type=DEVICE_TYPE_ICE_MAKER,
        capabilities=(
            GoveeCapability(
                type=CAPABILITY_ON_OFF,
                instance=INSTANCE_POWER,
                parameters={
                    "dataType": "ENUM",
                    "options": [
                        {"name": "on", "value": 1},
                        {"name": "off", "value": 0},
                    ],
                },
            ),
            GoveeCapability(
                type=CAPABILITY_TOGGLE,
                instance=INSTANCE_ICE_MAKING_TOGGLE,
                parameters={
                    "dataType": "ENUM",
                    "options": [
                        {"name": "iceMaking", "value": 0},
                        {"name": "Clean", "value": 1},
                    ],
                },
            ),
            GoveeCapability(
                type=CAPABILITY_WORK_MODE,
                instance=INSTANCE_WORK_MODE,
                parameters={
                    "dataType": "STRUCT",
                    "fields": [
                        {
                            "fieldName": "workMode",
                            "dataType": "ENUM",
                            "options": [{"name": "IceMakingMode", "value": 1}],
                            "required": True,
                        },
                        {
                            "fieldName": "modeValue",
                            "dataType": "ENUM",
                            "options": [
                                {
                                    "name": "IceMakingMode",
                                    "options": [
                                        {"name": "Small Nugget", "value": 1},
                                        {"name": "Medium Nugget", "value": 2},
                                        {"name": "Large Nugget", "value": 3},
                                    ],
                                }
                            ],
                            "required": True,
                        },
                    ],
                },
            ),
            GoveeCapability(
                type=CAPABILITY_TOGGLE,
                instance=INSTANCE_PRECOOL_TOGGLE,
                parameters={
                    "dataType": "ENUM",
                    "options": [
                        {"name": "on", "value": 1},
                        {"name": "off", "value": 0},
                    ],
                },
            ),
            GoveeCapability(
                type=CAPABILITY_TOGGLE,
                instance=INSTANCE_NIGHT_LIGHT,
                parameters={
                    "dataType": "ENUM",
                    "options": [
                        {"name": "on", "value": 1},
                        {"name": "off", "value": 0},
                    ],
                },
            ),
            GoveeCapability(
                type=CAPABILITY_RANGE,
                instance=INSTANCE_BRIGHTNESS,
                parameters={
                    "dataType": "INTEGER",
                    "range": {"min": 1, "max": 100, "precision": 1},
                },
            ),
            GoveeCapability(
                type=CAPABILITY_COLOR_SETTING,
                instance=INSTANCE_COLOR_RGB,
                parameters={
                    "dataType": "INTEGER",
                    "range": {"min": 0, "max": 16777215, "precision": 1},
                },
            ),
            GoveeCapability(
                type=CAPABILITY_MODE,
                instance=INSTANCE_NIGHTLIGHT_SCENE,
                parameters={
                    "dataType": "ENUM",
                    "options": [
                        {"name": "Party", "value": 1},
                        {"name": "Gathering", "value": 2},
                    ],
                },
            ),
            GoveeCapability(
                type=CAPABILITY_EVENT,
                instance=INSTANCE_LACK_WATER_EVENT,
                parameters={},
            ),
            GoveeCapability(
                type=CAPABILITY_EVENT,
                instance=INSTANCE_ICE_FULL_EVENT,
                parameters={},
            ),
            GoveeCapability(
                type=CAPABILITY_EVENT,
                instance=INSTANCE_CLEANING_COMPLETED_EVENT,
                parameters={},
            ),
            GoveeCapability(
                type=CAPABILITY_EVENT,
                instance=INSTANCE_RUN_INTERRUPT_EVENT,
                parameters={},
            ),
        ),
        is_group=False,
    )


@pytest.fixture
def device() -> GoveeDevice:
    """H8120 ice maker device."""
    return _h8120()


def _coordinator(device: GoveeDevice, state: GoveeDeviceState | None = None):
    """Build a mock coordinator holding one device."""
    coordinator = MagicMock()
    coordinator.devices = {device.device_id: device}
    coordinator.get_state.return_value = state
    coordinator.async_control_device = AsyncMock(return_value=True)
    return coordinator


async def _setup(module, device: GoveeDevice, **coord_attrs) -> list:
    """Run a platform's async_setup_entry and return the created entities."""
    coordinator = _coordinator(device)
    for key, value in coord_attrs.items():
        setattr(coordinator, key, value)
    entry = MagicMock()
    entry.runtime_data = coordinator
    entry.options = {}
    added: list = []
    await module.async_setup_entry(MagicMock(), entry, lambda ents: added.extend(ents))
    return added


# --------------------------------------------------------------------------- #
# Device classification
# --------------------------------------------------------------------------- #


class TestIceMakerClassification:
    def test_is_ice_maker(self, device):
        assert device.is_ice_maker

    def test_not_a_light_despite_nightlight_rgb(self, device):
        """The regression this SKU was reported for.

        The device exposes colorRgb (its nightlight), which used to satisfy the
        ``supports_rgb`` fallback and make the whole appliance a light.
        """
        assert device.supports_rgb
        assert not device.is_light_device

    def test_nightlight_gets_its_own_light_entity(self, device):
        """With is_light_device False, the nightlight is no longer conflated."""
        assert device.has_nightlight_light

    def test_not_mistaken_for_other_appliances(self, device):
        assert not device.is_fan
        assert not device.is_heater
        assert not device.is_purifier
        assert not device.is_humidifier
        assert not device.is_plug

    def test_capability_predicates(self, device):
        assert device.supports_ice_making_toggle
        assert device.supports_precool
        assert device.supports_ice_full_event
        assert device.supports_lack_water_event
        assert device.has_event_capability(INSTANCE_CLEANING_COMPLETED_EVENT)
        assert device.has_event_capability(INSTANCE_RUN_INTERRUPT_EVENT)
        assert not device.has_event_capability("nonexistentEvent")


class TestOptionParsing:
    def test_ice_size_options_flatten_nested_mode_values(self, device):
        assert device.get_ice_size_options() == [
            {"name": "Small Nugget", "work_mode": 1, "mode_value": 1},
            {"name": "Medium Nugget", "work_mode": 1, "mode_value": 2},
            {"name": "Large Nugget", "work_mode": 1, "mode_value": 3},
        ]

    def test_ice_making_mode_options_returned_verbatim(self, device):
        assert device.get_ice_making_mode_options() == [
            {"name": "iceMaking", "value": 0},
            {"name": "Clean", "value": 1},
        ]

    def test_option_getters_empty_without_capabilities(self):
        bare = GoveeDevice(
            device_id=ICE_MAKER_ID,
            sku="H8120",
            name="Ice Maker",
            device_type=DEVICE_TYPE_ICE_MAKER,
            capabilities=(),
            is_group=False,
        )
        assert bare.get_ice_size_options() == []
        assert bare.get_ice_making_mode_options() == []


# --------------------------------------------------------------------------- #
# Platform wiring
# --------------------------------------------------------------------------- #


class TestPlatformSetup:
    async def test_no_light_entity_for_the_appliance_itself(self, device):
        from custom_components.govee import light as light_mod

        added = await _setup(light_mod, device)
        names = [type(e).__name__ for e in added]
        assert "GoveeLightEntity" not in names
        # The nightlight still gets its own light entity — that one IS a light.
        assert "GoveeNightLightEntity" in names

    async def test_switch_entities(self, device):
        from custom_components.govee import switch as switch_mod

        added = await _setup(switch_mod, device)
        names = [type(e).__name__ for e in added]
        assert "GoveeAppliancePowerSwitchEntity" in names
        assert "GoveePrecoolSwitchEntity" in names
        # The nightlight is a light entity now, so no duplicate on/off switch.
        assert "GoveeNightLightSwitchEntity" not in names

    async def test_select_entities(self, device):
        from custom_components.govee import select as select_mod

        added = await _setup(select_mod, device)
        by_name = {type(e).__name__: e for e in added}
        assert "GoveeIceMakingModeSelectEntity" in by_name
        assert "GoveeIceSizeSelectEntity" in by_name
        assert by_name["GoveeIceSizeSelectEntity"].options == [
            "Small Nugget",
            "Medium Nugget",
            "Large Nugget",
        ]
        assert by_name["GoveeIceMakingModeSelectEntity"].options == [
            "iceMaking",
            "Clean",
        ]

    async def test_binary_sensor_entities(self, device):
        from custom_components.govee import binary_sensor as bs_mod

        added = await _setup(
            bs_mod, device, leak_sensors={}, register_leak_hubs=MagicMock()
        )
        names = [type(e).__name__ for e in added]
        assert "GoveeIceFullBinarySensor" in names
        assert "GoveeLackWaterBinarySensor" in names

    async def test_event_entities(self, device):
        from custom_components.govee import event as event_mod

        added = await _setup(
            event_mod, device, leak_sensors={}, register_leak_hubs=MagicMock()
        )
        instances = sorted(
            e._instance
            for e in added
            if type(e).__name__ == "GoveeDeviceCapabilityEvent"
        )
        assert instances == [
            INSTANCE_CLEANING_COMPLETED_EVENT,
            INSTANCE_RUN_INTERRUPT_EVENT,
        ]


# --------------------------------------------------------------------------- #
# Control commands
# --------------------------------------------------------------------------- #


class TestControls:
    async def test_ice_size_sends_work_mode_struct(self, device):
        from custom_components.govee import select as select_mod

        added = await _setup(select_mod, device)
        entity = next(
            e for e in added if type(e).__name__ == "GoveeIceSizeSelectEntity"
        )
        entity.async_write_ha_state = MagicMock()

        await entity.async_select_option("Large Nugget")

        command = entity.coordinator.async_control_device.call_args[0][1]
        assert command.get_value() == {"workMode": 1, "modeValue": 3}
        assert entity.current_option == "Large Nugget"

    async def test_clean_cycle_sends_value_one(self, device):
        from custom_components.govee import select as select_mod

        added = await _setup(select_mod, device)
        entity = next(
            e for e in added if type(e).__name__ == "GoveeIceMakingModeSelectEntity"
        )
        entity.async_write_ha_state = MagicMock()

        await entity.async_select_option("Clean")

        command = entity.coordinator.async_control_device.call_args[0][1]
        assert command.instance == INSTANCE_ICE_MAKING_TOGGLE
        assert command.get_value() == 1

    async def test_ice_making_cycle_sends_value_zero(self, device):
        """iceMaking is value 0 — the ENUM is a cycle selector, not on/off."""
        from custom_components.govee import select as select_mod

        added = await _setup(select_mod, device)
        entity = next(
            e for e in added if type(e).__name__ == "GoveeIceMakingModeSelectEntity"
        )
        entity.async_write_ha_state = MagicMock()

        await entity.async_select_option("iceMaking")

        assert entity.coordinator.async_control_device.call_args[0][1].get_value() == 0

    async def test_unknown_option_sends_nothing(self, device):
        from custom_components.govee import select as select_mod

        added = await _setup(select_mod, device)
        entity = next(
            e for e in added if type(e).__name__ == "GoveeIceSizeSelectEntity"
        )

        await entity.async_select_option("Crushed")

        entity.coordinator.async_control_device.assert_not_called()

    async def test_precool_toggle_round_trip(self, device):
        from custom_components.govee import switch as switch_mod

        added = await _setup(switch_mod, device)
        entity = next(
            e for e in added if type(e).__name__ == "GoveePrecoolSwitchEntity"
        )
        entity.async_write_ha_state = MagicMock()

        await entity.async_turn_on()
        assert entity.is_on
        command = entity.coordinator.async_control_device.call_args[0][1]
        assert command.instance == INSTANCE_PRECOOL_TOGGLE
        assert command.get_value() == 1

        await entity.async_turn_off()
        assert not entity.is_on
        assert entity.coordinator.async_control_device.call_args[0][1].get_value() == 0

    async def test_precool_stays_off_when_command_fails(self, device):
        from custom_components.govee import switch as switch_mod

        added = await _setup(switch_mod, device)
        entity = next(
            e for e in added if type(e).__name__ == "GoveePrecoolSwitchEntity"
        )
        entity.coordinator.async_control_device = AsyncMock(return_value=False)
        entity.async_write_ha_state = MagicMock()

        await entity.async_turn_on()

        assert not entity.is_on


# --------------------------------------------------------------------------- #
# State + event application
# --------------------------------------------------------------------------- #


class TestStateParsing:
    def test_ice_events_parsed_from_capability_state(self):
        state = GoveeDeviceState(device_id=ICE_MAKER_ID, online=True)
        state.update_from_api(
            {"capabilities": [
                {
                    "type": CAPABILITY_EVENT,
                    "instance": INSTANCE_ICE_FULL_EVENT,
                    "state": {"value": 1},
                },
                {
                    "type": CAPABILITY_EVENT,
                    "instance": INSTANCE_LACK_WATER_EVENT,
                    "state": {"value": 0},
                },
            ]}
        )
        assert state.ice_full is True
        assert state.lack_water is False

    def test_generic_toggles_captured(self):
        state = GoveeDeviceState(device_id=ICE_MAKER_ID, online=True)
        state.update_from_api(
            {"capabilities": [
                {
                    "type": CAPABILITY_TOGGLE,
                    "instance": INSTANCE_PRECOOL_TOGGLE,
                    "state": {"value": 1},
                },
                # Govee returns "" for iceMakingToggle on poll — must not
                # clobber the last known value with False.
                {
                    "type": CAPABILITY_TOGGLE,
                    "instance": INSTANCE_ICE_MAKING_TOGGLE,
                    "state": {"value": ""},
                },
            ]}
        )
        assert state.toggles[INSTANCE_PRECOOL_TOGGLE] is True
        assert INSTANCE_ICE_MAKING_TOGGLE not in state.toggles


# --------------------------------------------------------------------------- #
# Coordinator event push
# --------------------------------------------------------------------------- #


class TestCoordinatorEvents:
    """The OpenAPI event channel is the only source for these — the developer
    /device/state poll omits the ice maker's event capabilities entirely."""

    def _coordinator(self, device: GoveeDevice):
        import custom_components.govee.coordinator as coord_mod

        coord = object.__new__(coord_mod.GoveeCoordinator)
        coord._devices = {device.device_id: device}
        coord._states = {
            device.device_id: GoveeDeviceState.create_empty(device.device_id)
        }
        coord._water_full_changed_at = {}
        coord._pending_device_events = {}
        coord.hass = MagicMock()
        coord.async_set_updated_data = MagicMock()
        return coord

    def test_ice_full_event_applied(self, device):
        coord = self._coordinator(device)
        coord._on_openapi_event(
            device.device_id, "H8120", INSTANCE_ICE_FULL_EVENT, [{"value": 1}]
        )
        assert coord._states[device.device_id].ice_full is True
        coord.async_set_updated_data.assert_called_once()

    def test_ice_full_cleared(self, device):
        coord = self._coordinator(device)
        coord._states[device.device_id].ice_full = True
        coord._on_openapi_event(
            device.device_id, "H8120", INSTANCE_ICE_FULL_EVENT, [{"value": 0}]
        )
        assert coord._states[device.device_id].ice_full is False

    def test_lack_water_event_applied(self, device):
        coord = self._coordinator(device)
        coord._on_openapi_event(
            device.device_id, "H8120", INSTANCE_LACK_WATER_EVENT, [{"value": 1}]
        )
        assert coord._states[device.device_id].lack_water is True

    def test_lack_water_ignored_for_non_ice_makers(self):
        """Humidifiers and aroma diffusers emit lackWaterEvent too, but have no
        entity consuming it — handling it there would add a silent sensor."""
        from custom_components.govee.models.device import DEVICE_TYPE_DEHUMIDIFIER

        humidifier = GoveeDevice(
            device_id="AA:BB:CC:DD:EE:FF:71:50",
            sku="H7150",
            name="Dehumidifier",
            device_type=DEVICE_TYPE_DEHUMIDIFIER,
            capabilities=(),
            is_group=False,
        )
        coord = self._coordinator(humidifier)
        coord._on_openapi_event(
            humidifier.device_id, "H7150", INSTANCE_LACK_WATER_EVENT, [{"value": 1}]
        )
        assert coord._states[humidifier.device_id].lack_water is None
        coord.async_set_updated_data.assert_not_called()

    def test_momentary_events_queue_instead_of_mutating_state(self, device):
        coord = self._coordinator(device)
        coord._on_openapi_event(
            device.device_id, "H8120", INSTANCE_CLEANING_COMPLETED_EVENT, [{"value": 1}]
        )
        assert coord._pending_device_events[device.device_id] == [
            INSTANCE_CLEANING_COMPLETED_EVENT
        ]
        # Momentary events do not go through the state machine.
        coord.async_set_updated_data.assert_not_called()

    def test_consume_device_event_is_per_instance(self, device):
        coord = self._coordinator(device)
        coord._pending_device_events[device.device_id] = [
            INSTANCE_CLEANING_COMPLETED_EVENT,
            INSTANCE_RUN_INTERRUPT_EVENT,
        ]

        assert coord.consume_device_event(
            device.device_id, INSTANCE_CLEANING_COMPLETED_EVENT
        )
        # Consuming one must not swallow the other.
        assert coord._pending_device_events[device.device_id] == [
            INSTANCE_RUN_INTERRUPT_EVENT
        ]
        assert coord.consume_device_event(
            device.device_id, INSTANCE_RUN_INTERRUPT_EVENT
        )
        assert device.device_id not in coord._pending_device_events

    def test_consume_device_event_empty(self, device):
        coord = self._coordinator(device)
        assert not coord.consume_device_event(
            device.device_id, INSTANCE_RUN_INTERRUPT_EVENT
        )
