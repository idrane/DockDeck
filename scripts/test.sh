#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
mkdir -p .build
xcrun swiftc -swift-version 5 -module-cache-path .build/ModuleCache Sources/DockModel.swift tests/main.swift -o .build/model-tests
.build/model-tests
python3 tests/package.py
