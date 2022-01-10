import os, os.path
import subprocess
import sys
import time
from pathlib import Path
from shutil import copyfile
import threading
from loguru import logger
from typing import List, Optional

"""
Usage:
mp3dirconv.py <input folder> <output folder>
"""

EXT_FROM = [".m4a", ".flac"]  # extensions to convert from
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
    if not os.path.exists(output_folder):
        os.mkdir(output_folder)
    logger.info(f"Copying file '{input_file}' to '{output_file}'")
    copyfile(input_file, output_file)
    time.sleep(5)


def convert_file(input_file: str, output_folder: str, output_file: str):
    if not os.path.exists(output_folder):
        os.mkdir(output_folder)
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


def convert_all_in_folder(folder_to_convert: Path, output_folder: Path):
    # resolve, convert to string
    output_folder = str(Path(output_folder).resolve())
    all_copy_tasks = []
    all_convert_tasks = []
    for root, dirs, files in os.walk(folder_to_convert):
        # add relative path of subfolder
        output_folder += str(Path(root)).replace(str(folder_to_convert), "")
        for file in files:
            file_path = Path(file)
            song_name = file_path.stem
            output_file = f"{output_folder}\\{song_name}{EXT}"
            input_file = str(Path(Path(root) / f"{song_name}{file_path.suffix}").resolve())
            if file_path.suffix in EXT_FROM and file_path.suffix != EXT:
                all_convert_tasks.append(threading.Thread(target=convert_file, args=(input_file, output_folder, output_file,)))
            elif file_path.suffix == EXT:
                output_file = str(Path(output_file).resolve())
                all_copy_tasks.append(threading.Thread(target=copy_file, args=(input_file, output_folder, output_file,)))
    threading.Thread(target=run_tasks, args=(all_copy_tasks,)).start()
    threading.Thread(target=run_tasks, args=(all_convert_tasks,)).start()


if __name__ == "__main__":
    enable_logging()
    arg_input_folder = Path(sys.argv[1]).resolve()
    arg_output_folder = Path(sys.argv[2]).resolve()
    convert_all_in_folder(arg_input_folder, arg_output_folder)
