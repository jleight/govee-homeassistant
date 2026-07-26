"""Event platform for Govee integration.

Provides event entities for:
- Button presses on Govee leak sensors (H5058), received via MQTT multiSync
  messages (0xEE 0x32).
- Momentary ``devices.capabilities.event`` pushes on appliances, e.g. the
  H8120 ice maker's clean-cycle-finished and run-interrupted notifications,
  received via the OpenAPI event channel.
"""

from __future__ import annotations

import logging

from homeassistant.components.event import EventDeviceClass, EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    SUFFIX_CLEANING_COMPLETED,
    SUFFIX_RUN_INTERRUPT,
)
from .coordinator import GoveeCoordinator
from .entity import GoveeEntity
from .models.device import (
    INSTANCE_CLEANING_COMPLETED_EVENT,
    INSTANCE_RUN_INTERRUPT_EVENT,
    GoveeDevice,
    GoveeLeakSensor,
    leak_sensor_device_info,
)

_LOGGER = logging.getLogger(__name__)

# Momentary event capabilities that map onto an HA event entity:
# instance -> (translation_key, unique_id suffix, event type).
DEVICE_EVENT_SPECS: dict[str, tuple[str, str, str]] = {
    INSTANCE_CLEANING_COMPLETED_EVENT: (
        "govee_cleaning_completed",
        SUFFIX_CLEANING_COMPLETED,
        "cleaning_completed",
    ),
    INSTANCE_RUN_INTERRUPT_EVENT: (
        "govee_run_interrupt",
        SUFFIX_RUN_INTERRUPT,
        "run_interrupted",
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Govee event entities from a config entry."""
    coordinator: GoveeCoordinator = entry.runtime_data

    entities: list[EventEntity] = []

    # Register hub devices first so leak sensors' `via_device` link resolves
    # (must run after orphan-cleanup in __init__.py).
    coordinator.register_leak_hubs()
    for sensor in coordinator.leak_sensors.values():
        entities.append(GoveeLeakButtonEvent(coordinator, sensor))

    # Momentary appliance notifications — the ice maker's clean-cycle-finished
    # and run-interrupted pushes (H8120). These carry no lingering condition,
    # so they are events rather than binary sensors.
    for device in coordinator.devices.values():
        if device.is_group:
            continue
        for instance, spec in DEVICE_EVENT_SPECS.items():
            if not device.has_event_capability(instance):
                continue
            translation_key, unique_suffix, event_type = spec
            entities.append(
                GoveeDeviceCapabilityEvent(
                    coordinator=coordinator,
                    device=device,
                    instance=instance,
                    translation_key=translation_key,
                    unique_suffix=unique_suffix,
                    event_type=event_type,
                )
            )
            _LOGGER.debug(
                "Created %s event entity for %s", instance, device.name
            )

    if entities:
        async_add_entities(entities)
        _LOGGER.debug("Set up %d Govee event entities", len(entities))


class GoveeLeakButtonEvent(EventEntity):
    """Event entity for button presses on a Govee leak sensor.

    Subscribes to the leak-specific dispatcher signal rather than the
    coordinator's generic update to avoid churning unrelated entities.
    """

    _attr_has_entity_name = True
    _attr_device_class = EventDeviceClass.BUTTON
    _attr_event_types = ["press"]
    _attr_translation_key = "leak_button"

    def __init__(
        self,
        coordinator: GoveeCoordinator,
        sensor: GoveeLeakSensor,
    ) -> None:
        """Initialize the button event entity."""
        self._coordinator = coordinator
        self._sensor = sensor
        self._attr_unique_id = f"{sensor.device_id}_button"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for device registry."""
        return leak_sensor_device_info(self._sensor, DOMAIN)

    async def async_added_to_hass(self) -> None:
        """Subscribe to leak-specific dispatcher signal."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, f"{DOMAIN}_leak_update", self._handle_leak_update
            )
        )

    @callback
    def _handle_leak_update(self) -> None:
        """Handle leak-specific update signal."""
        if self._coordinator.consume_button_press(self._sensor.device_id):
            self._trigger_event("press")
            self.async_write_ha_state()


class GoveeDeviceCapabilityEvent(GoveeEntity, EventEntity):
    """Event entity for a momentary ``devices.capabilities.event`` push.

    Subscribes to the device-event dispatcher signal rather than the
    coordinator's generic update, so an ice maker finishing a clean cycle does
    not churn every light entity.
    """

    def __init__(
        self,
        coordinator: GoveeCoordinator,
        device: GoveeDevice,
        instance: str,
        translation_key: str,
        unique_suffix: str,
        event_type: str,
    ) -> None:
        """Initialize the capability event entity.

        Args:
            coordinator: Govee data coordinator.
            device: Device this event belongs to.
            instance: The event capability instance to consume.
            translation_key: Entity translation key.
            unique_suffix: Unique-id suffix.
            event_type: The single event type this entity fires.
        """
        super().__init__(coordinator, device)

        self._instance = instance
        self._attr_translation_key = translation_key
        self._attr_unique_id = f"{device.device_id}{unique_suffix}"
        self._attr_event_types = [event_type]
        self._event_type = event_type

    async def async_added_to_hass(self) -> None:
        """Subscribe to the device-event dispatcher signal."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, f"{DOMAIN}_device_event", self._handle_device_event
            )
        )

    @callback
    def _handle_device_event(self) -> None:
        """Fire the event if one is queued for this device and instance."""
        if self.coordinator.consume_device_event(self._device_id, self._instance):
            self._trigger_event(self._event_type)
            self.async_write_ha_state()
