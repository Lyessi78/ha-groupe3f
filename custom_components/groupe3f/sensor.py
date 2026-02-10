"""Sensor platform for Groupe 3F."""
from __future__ import annotations
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass, SensorEntity, SensorStateClass
)
from homeassistant.const import UnitOfVolume
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_CONTRACT_ID, DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    contract_id = entry.data[CONF_CONTRACT_ID]

    entities = []
    # Map JSON boolean keys to Names
    types = {"compteurChaud": "Eau Chaude", "compteurFroid": "Eau Froide"}

    for key, name in types.items():
        # Check if any data exists for this meter type
        if any(item.get(key) is True for item in coordinator.data):
            entities.append(Groupe3FSensor(coordinator, contract_id, key, name))

    async_add_entities(entities)

class Groupe3FSensor(CoordinatorEntity, SensorEntity):
    """Groupe 3F Sensor."""
    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.WATER
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfVolume.CUBIC_METERS

    def __init__(self, coordinator, contract_id, filter_key, name):
        super().__init__(coordinator)
        self._filter = filter_key
        self._attr_name = name
        self._attr_unique_id = f"{contract_id}_{filter_key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, contract_id)},
            name=f"Compteur 3F ({contract_id})",
            manufacturer="Groupe 3F",
        )

    @property
    def native_value(self):
        """Return the latest index."""
        # Get data for this specific meter
        data = [i for i in self.coordinator.data if i.get(self._filter) is True]
        if not data: return None
        # Sort by date descending and take first
        latest = sorted(data, key=lambda x: x.get("ecrelDatrel", ""), reverse=True)[0]
        return latest.get("ecrelVal")

    @property
    def extra_state_attributes(self):
        """Attributes."""
        data = [i for i in self.coordinator.data if i.get(self._filter) is True]
        if not data: return {}
        latest = sorted(data, key=lambda x: x.get("ecrelDatrel", ""), reverse=True)[0]
        return {
            "last_reading": latest.get("ecrelDatrel"),
            "serial_number": latest.get("painsCodser", "").strip(),
            "monthly_cons_m3": latest.get("ecconVal")
        }