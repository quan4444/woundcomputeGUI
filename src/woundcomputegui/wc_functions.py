import os
import fnmatch
import shutil
import yaml
import re
from humanfriendly import format_timespan
from woundcompute import image_analysis as ia
from pathlib import Path
import re
import psutil
import time
from concurrent.futures import ThreadPoolExecutor,ProcessPoolExecutor,wait,FIRST_COMPLETED,ALL_COMPLETED
from functools import partial
import traceback
import sys


def create_wc_yaml(path_in: str, image_type_in: str, is_fl_in: bool, is_pillars_in: bool):
    """Given the output path as string. Will create a yaml file in the main output folder. This yaml file will be
    copied into each subfolder during the sorting function"""

    # Default keys and values stored in yaml file
    yaml_input_file = {
        'version': 1.0,
        'segment_brightfield': False,
        'seg_bf_version': 1,
        'seg_bf_visualize': False,
        'segment_fluorescent': False,
        'seg_fl_version': 1,
        'seg_fl_visualize': False,
        'segment_ph1': True,  # True,
        'seg_ph1_version': 2,
        'seg_ph1_visualize': True,
        'track_brightfield': False,
        'track_bf_version': 1,
        'track_bf_visualize': False,
        'track_ph1': False,
        'track_ph1_version': 1,
        'track_ph1_visualize': False,
        'bf_seg_with_fl_seg_visualize': False,
        'bf_track_with_fl_seg_visualize': False,
        'ph1_seg_with_fl_seg_visualize': False,
        'ph1_track_with_fl_seg_visualize': False,
        'zoom_type': 2,
        'track_pillars_ph1': False
    }

    # Conditionally modify yaml file based on image_type input

    for key, value in yaml_input_file.items():
        if image_type_in in key and not "version" in key and not "fl" in key and not "track" in key:
            yaml_input_file[key] = True

            if is_fl_in:
                if "fl" in key and not "version" in key:
                    yaml_input_file[key] = True

        if "pillars" in key and not "version" in key and is_pillars_in:
            yaml_input_file[key] = True

    # Write yaml output to path_output
    with open(os.path.join(path_in, 'wc_dataset_' + image_type_in + '.yaml'), 'w') as file:
        yaml.safe_dump(yaml_input_file, file, sort_keys=False)


def copy_file(src, dest):
    try:
        shutil.copy2(src, dest)
    except OSError as e:
        # If it fails, inform the user.
        print('Error: %s - %s.' % (e.filename, e.strerror))


def write_to_sp_yaml(path_input_fn: str, input_list_fn, name_fn: str):
    """Given the path to the input folder and a list. Will write the list to a yaml file in the input folder"""

    with open(os.path.join(path_input_fn,name_fn + '.yaml'), 'w') as file:
        yaml.safe_dump(input_list_fn, file, sort_keys=False)


def define_basename_list(path_input_fn: str, path_output_fn: str, ms_choice: str) -> (list, bool):
    """Given an input path as a string. Will return a list of experiment names in the input folder"""

    is_nd_out = False
    basename_list_fn = []

    if ms_choice == "Cytation":
        basename_list_fn = [name for name in os.listdir(path_input_fn) if
                            os.path.isdir(os.path.join(path_input_fn, name))]
        basename_list_fn = [name for name in basename_list_fn if
                            not os.path.join(path_input_fn, name) == path_output_fn]
        basename_list_fn = [name for name in basename_list_fn if not os.path.join(path_input_fn, name) == os.path.join(path_input_fn, 'Sorted')]

    else:
        for file in os.listdir(path_input_fn):
            if file.endswith('.nd'):
                name, ext = os.path.splitext(file)
                basename_list_fn.append(name)
                is_nd_out = True

        if not is_nd_out:
            file_list = os.listdir(path_input_fn)
            basename = [file.split('_') for file in file_list if file.endswith('.tif') or file.endswith('.TIF')]
            basename = list(dict.fromkeys(["_".join([str(item1) for item1 in item[0:-2]]) for item in basename]))
            basename_list_fn = [b for b in basename if 'thumb' not in b]

    write_to_sp_yaml(path_output_fn, basename_list_fn, 'basename_list')

    return basename_list_fn, is_nd_out


