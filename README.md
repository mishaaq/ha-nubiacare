# Nubia Care for Home Assistant

This custom integration connects to a Nubia Care account and creates a Home
Assistant device, GPS device tracker, and battery sensor for each watch
associated with that account. Trackers use the latest location reported by
Nubia Care and appear on the Home Assistant map when a location is available.
The battery sensor reports the latest battery percentage provided by Nubia
Care.

## Installation

Install this integration with HACS as a custom repository, or copy the
`custom_components/nubiacare` directory into your Home Assistant
`config/custom_components` directory. Restart Home Assistant after installing.

## Configuration

In Home Assistant, go to **Settings → Devices & services → Add integration**,
search for **Nubia Care**, and enter the username and password for your Nubia
Care account. The integration checks the credentials and retrieves the account
devices before completing setup.

On setup or reload, the integration retrieves the account's current device
list, fetches each device's installed firmware version for Home Assistant's
device information, and polls current state every ten minutes. Newly
associated devices are discovered after the integration is reloaded. Devices
without a reported location remain available but have no map coordinates until
the service provides a location. Home Assistant's standard GPS attributes are
numeric floats. Credentials are stored in the config entry;
authentication tokens are kept in memory and renewed when Home Assistant
starts.

## Actions

Use the **Nubia Care: Refresh location** action in an automation or script
to ask a watch to report its current location. Select the watch as the device
target. The integration waits about 10 seconds after the request, then refreshes
its device data.

## Removal

Remove the integration from **Settings → Devices & services**. Home Assistant
will stop polling Nubia Care and unload the account's entities.
