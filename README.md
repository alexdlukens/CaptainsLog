# CaptainsLog
A GUI Docker log viewer

## Why

- Want to keep track of logs for docker containers that keep restarting
- Provide search functionality for logs
- Quickly enter bash terminal on docker containers
- Rapidly save docker logs to file/clipboard
- Potentially integrate docker log saving with third-party applications (e.g Slack)


## About

Designing in Python using GTK4 and Adwaita

Intend to release as executable, using Pyinstaller.
Potentially add CI/CD using Github

## Setup

To install all dependencies for CaptainsLog, run the following commands from the base directory of this project.

```bash
poetry config virtualenvs.in-project true
poetry install
```

To build the project, then run

```bash
./build_executable.sh
./setup_appdir.sh
```

This will build the executable using pyinstaller, and download all requisite AppImage tools for building CaptainsLog.
It will produce an AppImage in the dist/ folder: CaptainsLog.AppImage that can be run on any machine.