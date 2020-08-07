#!/usr/bin/python3

import arkit
import sys
import os
import argparse
import shutil
import subprocess
import tempfile
from collections import OrderedDict
import struct

SERVER_MOD_DIRECTORY = "ShooterGame/Content/Mods"

STEAMCMD_STEAMAPPS = "/usr/game/"
STEAMCMD_MODS_PATH = "~/.local/share/Steam/steamapps/workshop/content/346110"

SERVER_CHECK_PATH = "ShooterGame/Content"
STEAMCMD_SCRIPT = "steamcmd"

WINDOWS_NOEDITOR = "WindowsNoEditor"
WINDOWS_NOEDITOR_MODFILE = WINDOWS_NOEDITOR + ".mod"
WINDOWS_NOEDITOR_MOD_INFO = WINDOWS_NOEDITOR + "/mod.info"
WINDOWS_NOEDITOR_MODMETA_INFO = WINDOWS_NOEDITOR + "/modmeta.info"


class ModDodo:
    def __init__(self, steamcmd_directory, modids, server_directory, local_mod_directory, mod_update, steamcmd_delete_cache, no_download, force_update):
        self.steamcmd_directory = steamcmd_directory
        self.server_directory = server_directory

        self.check_server_directory()
        if not no_download:
            self.check_steamcmd_directory()

        if not modids:
            modids = []
        if mod_update:
            self.append_installed_mods(modids)

        print("Installing mods: " + ', '.join(modids))

        # Mod/.z/UE magic stuff
        self.map_names = []  # stores map names from mod.info
        self.meta_data = OrderedDict([])  # stores key value from modmeta.info

        if local_mod_directory is '.':
          self.download_mod_directory = os.path.expanduser(STEAMCMD_MODS_PATH)
        else:
          self.download_mod_directory = os.path.normpath(local_mod_directory)

        print("Mod directory: " + self.download_mod_directory)

        if not no_download:
            if steamcmd_delete_cache:
                self.delete_steamcmd_cache()

        if not no_download:
            if not self.download_mods(modids):
                print_error("Could not download mods")
                sys.exit(1)

        # SteamCMD does not properly break lines
        print("")

        for modid in modids:
            if os.path.isfile(os.path.join(self.download_mod_directory, modid, WINDOWS_NOEDITOR, "mod.info")):
                steammodftime=os.path.getmtime(os.path.join(self.download_mod_directory, modid, WINDOWS_NOEDITOR, "mod.info"))
            else:
                steammodftime=1
            if os.path.isfile(os.path.join(self.server_directory, SERVER_MOD_DIRECTORY, modid, "mod.info")):
                arkmodftime=os.path.getmtime(os.path.join(self.server_directory, SERVER_MOD_DIRECTORY, modid, "mod.info"))
            else:
                arkmmodftime=0
            if mod_update and steammodftime <= arkmodftime and force_update:
                continue
            self.workdir = tempfile.mkdtemp()
            if self.extract_mod(modid):
                if self.create_mod_file(modid):
                    if self.move_mod(modid):
                        print("Mod " + str(modid) + " successfully installed")
                    else:
                        print_error("Could not move mod " + str(modid))
                else:
                    print_error("Could not create .mod file for mod " + str(modid))
            else:
                print_error("Could not extract mod " + str(modid))
            shutil.rmtree(self.workdir)

    def check_server_directory(self):
        if not os.path.isdir(os.path.join(self.server_directory, SERVER_CHECK_PATH)):
            print_error("Given server directory " + self.server_directory + " does not contain '" + SERVER_CHECK_PATH + "'")
            sys.exit(1)
        else:
            print("Installing mods for server: " + self.server_directory)

    def check_steamcmd_directory(self):
        if not os.path.isfile(os.path.join(self.steamcmd_directory, STEAMCMD_SCRIPT)):
            print_error("Given SteamCMD directory " + self.steamcmd_directory + " does not contain '" + STEAMCMD_SCRIPT + "'\n"
                        + "\tSee https://developer.valvesoftware.com/wiki/SteamCMD#Linux on how to install")
            sys.exit(1)
        else:
            print("Using SteamCMD: " + self.steamcmd_directory)

    def delete_steamcmd_cache(self):
        """
        Deleting the steamapp folder intends to prevent Steam from thinking it has downloaded this mod before.
        This is useful for hosts using TCAdmin which only have one SteamCMD folder. If a mod was downloaded
        by another customer, SteamCMD will think it already exists and not download it again. This means the old version
        will still be used.
        """
        steamapps = os.path.join(os.path.dirname(self.steamcmd_directory), STEAMCMD_STEAMAPPS)

        if os.path.isdir(steamapps):
            print("Trying to remove " + STEAMCMD_STEAMAPPS + " folder...")
            try:
                shutil.rmtree(steamapps)
                print("Success")
            except OSError:
                print_error("Failed to remove " + STEAMCMD_STEAMAPPS + " folder. Usually this does not indicate a problem.\n"
                            + "If this is a TCAdmin Server and you're using the TCAdmin SteamCMD it may prevent mods from updating.")

    def append_installed_mods(self, modids):
        print("Gurr. Reading installed mods...")

        if not os.path.isdir(os.path.join(self.server_directory, SERVER_MOD_DIRECTORY)):
            print_error("Given server directory " + self.server_directory + " does not contain " + SERVER_MOD_DIRECTORY + ".\n"
                        + "Cannot find any mods to update.")
            return
        for current_dir, directories, files in os.walk(os.path.join(self.server_directory, SERVER_MOD_DIRECTORY)):
            for directory in directories:
                # AFAIK these are updated by Ark itself, maybe only with -automanagedmods, 834585900 and 916417001 are maps
                if directory.isdigit() and directory not in ["111111111", "834585900", "916417001"]:
                    modids.append(directory)
            break

    def download_mods(self, modids):
        args = [os.path.join(self.steamcmd_directory, STEAMCMD_SCRIPT), "+login anonymous"]
        for modid in modids:
            args.extend(["+workshop_download_item", "346110", modid])
        args.append("+quit")
        try:
            return subprocess.call(args) == 0
        except Exception as e:
            print_error("Could not start steamcmd to download mods:\n" + str(e))
            sys.exit(1)

    def extract_mod(self, modid):
        """
        Extract the .z files using the arkit lib.
        :returns false, if any file fails to download
        """
        print("- Extracting mod " + str(modid) + "...")

        if not os.path.exists(os.path.join(self.download_mod_directory, modid, WINDOWS_NOEDITOR)):
            print_error("Mod directory does not exist in local mod repository")
            return False

        try:
            srcdir = os.path.join(self.download_mod_directory, modid, WINDOWS_NOEDITOR)
            destdir = os.path.join(self.workdir, modid)
            for curdir, subdirs, files in os.walk(srcdir):
                os.makedirs(os.path.join(destdir, os.path.relpath(curdir, srcdir)), 0o770, True)
                for file in files:
                    name, ext = os.path.splitext(file)
                    if ext == ".z":
                        src = os.path.join(curdir, file)
                        dst = os.path.join(destdir, os.path.relpath(curdir, srcdir), name)
                        arkit.unpack(src, dst)
                        shutil.copystat(src,dst)
                        uncompressed = os.path.join(curdir, file + ".uncompressed_size")
                        with open(uncompressed, "r") as fd:
                             unpacked_size = int(fd.read())
                             if os.stat(dst).st_size != unpacked_size:
                                print_error ("Wrong file size "+dst)
                                return False
                    if ext == ".info":
                        src = os.path.join(curdir, file)
                        dst = os.path.join(destdir, os.path.relpath(curdir, srcdir), file)
                        shutil.copy2(src, dst)
                        shutil.copystat(src,dst)
            for curdir, subdir, files in os.walk(srcdir):
                dstdirattr = os.path.join(destdir, os.path.relpath(curdir, srcdir))
                shutil.copystat(curdir,dstdirattr)
            shutil.copystat(curdir,destdir)

            return True

        except (arkit.UnpackException, arkit.SignatureUnpackException, arkit.CorruptUnpackException) as e:
            print_error(str(e))
            return False

    def create_mod_file(self, modid):
        """
        Create the .mod file.
        This code is an adaptation of the code from Ark Server Launcher.  All credit goes to Face Wound on Steam
        """
        print("- Writing .mod file...")
        if not self.parse_base_info(modid) or not self.parse_meta_data(modid):
            return False

        with open(os.path.join(self.workdir, modid+".mod"), "w+b") as f:

            modid = int(modid)
            f.write(struct.pack('ixxxx', modid))  # Needs 4 pad bits
            self.write_ue4_string("ModName", f)
            self.write_ue4_string("", f)

            map_count = len(self.map_names)
            f.write(struct.pack("i", map_count))

            for m in self.map_names:
                self.write_ue4_string(m, f)

            # Not sure of the reason for this
            num2 = 4280483635
            f.write(struct.pack('I', num2))
            num3 = 2
            f.write(struct.pack('i', num3))

            if "ModType" in self.meta_data:
                mod_type = b'1'
            else:
                mod_type = b'0'

            # TODO The packing on this char might need to be changed
            f.write(struct.pack('p', mod_type))
            meta_length = len(self.meta_data)
            f.write(struct.pack('i', meta_length))

            for k, v in self.meta_data.items():
                self.write_ue4_string(k, f)
                self.write_ue4_string(v, f)

        return True

    def move_mod(self, modid):
        """
        Move mod from SteamCMD download location to the ARK server.
        It will delete an existing mod with the same ID
        """

        print("- Moving mod...")

        ark_mod_directory = os.path.join(self.server_directory, SERVER_MOD_DIRECTORY)
        target_mod_directory = os.path.join(ark_mod_directory, str(modid))
        source_mod_directory = os.path.join(self.workdir)

        try:
            if not os.path.isdir(ark_mod_directory):
                    os.mkdir(ark_mod_directory)

            if os.path.isdir(target_mod_directory):
                shutil.rmtree(target_mod_directory)

            shutil.move(os.path.join(source_mod_directory, str(modid)), target_mod_directory)

            shutil.move(os.path.join(source_mod_directory, str(modid)+".mod"), os.path.join(ark_mod_directory, str(modid)+".mod"))
            os.chmod(os.path.join(ark_mod_directory, str(modid)+".mod"), 0o600)
            os.chmod(os.path.join(target_mod_directory, "modmeta.info"), 0o660)
            os.chmod(os.path.join(target_mod_directory, "mod.info"), 0o660)
            shutil.copystat(os.path.join(target_mod_directory, "mod.info"), os.path.join(ark_mod_directory, str(modid)+".mod"))

            return True
        except Exception as e:
            print_error("Encountered unexpected exception during move operation from " + source_mod_directory + " to " + ark_mod_directory + ":\n"
                        + str(e))
            return False

    def read_ue4_string(self, file):
        count = struct.unpack('i', file.read(4))[0]
        flag = False
        if count < 0:
            flag = True
            count -= 1

        if flag or count <= 0:
            return ""

        return file.read(count)[:-1].decode()

    def write_ue4_string(self, string_to_write, file):
        string_length = len(string_to_write) + 1
        file.write(struct.pack('i', string_length))
        barray = bytearray(string_to_write, "utf-8")
        file.write(barray)
        file.write(struct.pack('p', b'0'))

    def parse_meta_data(self, modid):
        """
        Parse the modmeta.info files and extract the key value pairs need to for the .mod file.
        How To Parse modmeta.info:
            1. Read 4 bytes to tell how many key value pairs are in the file
            2. Read next 4 bytes tell us how many bytes to read ahead to get the key
            3. Read ahead by the number of bytes retrieved from step 2
            4. Read next 4 bytes to tell how many bytes to read ahead to get value
            5. Read ahead by the number of bytes retrieved from step 4
            6. Start at step 2 again
        :return: Dict
        """

        mod_meta = os.path.join(self.download_mod_directory, modid, WINDOWS_NOEDITOR_MODMETA_INFO)
        if not os.path.isfile(mod_meta):
            print_error("Could not find " + WINDOWS_NOEDITOR_MODMETA_INFO + " in " + self.download_mod_directory + "/" + modid)
            return False

        with open(mod_meta, "rb") as f:

            total_pairs = struct.unpack('i', f.read(4))[0]

            for i in range(total_pairs):

                key, value = "", ""

                key_bytes = struct.unpack('i', f.read(4))[0]
                key_flag = False
                if key_bytes < 0:
                    key_flag = True
                    key_bytes -= 1

                if not key_flag and key_bytes > 0:
                    raw = f.read(key_bytes)
                    key = raw[:-1].decode()

                value_bytes = struct.unpack('i', f.read(4))[0]
                value_flag = False
                if value_bytes < 0:
                    value_flag = True
                    value_bytes -= 1

                if not value_flag and value_bytes > 0:
                    raw = f.read(value_bytes)
                    value = raw[:-1].decode()

                if key == "" or value == "":
                    print_error("Found potentially bad mapping: " + key + " = " + value + "\n"
                                + "Skipping and trying to continue anyway...")

                if key and value:
                    print("   * " + key + " = " + value)
                    self.meta_data[key] = value

        return True

    def parse_base_info(self, modid):
        mod_info = os.path.join(self.download_mod_directory, modid, WINDOWS_NOEDITOR_MOD_INFO)

        if not os.path.isfile(mod_info):
            print_error("Could not find " + WINDOWS_NOEDITOR_MOD_INFO + " in " + self.download_mod_directory + "/" + modid)
            return False

        with open(mod_info, "rb") as f:
            self.read_ue4_string(f)
            map_count = struct.unpack('i', f.read(4))[0]

            for i in range(map_count):
                cur_map = self.read_ue4_string(f)
                if cur_map:
                    self.map_names.append(cur_map)

        return True