def efficient_file_copy(path_output_fn, files_to_copy):
    # Use ThreadPoolExecutor for parallel copying
    with ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(copy_file, file.path, os.path.join(path_output_fn, file.name)) for file in files_to_copy
        ]

        # Wait for all copying tasks to complete
        for future in futures:
            future.result()


def sort_basename_folders(basename_list_fn: list, path_input_fn: str, path_output_fn: str, ms_choice: str):
    """Given a list of experiments obtained from the .nd files in the input folder. Given input and out paths as str.
 Creates an output folder at path_output. Copies and sorts TIFF files in path_input according to basenames in output
 folder"""

    for basename_fn in basename_list_fn:
        destination_folder = os.path.join(path_output_fn, basename_fn)
        # create folders for each expt
        try:
            os.makedirs(destination_folder, exist_ok=True)
        except OSError as e:
            # If it fails, inform the user.
            print('Error: %s - %s.' % (e.filename, e.strerror))

        # copy files into respective basename folders


        if ms_choice == "Cytation":
            path_temp = os.path.join(path_input_fn, basename_fn)

            # Get all .tif files
            tif_files = [file for file in os.scandir(path_temp) if file.name.lower().endswith('.tif')]

            # for file in os.listdir(path_temp):
            #     if file.endswith('.tif' or '.TIF'):
            #         copy_file(os.path.join(path_temp, file), os.path.join(path_output_fn, basename_fn, file))

        else:
            # copy .nd file into respective basename folder
            if os.path.isfile(os.path.join(path_input_fn, basename_fn + '.nd')):
                copy_file(os.path.join(path_input_fn, basename_fn + '.nd'),
                          os.path.join(destination_folder, basename_fn + '.nd'))

            # copy TIF files to respective basename folders, excludes thumbnail files

            # Prepare the file list
            tif_files = [ file for file in os.scandir(path_input_fn)
                    if file.name.startswith(basename_fn + '_') and not fnmatch.fnmatch(file.name, '*thumb*')
                ]

        # Copy all .tif files to the destination folder
        efficient_file_copy(destination_folder, tif_files)


def extract_nd_info(basename_list_fn: list, path_output_fn: str, is_nd: bool, ms_choice: str) -> dict:
    """Given a basename list and an output path. Will extract number of stage positions for each list and create
    position map lists for each basename"""
    #Stage position and timepoint information is extracted from the .nd file or from the files in the folder - can be returned from this function if needed

    stage_positions = []
    timepoints_list = []
    stage_pos_maps = {}
    stage_pos_submap = {}
    if is_nd:
        for index_fn, basename_fn in enumerate(basename_list_fn):
            with open(os.path.join(path_output_fn, basename_fn, basename_fn + '.nd'), 'r') as nd_file:
                print("\tOpened .nd")
                for l_no, line in enumerate(nd_file):
                    if '"NStagePositions"' in line:
                        spos_int = [int(s) for s in line.split() if s.isdigit()][-1]
                        stage_positions.append(spos_int)
                        stage_pos_submap = {}
                        for l_no1, line1 in enumerate(nd_file):
                            for N in range(1, spos_int+1):
                                if '"Stage' + str(N) + '"' in line1:
                                    sp_well = line1.split('"')[-2]
                                    stage_pos_submap[N] = sp_well
                        break
            stage_pos_maps[basename_fn] = stage_pos_submap
            print("\tExtracted information from .nd file")
    else:
        for index_fn,basename_fn in enumerate(basename_list_fn):
            file_list = os.listdir(os.path.join(path_output_fn,basename_fn))

            positions = []
            for file in file_list:
                spos = file
                stage_pattern_s = r's(\d+)'
                stage_pattern_letter = r'([A-H])(\d+)'

                stage_wellpos_match = re.search(stage_pattern_letter, file)
                stage_match_s = re.search(stage_pattern_s,file)

                if stage_wellpos_match:
                    spos = stage_wellpos_match.group(0)
                elif stage_match_s:
                    spos = stage_match_s.group(0)
                positions.append(spos)
            positions = list(dict.fromkeys(positions))
            print('\tPositions:',positions)
            stage_positions.append(len(positions))

            positions = [pos[:1] + pos[1:].zfill(2) for pos in positions]
            positions.sort()
            stage_pos_submaps = {N: position for N,position in zip(range(1,len(positions)+1), positions)}
            stage_pos_maps[basename_fn]=stage_pos_submaps
            print('\tExtracted information from files in folder')

