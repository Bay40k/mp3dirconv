import os, os.path
import subprocess
import sys
import time
from pathlib import Path
import shutil
import threading
from loguru import logger
from typing import List, Optional

"""
Usage:
mp3dirconv.py [options] <input folder> <output folder>
--file <input file> | Use list of paths from a file, and uses input folder as root reference for output subfolders
"""

EXT_FROM = [".m4a", ".flac", ".wav"]  # extensions to convert from
EXT = ".mp3"  # extension to convert to
SAMPL_RATE = "44100"  # sample rate (kHz)
BIT_RATE = "200"  # birate (kbps)

logger.remove()
default_log_format = "<g>{time:MM/DD/YYYY HH:mm:ss}</g> | <lvl>{level}</lvl> | <lvl><b>{message}</b></lvl>"


def enable_logging(log_level: str = "INFO", log_format: Optional[str] = default_log_format):
    """
    Enables logging.

    :param log_level: Loguru log level.
    :param log_format: Set a Loguru log format other than default.
    :return: None
    """
    logger.add(sys.stderr, format=log_format, level=log_level, colorize=True)


def copy_file(input_file: str, output_folder: str, output_file: str):
    if os.path.exists(output_file):
        return None
    logger.info(f"Copying file '{input_file}' to '{output_file}'")
    shutil.copyfile(input_file, output_file)


def convert_file(input_file: str, output_folder: str, output_file: str):
    # convert
    if not os.path.exists(output_file):
        logger.info(f"Converting file '{input_file}' to '{output_file}'\n")
        command = f'ffmpeg -i "{input_file}" -vn -ar {SAMPL_RATE}' \
                  f' -ac 2 -b:a {BIT_RATE}k -n -f {EXT[1:]} "{output_file}"'
        subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)


def run_tasks(tasks: List[threading.Thread], max_threads: int = 16):
    tasks_to_run = []
    running_threads = []
    amt_of_tasks = len(tasks)
    while amt_of_tasks > 0:
        for i in range(0, max_threads):
            try:
                tasks_to_run.append(tasks[i])
            except IndexError:
                continue
        for t in tasks_to_run:
            t.start()
            running_threads.append(t)
            tasks.pop(tasks.index(t))
        amt_of_tasks = len(tasks)
        # wait for tasks to complete
        for t in running_threads:
            t.join()
        tasks_to_run = []
        running_threads = []


def check_to_copy_or_convert_file(file_path: Path, output_folder: Path):
    all_copy_tasks = []
    all_convert_tasks = []
    song_name = file_path.stem
    output_file = f"{output_folder}\\{song_name}{EXT}"
    input_file = file_path
    if file_path.suffix in EXT_FROM and file_path.suffix != EXT:
        all_convert_tasks.append(threading.Thread(target=convert_file, args=(input_file, output_folder, output_file,)))
    elif file_path.suffix == EXT:
        input_file = str(input_file)
        output_file = str(Path(output_file).resolve())
        all_copy_tasks.append(threading.Thread(target=copy_file, args=(input_file, output_folder, output_file,)))
    return {
        "all_copy_tasks": all_copy_tasks,
        "all_convert_tasks": all_convert_tasks
    }


def convert_all_in_folder(folder_to_convert: Path, output_folder: Path, paths_file: Path = None):
    # resolve, convert to string
    all_copy_tasks = []
    all_convert_tasks = []

    dirs_to_make = []
    for root, dirs, files in os.walk(folder_to_convert):
        for dirname in dirs:
            dirpath = os.path.join(root, dirname)
            dirpath = str(Path(output_folder).resolve()) + dirpath.replace(str(folder_to_convert), "")
            dirs_to_make.append(dirpath)

    if paths_file:
        with open(paths_file.resolve(), "rb") as file:
            lines = file.readlines()
            lines = [line.rstrip() for line in lines]
        for line in lines:
            file_path = Path(line.decode("utf-8"))
            for dirpath in dirs_to_make:
                if str(file_path.parent.stem) in dirpath:
                    if not os.path.exists(dirpath):
                        os.makedirs(dirpath)
            new_output_folder = str(Path(output_folder).resolve())
            # get parent subfolder
            new_output_folder += str(file_path.parent).replace(str(folder_to_convert), "")
            check_copy_convert = check_to_copy_or_convert_file(file_path, new_output_folder)
            all_copy_tasks += check_copy_convert["all_copy_tasks"]
            all_convert_tasks += check_copy_convert["all_convert_tasks"]
    else:
        for root, dirs, files in os.walk(folder_to_convert):
            # copy directory structure
            for dirpath in dirs_to_make:
                if str(output_folder) in dirpath:
                    if not os.path.exists(dirpath):
                        os.makedirs(dirpath)
            # get input file subdirectory
            new_output_folder = str(Path(output_folder).resolve()) + str(Path(root)).replace(str(folder_to_convert), "")
            for file in files:
                file_path = Path(file)
                song_name = file_path.stem
                input_file = Path(Path(root) / f"{song_name}{file_path.suffix}").resolve()
                check_copy_convert = check_to_copy_or_convert_file(input_file, new_output_folder)
                all_copy_tasks += check_copy_convert["all_copy_tasks"]
                all_convert_tasks += check_copy_convert["all_convert_tasks"]

    threading.Thread(target=run_tasks, args=(all_copy_tasks,)).start()
    threading.Thread(target=run_tasks, args=(all_convert_tasks,)).start()


if __name__ == "__main__":
    enable_logging()
    arg_paths_file = None
    if sys.argv[1] == "--file":
        arg_paths_file = Path(sys.argv[2]).resolve()
        arg_input_folder = Path(sys.argv[3]).resolve()
        arg_output_folder = Path(sys.argv[4]).resolve()
    else:
        arg_input_folder = Path(sys.argv[1]).resolve()
        arg_output_folder = Path(sys.argv[2]).resolve()
    convert_all_in_folder(arg_input_folder, arg_output_folder, arg_paths_file)
