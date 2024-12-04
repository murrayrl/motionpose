import os
import platform
import sys
import re
import requests
import argparse
from pathlib import Path
import subprocess
import sys
import math
import shutil

ZED_SDK_MAJOR = ""
ZED_SDK_MINOR = ""

PYTHON_MAJOR = ""
PYTHON_MINOR = ""

OS_VERSION = ""
ARCH_VERSION = platform.machine()

whl_platform_str = ""

base_URL = "https://download.stereolabs.com/zedsdk/"

def pip_install(package, force_install=False, ignore_install=False, upgrade=False):
    try:
        call_list = [sys.executable, "-m", "pip", "install"]
        if ignore_install:
            call_list.append("--ignore-installed")
        if force_install:
            call_list.append("--force-reinstall")
        if upgrade:
            call_list.append("--upgrade")
        call_list.append(package)
        err = subprocess.check_call(call_list)
    except Exception as e:
        err = 1
        # print("DEBUG : Exception " + str(e))
    # print("DEBUG : " + package + " errcode " + str(err))
    return err


def check_valid_file(file_path):
    try:
        file_size = os.stat(file_path).st_size / 1000.
    except FileNotFoundError:
        file_size=0
    # size > 150 Ko
    return (file_size > 150)


def install_win_dep(name, py_vers):
    whl_file = name + "-3.1.5-cp" + str(py_vers) + "-cp" + str(py_vers)
    if py_vers <= 37:
        whl_file = whl_file + "m"
    if py_vers >= 310:
        whl_file = name + "-3.1.6-cp" + str(py_vers) + "-cp" + str(py_vers)
    whl_file = whl_file + "-win_amd64.whl"

    whl_file_URL = "https://download.stereolabs.com/py/" + whl_file
    print("-> Downloading " + whl_file)
    whl_file = os.path.join(dirname, whl_file)
    r = requests.get(whl_file_URL, allow_redirects=True)
    open(whl_file, 'wb').write(r.content)
    pip_install(whl_file)


def get_pyzed_directory():
    try:
        call_list = [sys.executable, "-m", "pip", "show", "pyzed"]
        lines = subprocess.check_output(call_list).decode().splitlines()
        for line in lines:
            key_word = "Location:"
            if line.startswith(key_word):
                directory = line[len(key_word):].strip()
                if os.path.isdir(directory):
                    print("Pyzed directory is " + directory)
                    return directory + "/pyzed"
                else:
                    print("ERROR : '" + directory + "' is not a directory")

        print("ERROR : Unable to find pyzed installation folder")
        print(lines)

    except Exception as e:
        print("ERROR : Unable to find pyzed installation folder.")
        return ""


def check_zed_sdk_version_private(file_path):
    global ZED_SDK_MAJOR
    global ZED_SDK_MINOR

    with open(file_path, "r", encoding="utf-8") as myfile:
        data = myfile.read()

    p = re.compile("ZED_SDK_MAJOR_VERSION (.*)")
    ZED_SDK_MAJOR = p.search(data).group(1)

    p = re.compile("ZED_SDK_MINOR_VERSION (.*)")
    ZED_SDK_MINOR = p.search(data).group(1)


def check_zed_sdk_version(file_path):
    file_path_ = file_path + "/sl/Camera.hpp"
    try:
        check_zed_sdk_version_private(file_path_)
    except AttributeError:
        file_path_ = file_path + "/sl_zed/defines.hpp"
        check_zed_sdk_version_private(file_path_)


parser = argparse.ArgumentParser(description='Helper script to download and setup the ZED Python API')
parser.add_argument('--path', help='whl file destination path')
args = parser.parse_args()

arch = platform.architecture()[0]
if arch != "64bit":
    print("ERROR : Python 64bit must be used, found " + str(arch))
    sys.exit(1)

# If path empty, take pwd
dirname = args.path or os.getcwd()

# If no write access, download in home
if not (os.path.exists(dirname) and os.path.isdir(dirname) and os.access(dirname, os.W_OK)):
    dirname = str(Path.home())

print("-> Downloading to '" + str(dirname) + "'")

if sys.platform == "win32":
    zed_path = os.getenv("ZED_SDK_ROOT_DIR")
    if zed_path is None:
        print("Error: you must install the ZED SDK.")
        sys.exit(1)
    else:
        check_zed_sdk_version(zed_path + "/include")
    OS_VERSION = "win" + "_" + str(ARCH_VERSION).lower()
    whl_platform_str = "win"

