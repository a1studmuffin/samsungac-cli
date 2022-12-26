import json
import logging
import subprocess
import voluptuous
import homeassistant.helpers.config_validation as cv
from homeassistant.components import climate
from homeassistant.components.climate import ClimateEntity, PLATFORM_SCHEMA
from homeassistant.components.climate.const import (
    SUPPORT_TARGET_TEMPERATURE,
    SUPPORT_FAN_MODE,
    ATTR_HVAC_MODE,
    ATTR_FAN_MODE,
    HVAC_MODE_AUTO,
    HVAC_MODE_COOL,
    HVAC_MODE_DRY,
    HVAC_MODE_FAN_ONLY,
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
    FAN_AUTO,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_HIGH,
    FAN_OFF,
    CURRENT_HVAC_OFF,
    CURRENT_HVAC_HEAT,
    CURRENT_HVAC_COOL,
    CURRENT_HVAC_DRY,
    CURRENT_HVAC_IDLE,
    CURRENT_HVAC_FAN,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    CONF_NAME,
    CONF_ACCESS_TOKEN,
    CONF_DEVICE_ID,
    TEMP_CELSIUS,
)
from homeassistant.helpers.typing import HomeAssistantType, ConfigType

_LOGGER = logging.getLogger(__name__)

CONF_SMARTTHINGS_PATH = "smartthings_path"

DEFAULT_NAME = "SamsungAC SmartThings CLI"
DEFAULT_SMARTTHINGS_PATH = "/usr/local/bin/smartthings"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        voluptuous.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        voluptuous.Required(CONF_ACCESS_TOKEN): cv.string,
        voluptuous.Required(CONF_DEVICE_ID): cv.string,
        voluptuous.Required(
            CONF_SMARTTHINGS_PATH, default=DEFAULT_SMARTTHINGS_PATH
        ): cv.string,
    }
)


async def async_setup_platform(
    hass: HomeAssistantType, config: ConfigType, async_add_entities, discovery_info=None
) -> None:
    async_add_entities(
        [
            SamsungACCLIClimate(
                config.get(CONF_NAME),
                config.get(CONF_ACCESS_TOKEN),
                config.get(CONF_DEVICE_ID),
                config.get(CONF_SMARTTHINGS_PATH),
            )
        ]
    )