def print_error(msg):
    print("\n[ERROR] " + msg)


def main():
    parser = argparse.ArgumentParser(description="Installs ARK Linux server mods via SteamCMD")
    parser.add_argument("--serverdir", default=".", dest="serverdir", help="home directory of the server (containing the /ShooterGame folder)")
    parser.add_argument("--localmoddir", default=".", dest="localmoddir", help="local directory where steam downloads mods (usually ~/.local/share/Steam/steamapps/workshop/content/346110")
    parser.add_argument("--modids", nargs="+", default=None, dest="modids", help="space-separated list of IDs of mods to install")
    parser.add_argument("--steamcmd", default="/usr/games", dest="steamcmd", help="path to SteamCMD, default: /usr/games")
    parser.add_argument("--updatemods", "-u", default=False, action="store_true", dest="updatemods", help="update existing mods")
    parser.add_argument("--force", "-f", default=False, action="store_true", dest="forceupdate", help="force update of mods on -u (also when not newer)")
    parser.add_argument("--deletecache", "-d", default=False, action="store_true", dest="deletecache", help="Delete SteamCMD cache, if used in multi-server environment")
    parser.add_argument("--nodownload", "-nd", default=False, action="store_true", dest="nodownload", help="Skip download via steamcmd")

    args = parser.parse_args()

    if not args.modids and not args.updatemods:
        print_error("Neither mod ids provided nor update requested. Don't know what to dodo.")
        print(parser.format_help())
        sys.exit(1)

    ModDodo(args.steamcmd,
            args.modids,
            args.serverdir,
            args.localmoddir,
            args.updatemods,
            args.deletecache,
            args.nodownload,
            args.forceupdate)


if __name__ == '__main__':
    main()
