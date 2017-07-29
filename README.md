# moddodo for Ark: Survival Evolved
------------------------------
Improved Linux fork of [barrycarey/Ark_Mod_Downloader](https://github.com/barrycarey/Ark_Mod_Downloader) 

You cannot simply download ARK mods for linux servers via SteamCMD. The individual files come archived as .z files which will not work directly with a server.
This tool allows direct downloading of mods and extracting their .z files, so that you do not need to maintain anything else on the server.

## Usage

This tool is intended be run with python3.

### Commandline Arguments

- `--workingdir` - (optional) - home directory of the server (containing the `/ShooterGame` folder)
- `--modids` - space-separated list of steam IDs of the mod you wish to 
- `--steamcmd` - (optional) directory of the SteamCMD install you wish to use, if not under ~/steam/Steam
- `--update` - (optional) - update all mods currently installed on the server

### Example

## Credits
<a href="https://github.com/project-umbrella/arkit.py" target="_blank">arkit.py</a> - Used to extract the .z files