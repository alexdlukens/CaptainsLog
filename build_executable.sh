#!/bin/bash
pyinstaller CaptainsLog.spec
cp dist/CaptainsLog AppDir/usr/bin/CaptainsLog
./appbuildtool.AppImage AppDir dist/CaptainsLog.AppImage