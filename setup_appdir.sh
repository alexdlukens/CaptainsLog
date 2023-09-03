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

# overwrite files from copy dir
mv squashfs-root AppDir

# re-package app image
./dist/appimagetool.AppImage ./AppDir ./dist/CaptainsLog.AppImage 

# potentially upload?