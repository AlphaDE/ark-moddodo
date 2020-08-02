# moddodo for Ark: Survival Evolved
------------------------------
Improved Linux fork of [barrycarey/Ark_Mod_Downloader](https://github.com/barrycarey/Ark_Mod_Downloader) 

You cannot simply download ARK mods for linux servers via SteamCMD. The individual files come archived as .z files which will not work directly with a server.
This tool allows direct downloading of mods and extracting their .z files, so that you do not need to maintain anything else on the server.

## Usage

This tool is intended be run with python3.

### Commandline Arguments

- `--serverdir PATH` - (optional) - home directory of the server (containing the `/ShooterGame` folder)
- `--localmoddir PATH` - (optional) - local directory for steam to download mods (usually ends with `/Steam/steamapps/workshop/content/346110`)
- `--modids ID [ID...]` - space-separated list of steam IDs of the mod you wish to install or update
- `--steamcmd PATH` - (optional) directory of the SteamCMD install you wish to use, if not under `~/steam/Steam`
- `--updatemods` - (optional) - update all mods currently installed on the server
- `--deletecache` - (optional) - deletes previously downloaded mods in SteamCMD for multi-server environments
- `--nodownload` - (optional) - prevents the execution of steamcmd to download/update the mods in the local directory, also ignores steamcmd parameter. This option allows the download the mods in a multi ark server environment once and then use a script and this tool to update the ark servers consecutively.


### Example

## Credits
<a href="https://github.com/project-umbrella/arkit.py" target="_blank">arkit.py</a> - Used to extract the .z files