elif "linux" in sys.platform:

    if "aarch64" in ARCH_VERSION:
        OS_VERSION = "linux_aarch64"
    else:
        OS_VERSION = "linux_x86_64"

    zed_path = "/usr/local/zed"
    if not os.path.isdir(zed_path):
        print("Error: you must install the ZED SDK.")
        sys.exit(1)
    check_zed_sdk_version(zed_path + "/include")
    whl_platform_str = "linux"
else:
    print("Unknown system.platform: %s  Installation failed, see setup.py." % sys.platform)
    sys.exit(1)

PYTHON_MAJOR = platform.python_version().split(".")[0]
PYTHON_MINOR = platform.python_version().split(".")[1]

whl_python_version = "-cp" + str(PYTHON_MAJOR) + str(PYTHON_MINOR) + "-cp" + str(PYTHON_MAJOR) + str(PYTHON_MINOR)
if int(PYTHON_MINOR) < 8:
    whl_python_version += "m"

disp_str = "Detected platform: \n\t " + str(OS_VERSION) + "\n\t Python " + str(PYTHON_MAJOR) + "." + str(PYTHON_MINOR)
disp_str += "\n\t ZED SDK " + str(ZED_SDK_MAJOR) + "." + str(ZED_SDK_MINOR)
print(disp_str)

whl_file = "pyzed-" + str(ZED_SDK_MAJOR) + "." + str(
    ZED_SDK_MINOR) + whl_python_version + "-" + whl_platform_str + "_" + str(ARCH_VERSION).lower() + ".whl"

whl_file_URL = base_URL + str(ZED_SDK_MAJOR) + "." + str(ZED_SDK_MINOR) + "/whl/" + OS_VERSION + "/" + whl_file
whl_file = os.path.join(dirname, whl_file)

#print(whl_file)
print("-> Checking if " + whl_file_URL + " exists and is available")
try:
    r = requests.get(whl_file_URL, allow_redirects=True)
    open(whl_file, 'wb').write(r.content)
except requests.exceptions.HTTPError as e:
    print("Error downloading whl file ({})".format(e))
except requests.exceptions.URLError as e:
    print("Invalid SSL certificate, trying to fix the issue by reinstalling 'certifi' package")
    err = pip_install("certifi", force_install=True, upgrade=True)
    if err == 0:
        # Retrying
        try:
            r = requests.get(whl_file_URL, allow_redirects=True)
            open(whl_file, 'wb').write(r.content)
        except Exception as e:
            print("Error downloading whl file ({})".format(e))


if check_valid_file(whl_file):
    # Internet is ok, file has been downloaded and is valid
    print("-> Found ! Downloading python package into " + whl_file)

    print("-> Installing necessary dependencies")
    err = 0
    if "aarch64" in ARCH_VERSION:
        # On jetson numpy is built from source and need other packages
        err_wheel = pip_install("wheel")
        err_cython = pip_install("cython")
        err = err_wheel + err_cython
    err_numpy = pip_install("numpy")

    if err != 0 or err_numpy != 0:
        print("ERROR : An error occurred, 'pip' failed to setup python dependencies packages (pyzed was NOT correctly setup)")
        sys.exit(1)

    err_pyzed = pip_install(whl_file, ignore_install=True)
    if err_pyzed == 0:
        print("Done")
    else:
        print("ERROR : An error occurred, 'pip' failed to setup pyzed package (pyzed was NOT correctly setup)")
        sys.exit(1)

    if sys.platform == "win32":
        print("Installing OpenGL dependencies required to run the samples")
        py_vers = int(int(PYTHON_MAJOR) * math.pow(10, len(PYTHON_MINOR)) + int(PYTHON_MINOR))
        install_win_dep("PyOpenGL", py_vers)
        install_win_dep("PyOpenGL_accelerate", py_vers)

        # Two files must be copied into pyzed folder : sl_zed64.dll and sl_ai64.dll
        pyzed_dir = get_pyzed_directory()
        source_dir = zed_path + "/bin"
        files = ["/sl_ai64.dll", "/sl_zed64.dll"]

        for file in files:
            if os.path.isfile(source_dir + file):
                shutil.copy(source_dir + file, pyzed_dir + file)
            else:
                print("ERROR : An error occurred, 'pip' failed to copy dll file " + source_dir + file + " (pyzed was NOT correctly setup)")
    else: # Only on linux, on windows this script should be used every time to avoid library search path issues
        print("  To install it later or on a different environment run : \n python -m pip install --ignore-installed " + whl_file)
    sys.exit(0)
else:
    print("\nUnsupported platforms, no pyzed file available for this configuration\n It can be manually installed from "
        "source https://github.com/stereolabs/zed-python-api")
    sys.exit(1)
