#!/bin/bash
set -e

# Get the directory of the script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# create dist dir
[ -d "$DIR/dist" ] || mkdir "$DIR/dist"

wget -O "$DIR/dist/python3.11.AppImage" https://github.com/niess/python-appimage/releases/download/python3.11/python3.11.1-cp311-cp311-manylinux_2_24_x86_64.AppImage

# get appbuildtool
wget -O "$DIR/dist/appimagetool.AppImage" https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage

# ensure that the appimage files exist
[ -f "$DIR/dist/appimagetool.AppImage" ] || exit 1
[ -f "$DIR/dist/python3.11.AppImage" ] || exit 1

# make app image executable
sudo chmod +x "$DIR/dist/appimagetool.AppImage"
sudo chmod +x "$DIR/dist/python3.11.AppImage"

# extract python app image
ls -la "$DIR/dist"
"$DIR/dist/python3.11.AppImage" --appimage-extract

[ -d "$DIR/AppDir" ] && rm -r "$DIR/AppDir"

# overwrite files from copy dir
mv squashfs-root AppDir
cp config/com.alexdlukens.CaptainsLog.desktop AppDir
cp config/com.alexdlukens.CaptainsLog.desktop AppDir/usr/share/applications
cp config/com.alexdlukens.CaptainsLog.svg AppDir
cp config/com.alexdlukens.CaptainsLog.svg AppDir/usr/share/icons/hicolor/256x256/apps
cp config/CaptainsLog.appdata.xml AppDir/usr/share/metainfo
cp config/AppRun AppDir
cp dist/CaptainsLog AppDir/usr/bin
rm AppDir/usr/share/metainfo/python*

# re-package app image
dist/appimagetool.AppImage AppDir dist/CaptainsLog.AppImage

# potentially upload?
