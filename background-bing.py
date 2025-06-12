#!/usr/bin/env python3
#
# Fetch the daily background wallpaper from Bing
# and change the local background
#
import logging
import os
import shutil
import subprocess
from os.path import expanduser
from xml.etree import ElementTree

import requests

BACK_LOG = 3  # backlog count of previous wallpapers
MARKET = "en-NZ"  # en-US, zh-CN, ja-JP, en-AU, en-UK, de-DE, en-NZ, en-CA
BING_HOST = "https://www.bing.com"
BING_URL = f"{BING_HOST}/HPImageArchive.aspx?format=xml&idx=0&n={BACK_LOG}&mkt={MARKET}"

WORKDIR = ".bing-background"


class BingWallpapers():
    """
    Wallpaper Repo
    """
    workdir = f"{expanduser('~')}/{WORKDIR}"

    def update(self):
        response = requests.get(BING_URL)
        tree = ElementTree.fromstring(response.content)
        for e_image in tree.iter("image"):
            name = e_image.find("startdate").text
            image_dir = f"{self.workdir}/{name}"
            if os.path.isdir(image_dir):
                logging.debug(f"{name} already exists")
                continue

            os.makedirs(image_dir)
            logging.debug(f"created {image_dir}")

            self.create_manifest(image_dir, e_image)

            url = e_image.find("url").text
            img_response = requests.get(f"{BING_HOST}/{url}")
            self.save_image(image_dir, img_response.content)

    def purge(self):
        """
        purge excess wallpapers
        """
        dirs = os.listdir(self.workdir)
        dirs.sort()
        for i in range(0, len(dirs) - BACK_LOG):
            path = f"{self.workdir}/{dirs[i]}"
            shutil.rmtree(path)
            logging.debug(f"purged={path}")

    def create_manifest(self, image_dir, node):
        path = f"{image_dir}/manifest"
        url = node.find("url").text
        description = node.find("copyright").text
        with open(path, "w") as output:
            output.write(f"description={description}\nurl={BING_HOST}/{url}\n")

    def save_image(self, wall_dir, content):
        path = f"{wall_dir}/image"
        with open(path, "wb") as output:
            output.write(content)

    def wallpaper(self):
        """
        :return: path to a wallpaper image, or None
        """
        dirs = os.listdir(self.workdir)
        dirs.sort(reverse=True)
        for d in dirs:
            path = f"{self.workdir}/{d}/image"
            if os.path.isfile(path):
                return path
        return None


class MateDesktopEnv():
    """
    MATE desktop env
    """
    get_background_cmd = "gsettings get org.mate.background picture-filename"
    set_background_cmd = "gsettings set org.mate.background picture-filename {path}"
    set_background_opt = "gsettings set org.mate.background picture-options stretched"

    def spawn(self, command):

        logging.debug(f"command={command}")
        done = subprocess.run(command, capture_output=True, text=True)
        info = f"set-background: exit={done.returncode}"
        if done.stdout:
            info += f", stdout=\"{done.stdout.strip()}\""
        if done.stderr:
            info += f", stderr=\"{done.stderr.strip()}\""
        logging.info(info)
        return done

    def get_background(self):

        done = self.spawn(self.get_background_cmd.split())
        if done.stdout:
            raw = done.stdout.strip()
            if raw:
                return raw[1:-1]  # ignore start and end "'"
        return None

    def set_background(self, path):
        """
        Set Background.
        :param path: path to new background
        :return:
        """
        if path == self.get_background():
            logging.debug(f"set: no-change")
            return

        self.spawn(self.set_background_cmd.replace("{path}", path).split())
        self.spawn(self.set_background_opt.split())


if __name__ == "__main__":
    logging.getLogger().setLevel(logging.DEBUG)

    wall = BingWallpapers()
    wall.update()
    wall.purge()

    MateDesktopEnv().set_background(wall.wallpaper())