class SamsungACCLIClimate(ClimateEntity):
    def __init__(
        self, name: str, access_token: str, device_id: str, smartthings_path: str
    ) -> None:
        self._name = name
        self._access_token = access_token
        self._device_id = device_id
        self._smartthings_path = smartthings_path
        self._current_mode = None
        self._switch_state = None
        self._min_temp = 0
        self._max_temp = 0
        self._current_temp = 0
        self._target_temp = 0
        self._mode = None
        self._action = None
        self._fan_mode = None
        self._available = False

    @property
    def name(self) -> str:
        return self._name

    @property
    def available(self) -> bool:
        return self._available

    @property
    def supported_features(self) -> int:
        return SUPPORT_TARGET_TEMPERATURE | SUPPORT_FAN_MODE

    @property
    def hvac_mode(self):
        return self._mode

    @property
    def hvac_action(self):
        return self._action

    @property
    def hvac_modes(self):
        return [
            HVAC_MODE_AUTO,
            HVAC_MODE_COOL,
            HVAC_MODE_DRY,
            HVAC_MODE_FAN_ONLY,
            HVAC_MODE_HEAT,
            HVAC_MODE_OFF,
        ]

    @property
    def min_temp(self):
        return self._min_temp

    @property
    def max_temp(self):
        return self._max_temp

    @property
    def temperature_unit(self):
        return TEMP_CELSIUS

    @property
    def current_temperature(self):
        return self._current_temp

    @property
    def target_temperature(self):
        return self._target_temp

    @property
    def fan_mode(self):
        return self._fan_mode

    @property
    def fan_modes(self):
        return [FAN_AUTO, FAN_LOW, FAN_MEDIUM, FAN_HIGH]

    def run_smartthings_command(self, command):
        try:
            smartthings_command = f"{self._smartthings_path} {command} {self._device_id} -j --token {self._access_token}"
            _LOGGER.debug(smartthings_command)
            result = subprocess.run(
                smartthings_command.split(), capture_output=True, text=True
            )
            _LOGGER.debug(result.stdout)
            return json.loads(result.stdout)
        except Exception as e:
            _LOGGER.debug(f"run_smartthings_command() failed: {str(e)}")
            return ""

    async def async_update(self):

        device_status_json = self.run_smartthings_command("devices:status")
        try:
            self._available = True

            self._min_temp = device_status_json["components"]["main"][
                "custom.thermostatSetpointControl"
            ]["minimumSetpoint"][
                "value"
            ]  # just assume celcius here
            self._max_temp = device_status_json["components"]["main"][
                "custom.thermostatSetpointControl"
            ]["maximumSetpoint"][
                "value"
            ]  # just assume celcius here

            self._current_mode = device_status_json["components"]["main"][
                "airConditionerMode"
            ]["airConditionerMode"]["value"]
            self._switch_state = device_status_json["components"]["main"]["switch"][
                "switch"
            ]["value"]
            if self._switch_state == "off":
                self._action = CURRENT_HVAC_OFF
                self._mode = HVAC_MODE_OFF
            elif self._current_mode == "auto":
                self._action = CURRENT_HVAC_IDLE
                self._mode = HVAC_MODE_AUTO
            elif self._current_mode == "cool":
                self._action = CURRENT_HVAC_COOL
                self._mode = HVAC_MODE_COOL
            elif self._current_mode == "dry":
                self._action = CURRENT_HVAC_DRY
                self._mode = HVAC_MODE_DRY
            elif self._current_mode == "wind":
                self._action = CURRENT_HVAC_FAN
                self._mode = HVAC_MODE_FAN_ONLY
            else:
                self._action = CURRENT_HVAC_OFF
                self._mode = HVAC_MODE_OFF
                _LOGGER.debug(f"Unknown HVAC current mode: {str(self._current_mode)}")

            self._current_fan_mode = device_status_json["components"]["main"][
                "airConditionerFanMode"
            ]["fanMode"]["value"]
            if self._current_fan_mode == "auto":
                self._fan_mode = FAN_AUTO
            elif self.current_mode == "low":
                self._fan_mode = FAN_LOW
            elif self.current_mode == "medium":
                self._fan_mode = FAN_MEDIUM
            elif self.current_mode == "high":
                self._fan_mode = FAN_HIGH
            else:
                self._fan_mode = FAN_OFF
                _LOGGER.debug(f"Unknown fan mode: {str(self._fan_mode)}")

            self._current_temp = device_status_json["components"]["main"][
                "temperatureMeasurement"
            ]["temperature"][
                "value"
            ]  # just assume celcius here
            self._target_temp = device_status_json["components"]["main"][
                "thermostatCoolingSetpoint"
            ]["coolingSetpoint"][
                "value"
            ]  # just assume celcius here
            self._power_consumption = device_status_json["components"]["main"][
                "powerConsumptionReport"
            ]["powerConsumption"]["power"]["value"]

            _LOGGER.debug(
                f"State update complete, Target temp: {self._target_temp}; Current temp: {self._current_temp}; Min temp: {self._min_temp}; Max temp: {self._max_temp}; Current mode: {self._current_mode}; Switch state: {self._switch_state}; Current fan mode: {self._current_fan_mode}; Power consumption: {self._power_consumption};"
            )

        except Exception as e:
            _LOGGER.debug(
                f"State update failed to parse json, setting to unavailable: {str(e)}"
            )
            self._available = False

    async def async_set_temperature(self, **kwargs) -> None:
        target_temp = kwargs.get(ATTR_TEMPERATURE)
        if target_temp is None:
            return

        self._target_temp = target_temp
        if self._switch_state == "on":
            self.run_smartthings_command(
                f"thermostatCoolingSetpoint:setCoolingSetpoint({self._target_temp})"
            )

        self.schedule_update_ha_state(True)

    async def async_set_hvac_mode(self, **kwargs) -> None:
        hvac_mode = kwargs.get(ATTR_HVAC_MODE)
        if hvac_mode is None:
            return

        self._current_mode = hvac_mode
        if self._current_mode == "fan_only":
            self._current_mode = "wind"

        # Update switch state from current hvac mode
        prev_switch_state = self._switch_state
        self._switch_state = "off" if self._current_mode == "off" else "on"
        if prev_switch_state != self._switch_state:
            self.run_smartthings_command(f"switch:{self._switch_state}()")

        if self._switch_state == "on":

            # Update AC mode if the unit is switched on on
            self.run_smartthings_command(
                f"airConditionerMode:setAirConditionerMode({self._current_mode})"
            )

            # also update properties that may have changed while the unit was off
            if prev_switch_state != self._switch_state:
                self.run_smartthings_command(
                    f"thermostatCoolingSetpoint:setCoolingSetpoint({self._target_temp})"
                )
                self.run_smartthings_command(
                    f"airConditionerFanMode:setAirConditionerFanMode({self._current_fan_mode})"
                )

        self.schedule_update_ha_state(True)

    async def async_set_fan_mode(self, **kwargs) -> None:
        fan_mode = kwargs.get(ATTR_FAN_MODE)
        if fan_mode is None:
            return

        self._current_fan_mode = fan_mode

        if self._switch_state == "on":

            # Update AC fan mode if the unit is switched on on
            self.run_smartthings_command(
                f"airConditionerFanMode:setAirConditionerFanMode({self._current_fan_mode})"
            )

        self.schedule_update_ha_state(True)
