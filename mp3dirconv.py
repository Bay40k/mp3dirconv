import os
import os.path
import shutil
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from queue import Empty as queueEmpty
from queue import Queue
from typing import List, Optional, Tuple

from loguru import logger

EXT_FROM = [".m4a", ".flac", ".wav"]  # extensions to convert from
EXT = ".mp3"  # extension to convert to
SAMPL_RATE = "44100"  # sample rate (kHz)
BIT_RATE = "200"  # birate (kbps)
MAX_THREADS = 16  # total max threads for any task
MAX_THREADS_PER_TASK = int(
    MAX_THREADS / 2
)  # maximum threads for convert and copy tasks

logger.remove()
default_log_format = "<g>{time:MM/DD/YYYY HH:mm:ss}</g> | <lvl>{level}</lvl> | <lvl><b>{message}</b></lvl>"


def enable_logging(
    log_level: str = "INFO", log_format: Optional[str] = default_log_format
):
    """
    Enables logging.

    :param log_level: Loguru log level.
    :param log_format: Set a Loguru log format other than default.
    :return: None
    """
    logger.add(sys.stderr, format=log_format, level=log_level, colorize=True)


def copy_file(input_file: str, output_file: str):
    if os.path.exists(output_file):
        return None
    logger.info(f"Copying file '{input_file}' to '{output_file}'")
    shutil.copyfile(input_file, output_file)


def convert_file(input_file: str, output_file: str):
    if not os.path.exists(output_file):
        logger.info(f"Converting file '{input_file}' to '{output_file}'")
        command = (
            f'ffmpeg -i "{input_file}" -vn -ar {SAMPL_RATE}'
            f' -ac 2 -b:a {BIT_RATE}k -n -f {EXT[1:]} "{output_file}"'
        )
        subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)


def worker(task_queue: Queue):
    while not task_queue.empty():
        try:
            task = task_queue.get_nowait()
            task.start()
            task.join()
        except queueEmpty:
            pass


def run_tasks(tasks: List[threading.Thread], max_threads: int = MAX_THREADS_PER_TASK):
    task_queue = Queue()
    for task in tasks:
        task_queue.put(task)

    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        executor.map(worker, [task_queue] * max_threads)


def check_to_copy_or_convert_file(
    file_path: Path, output_folder: Path
) -> Tuple[List[threading.Thread], List[threading.Thread]]:
    all_copy_tasks = []
    all_convert_tasks = []

    song_name = file_path.stem
    output_file = f"{output_folder}\\{song_name}{EXT}"
    input_file = file_path

    if file_path.suffix in EXT_FROM and file_path.suffix != EXT:
        all_convert_tasks.append(
            threading.Thread(
                target=convert_file,
                args=(
                    input_file,
                    output_file,
                ),
            )
        )
    elif file_path.suffix == EXT:
        input_file = str(input_file)
        output_file = str(Path(output_file).resolve())
        all_copy_tasks.append(
            threading.Thread(
                target=copy_file,
                args=(
                    input_file,
                    output_file,
                ),
            )
        )

    return all_copy_tasks, all_convert_tasks


def process_files(
    folder_to_convert: Path, output_folder: Path, paths_file: Path = None
) -> Tuple[List[threading.Thread], List[threading.Thread]]:
    all_copy_tasks = []
    all_convert_tasks = []

    dirs_to_make = []
    for root, dirs, files in os.walk(folder_to_convert):
        for dirname in dirs:
            dirpath = os.path.join(root, dirname)
            dirpath = str(Path(output_folder).resolve()) + dirpath.replace(
                str(folder_to_convert), ""
            )
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
            new_output_folder += str(file_path.parent).replace(
                str(folder_to_convert), ""
            )
            copy_tasks, convert_tasks = check_to_copy_or_convert_file(
                file_path, Path(new_output_folder)
            )
            all_copy_tasks += copy_tasks
            all_convert_tasks += convert_tasks
    else:
        for root, dirs, files in os.walk(folder_to_convert):
            for dirpath in dirs_to_make:
                if str(output_folder) in dirpath:
                    if not os.path.exists(dirpath):
                        os.makedirs(dirpath)
            new_output_folder = str(Path(output_folder).resolve()) + str(
                Path(root)
            ).replace(str(folder_to_convert), "")
            for file in files:
                file_path = Path(file)
                song_name = file_path.stem
                input_file = Path(
                    Path(root) / f"{song_name}{file_path.suffix}"
                ).resolve()
                copy_tasks, convert_tasks = check_to_copy_or_convert_file(
                    input_file, Path(new_output_folder)
                )
                all_copy_tasks += copy_tasks
                all_convert_tasks += convert_tasks

    return all_copy_tasks, all_convert_tasks


def convert_all_in_folder(
    folder_to_convert: Path, output_folder: Path, paths_file: Path = None
):
    """
    Usage:
    mp3dirconv.py [options] <input folder> <output folder>
    --file <input file> | Use list of paths from a file, and uses input folder as root reference for output subfolders
    """
    all_copy_tasks, all_convert_tasks = process_files(
        folder_to_convert, output_folder, paths_file
    )
    run_tasks(all_copy_tasks + all_convert_tasks, max_threads=MAX_THREADS)


if __name__ == "__main__":
    enable_logging()
    arg_paths_file = None
    try:
        if sys.argv[1] == "--file":
            arg_paths_file = Path(sys.argv[2]).resolve()
            arg_input_folder = Path(sys.argv[3]).resolve()
            arg_output_folder = Path(sys.argv[4]).resolve()
        else:
            arg_input_folder = Path(sys.argv[1]).resolve()
            arg_output_folder = Path(sys.argv[2]).resolve()
        convert_all_in_folder(arg_input_folder, arg_output_folder, arg_paths_file)
    except IndexError:
        print(convert_all_in_folder.__doc__)
