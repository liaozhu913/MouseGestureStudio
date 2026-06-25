from PyInstaller.utils.hooks import check_requirement
from PyInstaller.utils.hooks.qt import pyside6_library_info, ensure_single_qt_bindings_package


ensure_single_qt_bindings_package("PySide6")

if pyside6_library_info.version is not None:
    hiddenimports = ["shiboken6", "inspect"]
    if check_requirement("PySide6 >= 6.4.0"):
        hiddenimports += ["PySide6.support.deprecated"]

    binaries = [
        item
        for item in pyside6_library_info.collect_extra_binaries()
        if "opengl32sw.dll" not in item[0].lower()
    ]