#     write_to_sp_yaml(path_output_fn, stage_pos_maps, 'stage_positions')

    return stage_pos_maps


def move_rename_files(file, basename_fn: str, parent_output_fn: str,
                      stage_pos_maps_fn: dict, image_type_fn: str, ms_choice: str, is_nd: bool):
    #print(f'Processing file: {file}')
    if not file.lower().endswith('.tif'):
        return f"Skipped non-TIF file: {file}"

    timepoint_pattern = r't(\d+)'
    stage_pattern_s = r's(\d+)'
    stage_pattern_letter = r'([A-H])(\d+)'

    new_filename = file
    timepoint_match = re.search(timepoint_pattern, file)
    stage_wellpos_match = re.search(stage_pattern_letter, file)
    stage_match_s = re.search(stage_pattern_s, file)

    if timepoint_match:
        timepoint_num = int(timepoint_match.group(1))
        new_timepoint = f't{timepoint_num:03d}'
        new_filename = new_filename.replace(timepoint_match.group(0), new_timepoint)

    if stage_wellpos_match:
        spos = stage_wellpos_match.group(0)
    elif stage_match_s:
        stage_num = int(stage_match_s.group(1))
        spos = f's{stage_num:03d}'
        if is_nd:
            spos += '_' + str(stage_pos_maps_fn[basename_fn][stage_num])
        new_filename = new_filename.replace(stage_match_s.group(0), spos)

    path_input_fn = os.path.join(parent_output_fn, basename_fn)
    path_pos_output_fn = os.path.join(parent_output_fn, basename_fn, spos)
    target_dir = os.path.join(path_pos_output_fn, f'{image_type_fn}_images')

    #print(f'Creating directory: {target_dir}')
    os.makedirs(target_dir, exist_ok=True)

    yaml_src = os.path.join(parent_output_fn, f'wc_dataset_{image_type_fn}.yaml')
    yaml_dst = os.path.join(path_pos_output_fn, f'wc_dataset_{image_type_fn}.yaml')
    if not os.path.exists(yaml_dst):
        #print(f'Copying YAML file to: {yaml_dst}')
        shutil.copy2(yaml_src, yaml_dst)

    source_path = os.path.join(path_input_fn, file)
    target_path = os.path.join(target_dir, new_filename)
    #print(f'Moving file from {source_path} to {target_path}')
    try:
        shutil.move(source_path, target_path)
        #return f"Successfully moved: {file} to {target_path}"
    except OSError as e:
        error_msg = f'Error: {e.filename} - {e.strerror}'
        print(error_msg)


