#!/bin/bash

wget -O dist/python3.11.AppImage https://github.com/niess/python-appimage/releases/download\
/python3.11/python3.11.1-cp311-cp311-manylinux_2_24_x86_64.AppImage

# get appbuildtool
wget -O dist/appimagetool.AppImage https://github.com/AppImage/AppImageKit/releases/download/continuous/\
appimagetool-x86_64.AppImage


# make app image executable
chmod +x dist/appimagetool.AppImage
chmod +x dist/python3.11.AppImage

# extract python app image
./dist/python3.11.AppImage --appimage-extract

[ -d "AppDir" ] && rm -r AppDir

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
./dist/appimagetool.AppImage ./AppDir ./dist/CaptainsLog.AppImage 

# potentially upload?