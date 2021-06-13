# __Author__: Khoi Van 2021

import argparse
import csv
import logging
import re
import shutil
import sys
from functools import partial
from itertools import groupby
from multiprocessing import Pool
from operator import itemgetter
from pathlib import Path, PurePath
from typing import Dict, List, Optional, Union

# from fuzzywuzzy import fuzz, process
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import BarColumn, Progress, SpinnerColumn, TimeElapsedColumn

console = Console()
sys.setrecursionlimit(20000)

# Set logger using Rich: https://rich.readthedocs.io/en/latest/logging.html
logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)
log = logging.getLogger("rich")


CURRENT_FILEPATH = Path(__file__).resolve().parent
DATA_FOLDER = CURRENT_FILEPATH / 'data'
DATA_FOLDER.mkdir(exist_ok=True)
INPUT_FILE = DATA_FOLDER / 'manualNames.csv'
DIRECTORY_FILE = DATA_FOLDER / 'manifest.csv'
INPUT_MANUAL_FOLDER = DATA_FOLDER / 'manuals'
OUTPUT_MANUAL_FOLDER = CURRENT_FILEPATH.parent / 'manuals'

LOG_FOLDER = CURRENT_FILEPATH / 'logs'
LOG_FOLDER.mkdir(exist_ok=True)
FOUND_MANUALS_RESULT_FILE = LOG_FOLDER / 'found_manuals.csv'
NOT_FOUND_MANUALS_RESULT_FILE = LOG_FOLDER / 'not_found_manuals.csv'


def init_argparse() -> argparse.ArgumentParser:
    """Creating CLI helper"""
    parser = argparse.ArgumentParser(
        usage="python %(prog)s [OPTIONS]",
        description="Generate Installation Manuals for North Country Fire items."
    )
    parser.add_argument('-d', '--debug',
                        help='Print more debug info.',
                        action="store_true")
    parser.add_argument('-p', '--parallel',
                        help='Generate Installation Manual files in asynchronous fashion (default).',
                        default=True,
                        action="store_true")
    parser.add_argument('-s', '--sequential',
                        help='Generate Installation Manual files sequentially.',
                        action="store_true")
    return parser


def import_item_list(file):
    with open(file, 'r', newline='') as csv_file:
        dict_reader = csv.DictReader(csv_file)
        return [line for line in dict_reader]


def extract_installation_manual(file):
    # Remove the not found result file and log file if exists
    FOUND_MANUALS_RESULT_FILE.unlink(missing_ok=True)
    NOT_FOUND_MANUALS_RESULT_FILE.unlink(missing_ok=True)

    items_needed_manuals = import_item_list(file)

    directory = load_directory_file()
    # breakpoint()

    # Synchronouse fashion, easy for debug
    if parsing_mode == 'sequential':
        for item in items_needed_manuals:
            try:
                find_installation_manual(item, directory=directory)
            except Exception as error:
                log.error(f'{item=}')
                log.exception(error)

    else:
        # Ref: https://github.com/willmcgugan/rich/issues/121
        progress = Progress(SpinnerColumn(),
                            "[bold green]{task.description}",
                            BarColumn(),
                            "[progress.percentage]{task.percentage:>3.1f}%",
                            "({task.completed} of {task.total})"
                            "•",
                            TimeElapsedColumn(),
                            # transient=True,
                            console=console)

        with progress:
            task_description = f'Generating Installation Manuals ...'
            task_id = progress.add_task(task_description,
                                        total=len(items_needed_manuals),
                                        start=True)

            try:
                pool_size = 25
                with Pool(processes=pool_size) as p:
                    results = p.imap(partial(find_installation_manual,
                                             directory=directory
                                             ),
                                     items_needed_manuals,
                                     chunksize=8)
                    for result in results:
                        progress.advance(task_id)

            except Exception as error:
                # if debug:
                # traceback_str = ''.join(traceback.format_exception(etype=type(error), value=error, tb=error.__traceback__))
                # log.error(traceback_str)
                log.exception(error)
                # log.error(error)


def find_installation_manual(item: Dict[str, str],
                             directory: List[Dict[str, str]]) -> None:
    manual_path = find_match(item, directory)
    if manual_path == 'ignore':
        # Write ignored item to log
        item.update({'comment': 'Ignored.'})
        write_items_to_csv(file=NOT_FOUND_MANUALS_RESULT_FILE, lines=[item])
    elif manual_path:
        copy_manual(item=item,
                    manual_path=manual_path,
                    out_dir=OUTPUT_MANUAL_FOLDER)
        # Write the match image file to log
        item.update({'matched_manual': Path(manual_path).relative_to(INPUT_MANUAL_FOLDER)})
        write_items_to_csv(file=FOUND_MANUALS_RESULT_FILE, lines=[item])
    else:
        # Write not found item to log
        item.update({'comment': 'Not found any matched installation manual.'})
        write_items_to_csv(file=NOT_FOUND_MANUALS_RESULT_FILE, lines=[item])


def find_match(item: Dict[str, str],
               directory: List[Dict[str, str]]
               ) -> Optional[Union[str, PurePath]]:
    sku_to_ignore = ['SDLOGS-ODCOUG', 'HDLOGS-ODCOUG',
                     'LOGS-DRTWOOD-48', 'LOGS-DRTWOOD-60', 'LOGS-DRTWOOD-72',
                     'DRTWOOD-JADE',
                     'STFSO18',
                     ]
    if (item.get('manufacturerSKU') in sku_to_ignore
        or item.get('c__productCategory', '').lower() == 'Media Kits'.lower()):
        return 'ignore'

    brand = item['brand']
    if not brand or not directory.get(brand):
        # Write not found item to log
        item.update({'comment': 'Empty brand of does not have manuals for this brand.'})
        write_items_to_csv(file=NOT_FOUND_MANUALS_RESULT_FILE, lines=[item])
        return None

    matched_manuals = find_fuzzy(item=item,
                                 brand_directory=directory[brand])
    if matched_manuals and len(matched_manuals) > 1:
        # Sort according to 'manual_type', i.e. 'installation' better than 'owner'
        matched_manuals = sorted(matched_manuals, key=itemgetter('manual_type'))
        # breakpoint()
        # If the SKU in the matched list are different, rank them and sort from closest to the item SKU in word order
        matched_manuals = rank_closest_sku(anchor=item,
                                           list_to_be_ranked=matched_manuals)
    if matched_manuals:
        return INPUT_MANUAL_FOLDER / matched_manuals[0]['pdf_location']


