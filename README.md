# missedBlocksSwitcher
Modified version of roelandp's python script to switch witness signing keys on too many missed blocks

- Now uses the automatic node selection built into Python-Bitshares
- Allows for resetting the missed block accounting when node OK for awhile
- Provides for a list of alternate nodes to switch witness to
- Logs info to a file
- Confirms switch to new witness signing key
- Displays info on cmd line for current (public) signing key, missed blocks and "flip" counter
- Written as a Python-Bitshares `standalone` program that doesn't require uptick or external means to initialize the Python-Bitshares internal sqlite wallet
