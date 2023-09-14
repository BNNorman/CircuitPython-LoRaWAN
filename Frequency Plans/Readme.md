# Readme.md

Settings.json contains the default frequency plan for EU_863_870_TTN if you want to change it you need to edit the settings.json file and change all the entries from, and including, the TTN section.

AU_915_928_FSB_2.json can be used to replace the default. Don't be tempted to include both sections because that just uses up memory unneccessarily and the TTN sections would differ (Room for code improvement there).


# TTN Frequency plans

https://www.thethingsnetwork.org/docs/lorawan/frequency-plans/

Note that AU downlink frequencies and data rates depend on the uplink channel and data rate. So if you uplink on channel 1 (916.8MHz SF7-12 BW125) your downlink will be channel 1 (923.3MHz SSF7-12 BW500). RX2 is always 923.3 SF12 BW500.