def rank_closest_sku(anchor: Dict[str, str],
                     list_to_be_ranked: List[Dict[str, str]]
                     ) -> List[Dict[str, str]]:
    """If the SKU in the matched list are different,
    rank them and sort from closest to the item SKU in word order

    e.g, item SKU 'DRT3045TEN', matched_manuals contains 'DRT6345TEN' and 'DRT3045DEN'; 'DRT3045DEN' should be a better match

    Parameters
    ----------
    anchor : Dict[str, str]
        [description]
    list_to_be_ranked : List[Dict[str, str]]
        [description]

    Returns
    -------
    List[Dict[str, str]]
        [description]
    """
    scores = set()
    sku = anchor['manufacturerSKU']
    for item in list_to_be_ranked:
        score = 0
        for i, c in enumerate(item['sku']):
            if i < len(sku) and c == sku[i]:
                score += 1
            else:
                break
        item['score'] = score
        scores.add(score)

    if len(scores) == 1:
        # If the same score, return in alphabetical order of 'sku',
        # e.g. 'DRT4245TEN-B' before 'DRT4245TEN-C'
        return sorted(list_to_be_ranked, key=itemgetter('sku'))

    return sorted(list_to_be_ranked, key=itemgetter('score'), reverse=True)


def find_fuzzy(item, brand_directory):
    # Handle issue with input missing both 'manufacturerSKU AND 'c__series'
    if not item['manufacturerSKU'] and not item['c__series']:
        return []

    manufacturer_sku_choices = {index: line['sku']
                                for index, line in enumerate(brand_directory)
                                if line['sku']}
    # console.log(f'{item["manufacturerSKU"]=}')

    options = []
    if manufacturer_sku_choices:
        # Return as a tuple of 3 (because the choices was added as dict):
        # (the match value of the dict (which was compared to the string), the score, and the key of the value)
        # options = process.extract(item['manufacturerSKU'], manufacturer_sku_choices, limit=5, scorer=fuzz.token_sort_ratio)
        options = process.extract(item['manufacturerSKU'], manufacturer_sku_choices, limit=5, scorer=fuzz.ratio)
    else:
        # search using series here
        series_choices = {index: line['series']
                          for index, line in enumerate(brand_directory)
                          if line['series']}
        # options = process.extract(item['c__series'], series_choices, limit=5, scorer=fuzz.token_sort_ratio)
        options = process.extract(item['c__series'], series_choices, limit=5, scorer=fuzz.ratio)

    top_score = options[0][1] if options else 0
    # breakpoint()
    if top_score < 65:
        return None
    top_score_results = [option for option in options if option[1] >= top_score]
    return [brand_directory[index] for _, _, index in top_score_results]


def find_matches_startwith(item, directory
                           ) -> Optional[List[Dict[str, str]]]:
    base_sku = re.search(r'^([a-z]{3}\d{2})', item, flags=re.IGNORECASE)
    if base_sku:
        # !Special cases
        if item.lower() == 'vre4536':
            return [line for line in directory
                    if line['series'].lower().startswith('vre4500')]

        return [line for line in directory
                if line['series'].lower().startswith(base_sku[1].lower())]


def load_directory_file() -> Dict[str, List[Dict[str, str]]]:
    with open(DIRECTORY_FILE, 'r') as f:
        dict_reader = csv.DictReader(f)
        sorted_directory = sorted(iter(dict_reader), key=itemgetter('brand'))
        return {brand: list(info)
                for brand, info in groupby(sorted_directory,
                                           key=itemgetter('brand'))}


def copy_manual(item: Dict,
                manual_path: Union[str, PurePath],
                out_dir: Union[str, PurePath]) -> None:
    # Some sku contain forward slash, not good for filename, e.g 'VDY24/18NMP', 'RAK35/40'
    # or space, e.g. "BZLB-BLNI RAP54", "BZLB-BLNI RAP42", 'MHS HEAT-ZONE-TOP'
    desired_manual_name = item['installationManualFileName(.pdf)'].replace('/', '_').replace(' ', '-')
    manual_file = Path(manual_path)
    destination = Path(out_dir) / item['brand'] / f'{desired_manual_name}{manual_file.suffix}'
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(Path(manual_path), Path(destination))
    except Exception as error:
        print()
        log.error(error)


def write_items_to_csv(file, lines):
    '''Write item without found images into csv file'''
    file_exists = Path(file).exists()
    with open(Path(file), 'a') as csvfile:
        headers = list(lines[0].keys())
        writer = csv.DictWriter(csvfile, delimiter=',',
                                lineterminator='\n',
                                fieldnames=headers)

        if not file_exists:
            writer.writeheader()  # file doesn't exist yet, write a header

        writer.writerows(lines)


if __name__ == '__main__':
    parser = init_argparse()
    debug = parser.parse_args().debug
    parallel = parser.parse_args().parallel
    sequential = parser.parse_args().sequential
    parsing_mode = 'sequential' if sequential else 'parallel'

    extract_installation_manual(file=INPUT_FILE)
