#!/usr/bin/python

"""
    11-01-2020
    Author: Naman Jain

    Converting Kivy App to Windows Executable
"""

import os
# import sys
import logging


def main():
    """
    Main Function
    :return:
    """
    logging.basicConfig(level=logging.NOTSET)

    # python = sys.executable
    app_name = "PyMTag"
    # main_file = "py_main.py"
    # Generating specification file
    # spec_cmd = rf"{python} -m PyInstaller -y --noconsole --name {app_name} --icon images/app_icon.ico py_main.py"

    logging.info(f"Generating Specification file...")
    # os.system(spec_cmd)

    input("Please Edit the spec file and press enter to continue...")

    logging.info(f"Specification file generated: {app_name}.spec")

    logging.info(f"Generating Executable file with application name: {app_name}")

    exe_cmd = rf"python -m PyInstaller -y {app_name}.spec"
    os.system(exe_cmd)

    logging.info(f"Executable generation process completed: {app_name}.exe")


if __name__ == '__main__':
    main()

else:
    raise RuntimeError("This module should not be imported and is designed to executed as main script")
