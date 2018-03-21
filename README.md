# missedBlocksSwitcher
Modified version of roelandp's python script to switch witness signing keys on too many missed blocks

- Now uses the automatic node selection built into Python-Bitshares
- Allows for resetting the missed block accounting when node OK for awhile
- Provides for a list of alternate nodes to switch witness to
- logs info to a file
- displays info on cmd line for current (public) signing key, missed blocks and "flip" counter
- Written as a Python-Bitshares `standalone` program that doesn't require uptick or external means to initialize the Python-Bitshares internal sqlite wallet
