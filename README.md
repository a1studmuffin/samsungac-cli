# SmartThings CLI climate entity for Home Assistant

A Home Assistant custom component to control Samsung HVAC units via [SmartThings CLI](https://github.com/SmartThingsCommunity/smartthings-cli).  
This is an alternative to the official [SmartThings integration](https://www.home-assistant.io/integrations/smartthings), and doesn't require SSL or Home Assistant Cloud subscription.  
Tested using a Samsung MIM-H04AN wifi kit with air conditioner model AC160JNHFKH/SA.  

## Installation

1. Install via HACS, or manually copy the files in `/custom_components/samsungac-cli/` to `<config directory>/custom_components/samsungac-cli`.
2. Install the `smartthings` binary on your Home Assistant install.  
   eg. For Home Assistant OS running on a Raspberry Pi, in a Terminal window type:
   ```
   wget -c https://github.com/SmartThingsCommunity/smartthings-cli/releases/download/%40smartthings%2Fcli%401.0.1/smartthings-linuxstatic-armv7.tar.gz -O - | tar -xz -C /usr/local/bin/
   ```
   This will download and extract the `smartthings` binary to `/usr/local/bin/smartthings`.

## Configuration

### configuration.yaml

```yaml
climate:
  - platform: samsungac-cli
    name: My Samsung AC
    access_token: !secret smartthings_personal_access_token
    device_id: !secret smartthings_device_id
    smartthings_path: /usr/local/bin/smartthings
```
### secrets.yaml

```yaml
smartthings_personal_access_token: <your_personal_access_token>
smartthings_device_id: <your_device_id>
```
### Configuration variables

key | description  
:--- | :---  
**access_token (Required)** | Your SmartThings Personal Access Token (PAT). To create one, follow the "Personal Access Token (PAT)" steps [here](https://www.home-assistant.io/integrations/smartthings/#personal-access-token-pat).
**device_id (Required)** | The device ID of your SmartThings HVAC unit. Find this using SmartThings CLI's ['devices' command](https://github.com/SmartThingsCommunity/smartthings-cli#smartthings-devices-id).
**smartthings_path (Required)** | The path on your Home Assistant instance to the `smartthings` binary.