def efficient_sort_stage_pos(basename_list_fn: list, parent_output_fn: str,
                             stage_pos_maps_fn: dict, image_type_fn: str, ms_choice: str, is_nd: bool):
    """Given basename list, parent output folder and number of stage positions list extracted from nd files. Sorts
    files into stage position folders"""
    print('\tEntered efficient_sort_stage_pos')
    with ThreadPoolExecutor() as executor:
        for basename_fn in basename_list_fn:
            print(f'\tProcessing basename: {basename_fn}')
            file_list = [entry.name for entry in os.scandir(os.path.join(parent_output_fn, basename_fn))
                         if entry.is_file() and entry.name.lower().endswith('.tif')]
            print(f'\tFound {len(file_list)} TIF files for {basename_fn}')

            # Use list() to force execution of all tasks
            results = list(
                executor.map(partial(move_rename_files, basename_fn=basename_fn, parent_output_fn=parent_output_fn,
                                     stage_pos_maps_fn=stage_pos_maps_fn, image_type_fn=image_type_fn,
                                     ms_choice=ms_choice, is_nd=is_nd), file_list))


def wc_run(input_path_fn: str):
    # ** Section 3: Execute woundcompute for all basename folders in the Sorted folder ** #
    time_all = []
    current = time.time()
    try:
        time_all, action_all = ia.run_all(Path(input_path_fn))
        secondsPassed = time.time() - current
        print("\tProcessing: ", input_path_fn, "  Tissue: ", os.path.basename(os.path.normpath(input_path_fn)), "     time: ",
                format_timespan(secondsPassed))
    except Exception as ex:
        time_all.append(time.time())
        print("\tPath: ", input_path_fn, "    Tissue: ", os.path.basename(os.path.normpath(input_path_fn)), "     time: ",
                  time.ctime())
        print("---------ERROR OF SOME DESCRIPTION HAS HAPPENED-------")
        # print(ex)
        print("An error occurred:", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        print("------------------------------------------------------")


# Parallel Processing handlers
def get_cpu_usage():
    return psutil.cpu_percent(interval=5, percpu=False)


def wc_process_folder(main_folder:str, cpu_threshold:int):
    if not os.path.exists(main_folder):
        print(f"Folder {main_folder} does not exist. Skipping...")
        return
    subfolders = [f for f in os.scandir(main_folder) if f.is_dir()]

    with ProcessPoolExecutor() as executor:
        futures = set()
        subfolder_queue = subfolders.copy()

        # Start processing the first subfolder
        if subfolder_queue:
            initial_subfolder = subfolder_queue.pop(0)
            initial_future = executor.submit(wc_run, initial_subfolder.path)
            futures.add(initial_future)
            print(f'\tStarted process for {initial_subfolder.name}...')

            # Wait for 10 seconds to measure CPU usage
            time.sleep(10)
            cpu_usage = get_cpu_usage()
            print(f'\tCPU usage after 10 seconds: {cpu_usage}%')

            # Calculate the max number of processes based on the CPU usage threshold
            available_cpu = cpu_threshold - cpu_usage
            if available_cpu > 0:
                single_process_cpu = cpu_usage  # Assume single process usage equals measured CPU usage
                max_processes = max(1, int(available_cpu / single_process_cpu) + 1)  # +1 to include the initial process
                print(f'\tMaximum number of processes that can run: {max_processes}')

                # Submit remaining subfolders based on calculated max processes
                while subfolder_queue and len(futures) < max_processes:
                    next_subfolder = subfolder_queue.pop(0)
                    future = executor.submit(wc_run, next_subfolder.path)
                    futures.add(future)
                    print(f'\tAdded process for {next_subfolder.name}.')

        # Process remaining subfolders as tasks complete
        while futures or subfolder_queue:
            done, futures = wait(futures, timeout=5, return_when=FIRST_COMPLETED)
            for future in done:
                try:
                    future.result()  # Check for exceptions
                except Exception as e:
                    print(f'\tError processing subfolder: {e}')

            # Add new tasks if there are subfolders remaining and we're below max_processes
            while subfolder_queue and len(futures) < max_processes:
                next_subfolder = subfolder_queue.pop(0)
                future = executor.submit(wc_run, next_subfolder.path)
                futures.add(future)
                print(f'\tAdded future for {next_subfolder.name}.')

            # Wait for all remaining futures to complete
            wait(futures, return_when=ALL_COMPLETED)
    print('\tAll subfolders processed.')