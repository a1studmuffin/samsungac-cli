import json
import logging
import subprocess
import voluptuous
import homeassistant.helpers.config_validation as cv
from homeassistant.const import UnitOfTemperature
from homeassistant.components import climate
from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature, HVACMode, HVACAction, PLATFORM_SCHEMA
from homeassistant.components.climate import (
    ATTR_HVAC_MODE,
    ATTR_FAN_MODE,
    FAN_AUTO,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_HIGH,
    FAN_OFF,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    CONF_NAME,
    CONF_ACCESS_TOKEN,
    CONF_DEVICE_ID,
)
from homeassistant.helpers.typing import ConfigType
from homeassistant.core import HomeAssistant

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
    hass: HomeAssistant, config: ConfigType, async_add_entities, discovery_info=None
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
        self._current_fan_mode = None
        self._switch_state = None
        self._min_temp = 0
        self._max_temp = 0
        self._current_temp = 0
        self._target_temp = 0
        self._mode = None
        self._action = None
        self._fan_mode = None
        self._available = False
        self._attributes = {}

    @property
    def name(self) -> str:
        return self._name

    @property
    def available(self) -> bool:
        return self._available

    @property
    def supported_features(self) -> int:
        return ClimateEntityFeature.TURN_ON | ClimateEntityFeature.TURN_OFF | ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.FAN_MODE

    @property
    def hvac_mode(self):
        return self._mode

    @property
    def hvac_action(self) -> str:
        return self._action

    @property
    def hvac_modes(self) -> list:
        return [
            HVACMode.AUTO,
            HVACMode.COOL,
            HVACMode.DRY,
            HVACMode.FAN_ONLY,
            HVACMode.HEAT,
            HVACMode.OFF,
        ]

    @property
    def min_temp(self) -> float:
        return self._min_temp

    @property
    def max_temp(self) -> float:
        return self._max_temp

    @property
    def temperature_unit(self) -> str:
        return UnitOfTemperature.CELSIUS

    @property
    def current_temperature(self) -> float:
        return self._current_temp

    @property
    def target_temperature(self) -> float:
        return self._target_temp

    @property
    def target_temperature_step(self) -> float:
        return 1.0

    @property
    def fan_mode(self) -> str:
        return self._fan_mode

    @property
    def fan_modes(self) -> list:
        return [FAN_AUTO, FAN_LOW, FAN_MEDIUM, FAN_HIGH]

    @property
    def extra_state_attributes(self) -> int:
        return self._attributes

    def run_smartthings_command(self, command, arguments):
        try:
            smartthings_command = f"{self._smartthings_path} {command} {self._device_id} {arguments} -j --token {self._access_token}"
            _LOGGER.debug(smartthings_command)
            result = subprocess.run(
                smartthings_command.split(), capture_output=True, text=True
            )
            _LOGGER.debug(result.stdout)
            _LOGGER.debug(result.stderr)
            return result.stdout
        except Exception as e:
            _LOGGER.debug(f"run_smartthings_command() failed: {str(e)}")
            return ""

    async def async_update(self):
        device_status_text = self.run_smartthings_command("devices:status", "")
        try:
            device_status_json = json.loads(device_status_text)

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

            self._current_temp = int(
                device_status_json["components"]["main"]["temperatureMeasurement"][
                    "temperature"
                ]["value"]
            )

            self._target_temp = int(
                device_status_json["components"]["main"]["thermostatCoolingSetpoint"][
                    "coolingSetpoint"
                ]["value"]
            )

            self._current_mode = device_status_json["components"]["main"][
                "airConditionerMode"
            ]["airConditionerMode"]["value"]

            self._switch_state = device_status_json["components"]["main"]["switch"][
                "switch"
            ]["value"]
            if self._switch_state == "off":
                self._action = HVACAction.OFF
                self._mode = HVACMode.OFF
            elif self._current_mode == "auto":
                if (
                    self._target_temp > self._current_temp + 1
                ):  # todo - can we get real hvac action here rather than faking it?
                    self._action = HVACAction.HEATING
                elif self._target_temp < self._current_temp - 1:
                    self._action = HVACAction.COOLING
                else:
                    self._action = HVACAction.IDLE
                self._mode = HVACMode.AUTO
            elif self._current_mode == "cool":
                self._action = HVACAction.COOLING
                self._mode = HVACMode.COOL
            elif self._current_mode == "heat":
                self._action = HVACAction.HEATING
                self._mode = HVACMode.HEAT
            elif self._current_mode == "dry":
                self._action = HVACAction.DRYING
                self._mode = HVACMode.DRY
            elif self._current_mode == "wind":
                self._action = HVACAction.FAN
                self._mode = HVACMode.FAN_ONLY
            else:
                self._action = HVACAction.OFF
                self._mode = HVACMode.OFF
                _LOGGER.debug(f"Unknown HVAC current mode: {str(self._current_mode)}")

            self._current_fan_mode = device_status_json["components"]["main"][
                "airConditionerFanMode"
            ]["fanMode"]["value"]
            if self._current_fan_mode == "auto":
                self._fan_mode = FAN_AUTO
            elif self._current_fan_mode == "low":
                self._fan_mode = FAN_LOW
            elif self._current_fan_mode == "medium":
                self._fan_mode = FAN_MEDIUM
            elif self._current_fan_mode == "high":
                self._fan_mode = FAN_HIGH
            else:
                self._fan_mode = FAN_OFF
                _LOGGER.debug(f"Unknown fan mode: {str(self._current_fan_mode)}")

            current_power = (
                device_status_json["components"]["main"]["powerConsumptionReport"][
                    "powerConsumption"
                ]["value"]["power"]
                * 1000
            )  # kW to W
            if self._mode == HVACMode.OFF:
                current_power = 0

            self._attributes = {"current_power": current_power}

            self._available = True

            _LOGGER.debug(
                f"State update complete, Target temp: {self._target_temp}; Current temp: {self._current_temp}; Min temp: {self._min_temp}; Max temp: {self._max_temp}; Current mode: {self._current_mode}; Switch state: {self._switch_state}; Current fan mode: {self._current_fan_mode}; Current power: {current_power};"
            )

        except Exception as e:
            self._available = False
            _LOGGER.debug(
                f"State update failed to parse json, setting to unavailable: {str(e)}"
            )

    async def async_set_temperature(self, **kwargs) -> None:
        target_temp = kwargs.get(ATTR_TEMPERATURE)
        if target_temp is None:
            return

        _LOGGER.debug(f"async_set_temperature({target_temp})")

        self.run_smartthings_command(
            "devices:commands",
            f"thermostatCoolingSetpoint:setCoolingSetpoint({int(target_temp)})",
        )

        self.schedule_update_ha_state(True)

    async def async_set_hvac_mode(self, **kwargs) -> None:
        hvac_mode = kwargs.get(ATTR_HVAC_MODE)
        if hvac_mode is None:
            return

        _LOGGER.debug(f"async_set_hvac_mode({hvac_mode})")

        if hvac_mode == "fan_only":
            hvac_mode = "wind"

        # Update switch state from current hvac mode
        switch_state = "off" if hvac_mode == "off" else "on"
        self.run_smartthings_command("devices:commands", f"switch:{switch_state}()")

        if switch_state == "on":
            self.run_smartthings_command(
                "devices:commands",
                f'airConditionerMode:setAirConditionerMode("{hvac_mode}")',
            )

            # also update properties that may have changed while the unit was off
            # if self._target_temp:
            #     self.run_smartthings_command(
            #         "devices:commands",
            #         f"thermostatCoolingSetpoint:setCoolingSetpoint({int(self._target_temp)})",
            #     )

            # if self._current_fan_mode:
            #     self.run_smartthings_command(
            #         "devices:commands",
            #         f'airConditionerFanMode:setFanMode("{self._current_fan_mode}")',
            #     )

        self.schedule_update_ha_state(True)

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        if fan_mode is None:
            return

        _LOGGER.debug(f"async_set_fan_mode({fan_mode})")

        if self._switch_state == "on":
            self.run_smartthings_command(
                "devices:commands",
                f'airConditionerFanMode:setFanMode("{fan_mode}")',
            )

        self.schedule_update_ha_state(True)

    async def async_added_to_hass(self):
        self.schedule_update_ha_state(True)
