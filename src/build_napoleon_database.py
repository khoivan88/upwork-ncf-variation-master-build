# __Author__: Khoi Van 2021

import argparse
import json
import logging
import re
from itertools import zip_longest
from pathlib import Path, PurePath
from typing import Dict, List, Set, Union
# from copy import deepcopy

import pandas as pd
from openpyxl import load_workbook
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, BarColumn, SpinnerColumn, TimeElapsedColumn

from extract_napoleon_data_from_catalog import extract_napoleon_data_from_catalog


console = Console()
# sys.setrecursionlimit(20000)

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
# DATA_FOLDER.mkdir(exist_ok=True)
ORIGINAL_DATA_FOLDER = DATA_FOLDER / 'original'
BUILD_DATA_FOLDER = DATA_FOLDER / '_build'
BUILD_DATA_FOLDER.mkdir(exist_ok=True)

PRICEBOOK_FILE = ORIGINAL_DATA_FOLDER / 'Napoleon 2021-sanitized.xlsx'
NAPOLEON_CRUDE_DATA_FILE = BUILD_DATA_FOLDER / 'napoleon-crude-data.json'
NAPOLEON_DATABASE_FILE = BUILD_DATA_FOLDER / 'napoleon-database.json'
# NCF_FILE = DATA_FOLDER / 'ncfNapoleonCatalogTemplate.xlsx'
# NCF_CSV_FILE = DATA_FOLDER / 'ncfNapoleonCatalogTemplate.csv'
OPTIONAL_LOOKUP = {'mandatory': 'Required',
                   'optional': 'Optional'}
ADDITIONAL_OPTIONAL_LOOKUP = {'INC': 'Included',
                              'OPT': 'Optional',
                              'N/A': 'Not Available'}


def init_argparse() -> argparse.ArgumentParser:
    """Creating CLI helper"""
    parser = argparse.ArgumentParser(
        usage="python %(prog)s [OPTIONS]",
        description="Validate North Country Fire data for Napoleon dataset."
    )
    parser.add_argument('-d', '--debug',
                        help='Print more debug info.',
                        action="store_true")
    parser.add_argument('-r', '--reload-database',
                        help='Force reloading of database from pricebook.',
                        action="store_true")
    return parser


def build_db(database: Dict):
    # Remove 'content' key, value pair from each series in 'series'
    db = remove_content_sections(database)
    db = sanitize_series_names(db)
    db = add_base_skus(db)
    db = add_fuel_type(db)    # ! Add before 'ignition_type'
    db = add_gas_fuel_type(db)
    db = add_ignition_type(db)
    db = add_series_number(db)
    db = add_series_name(db)
    db = add_vent_type(db)
    db = add_style(db)
    db = add_product_category(db)
    db = add_productTypeNonoperative(db)    # ! add after 'product_type'
    db = add_display_name(db)

    # Save database
    save_db(database=db, file=NAPOLEON_DATABASE_FILE)


def remove_content_sections(database: Dict) -> Dict:
    new_series_section = {series: {key: value
                                   for key, value in info.items()
                                   if key != 'content'}
                          for series, info in database['series'].items()
                          }
    # new_series_section = {}
    # for series, info in database['series'].items():
    #     for key, value in info.items():
    #         if key != 'content':
    #             breakpoint()
    #             new_series_section[series].update({key: value})
    database['series'] = new_series_section
    return database


def sanitize_series_names(database: Dict) -> Dict:
    for info in database['series'].values():
        new_title = re.sub(r'''
                           (
                            SERIES\sFIREPLACE\sMODELS
                            |FIREPLACE\sMODELS
                            |\bFIREPLACE\b
                            |\bMODELS\b
                            |\bWOOD\b
                            |\bGAS\b
                            |(?<!S)\sSERIES
                            |Clean\sFace\sOutdoor
                            |Electric
                            ).*
                           ''',
                           '',
                           info['title'],
                           flags=re.IGNORECASE | re.UNICODE | re.VERBOSE).encode("ascii", "ignore").decode().strip()
        new_title = re.sub(r'\s{2,}', ' ', new_title).title()
        info['title'] = new_title
    return database


def add_fuel_type(database: Dict) -> Dict:
    for series_info in database['series'].values():
        for product_line in series_info['units']:
            product_line_name = product_line['name']
            for unit in product_line['details']:
                if unit:
                    if re.search(r'wood', product_line_name, flags=re.IGNORECASE):
                        unit['fuel_type'] = 'Wood'
                    elif re.search(r'propane|gas', product_line_name, flags=re.IGNORECASE):
                        unit['fuel_type'] = 'Gas'
                    elif re.search(r'pellet', product_line_name, flags=re.IGNORECASE):
                        unit['fuel_type'] = 'Pellet'
                    else:    # Some time a product name does not specify, such as 'GSS42CFN'
                        unit['fuel_type'] = 'Gas'
    return database


def add_gas_fuel_type(database: Dict) -> Dict:
    for series_info in database['series'].values():
        for product_line in series_info['units']:
            product_line_name = product_line['name']
            for unit in product_line['details']:
                if unit and unit['fuel_type'] == 'Gas':
                    gas_fuel_type = 'Natural Gas'    # default
                    re_gas_fuel_type = re.compile(r'propane|natural gas', re.IGNORECASE)
                    gas_fuel_type_result = re_gas_fuel_type.search(product_line_name)
                    if gas_fuel_type_result:
                        gas_fuel_type = f'{gas_fuel_type_result[0].title()}'
                    unit['gas_fuel_type'] = gas_fuel_type
    return database


def add_ignition_type(database: Dict) -> Dict:
    for series_info in database['series'].values():
        for product_line in series_info['units']:
            product_line_name = product_line['name']
            for unit in product_line['details']:
                if unit:
                    if debug:
                        log.info(f"{unit['manufacturerSku']=}")
                    # if unit['fuel_type'] == 'Wood':
                    #     unit['ignition_type'] = ''
                    if unit['fuel_type'] == 'Gas':
                        ignition_type = 'Electronic Ignition'    # default
                        re_ignition_type = re.compile(r'electronic|millivolt', re.IGNORECASE)
                        ignition_type_result = re_ignition_type.search(product_line_name)
                        if ignition_type_result:
                            ignition_type = f'{ignition_type_result[0].title()} Ignition'
                        unit['ignition_type'] = ignition_type.title()
    return database


def add_base_skus(database: Dict) -> Dict:
    for series_info in database['series'].values():
        base_skus = series_info['baseSku']
        number_of_base_skus = len(base_skus)
        for product_line in series_info['units']:
            units = product_line['details']
            for i, unit in enumerate(units):
                if unit :
                    # Most of the series have 'baseSku'
                    if number_of_base_skus > 0 and i < number_of_base_skus:
                        unit['base_sku'] = base_skus[i]

                    # For some rare case without 'baseSku', e.g. pricebook lines 1200, 1818-1819, 1841-1842
                    else:
                        if debug:
                            log.info(f"Item '{unit['manufacturerSku']}' in a series without baseSku")
                        # See here for info on the regex: https://regex101.com/r/E9id2S/1/
                        unit['base_sku'] = re.search(r'^[A-Z]*\d*', unit['manufacturerSku'])[0]

    return database


def add_series_number(database: Dict) -> Dict:
    # Exception mapping of 'base_sku' and their corresponding 'series_number'
    SERIES_NUMBER_EXCEPTION = {
        'BHD4-Glass': 'BHD4',
        'BHD4-Cradle': 'BHD4ST',
        'BHD4-Logs': 'BHD4',
        'GDI3': 'GDI3',
        'GDI3N': 'GDI3',
        'GDI3NE': 'GDI3',
        'GDIG3': 'GDIG3',
        'GDIG3N': 'GDIG3',
        'GDIX3': 'GDIX3',
        'GDIX3N': 'GDIX3',
        'GDIX4N': 'GDIX4',
        'GDIX4': 'GDIX4',
        'GDIZC': 'ZC',
        'GSST8': 'GSST8N',
        'GT8': 'GT8NSB',
        'GVFT8': 'GVFT8N',
        'EPI3': 'EPI3',
    }
    for series_info in database['series'].values():
        for product_line in series_info['units']:
            for unit in product_line['details']:
                if unit.get('base_sku'):
                    if debug:
                        log.info(f"{unit['base_sku']=}")
                    if unit['base_sku'] in SERIES_NUMBER_EXCEPTION:
                        unit['series_number'] = SERIES_NUMBER_EXCEPTION[unit['base_sku']]
                    else:
                        unit['series_number'] = re.search(r'\d{2,}', unit['base_sku'])[0]
    return database


def add_series_name(database: Dict) -> Dict:
    for series_info in database['series'].values():
        series_name = series_info['title']
        for product_line in series_info['units']:
            for unit in product_line['details']:
                if unit:
                    # Cleaning up series name because the series number are duplicated sometimes!
                    sanitized_series_name = series_name.rstrip(unit.get("series_number")).strip()
                    unit['series_name'] = sanitized_series_name
    return database


def add_vent_type(database: Dict) -> Dict:
    for series_info in database['series'].values():
        for product_line in series_info['units']:
            product_line_name = product_line['name']
            for unit in product_line['details']:
                if unit and unit["fuel_type"] == "Gas":
                    vent_type = re.search(r'vent free|direct vent', product_line_name, flags=re.IGNORECASE)
                    if vent_type:
                        unit['vent_type'] = vent_type[0].title().replace(' ', '-')
                    else:
                        unit['vent_type'] = 'Vented'
    return database


def add_style(database: Dict) -> Dict:
    # Exception mapping of 'base_sku' and their corresponding 'series_number'
    STYLE_MAPPING = {
        'see through': 'See-Thru',
        'vertical': 'Vertical',
        '3 sided': 'Peninsula',
        # 'single side': 'Linear',
        'linear': 'Linear',
        # None: 'Traditional',
    }

    for series_info in database['series'].values():
        for product_line in series_info['units']:
            product_line_name = product_line['name']
            for unit in product_line['details']:
                if unit:
                    series_and_product_line_name = f"{unit['series_name']} {product_line_name}"
                    style = re.search('|'.join(re.escape(term) for term in STYLE_MAPPING),
                                      series_and_product_line_name,
                                      flags=re.IGNORECASE)
                    if style:
                        unit['style'] = STYLE_MAPPING[style[0].lower()]
                    elif 'L' in unit.get('base_sku', ''):
                        unit['style'] = 'Linear'
                    else:
                        unit['style'] = 'Traditional'
    return database


def add_product_category(database: Dict) -> Dict:
    VARIATION_PRODUCT_CATEGORY_MAPPING = {'log set': 'Media Kits',
                                          'panel': 'Interior Panels',
                                          'illusion glass': 'Interior Panels',
                                          'trim': 'Trim Kits',
                                          'element': 'Front Accents',    # ! this before 'front', because some items with 'element' also have 'front', such as 'Arched Iron Elements - Antique Pewter (Fits on Whitney front)'
                                          'front': 'Decorative Fronts',
                                          'conversion': 'Conversion Kits',
                                          }
    for series_info in database['series'].values():
        # For series's units
        for product_line in series_info['units']:
            product_line_name = product_line['name']
            for unit in product_line['details']:
                if unit:
                    product_category = re.search(r'wood fireplace|wood stove|gas insert|gas stove|gas log set',
                                                 product_line_name,
                                                 flags=re.IGNORECASE)
                    if product_category:
                        unit['product_category'] = product_category[0].title() + 's'
                    else:
                        unit['product_category'] = 'Gas Fireplaces'

        # For series's variants
        if series_info.get('variations'):
            for product_line in series_info['variations']:
                variation_name = product_line['name']
                for variation in product_line['details']:
                    if variation:
                        product_category = re.search('|'.join(re.escape(term)
                                                              for term in VARIATION_PRODUCT_CATEGORY_MAPPING),
                                                     variation_name,
                                                     flags=re.IGNORECASE)
                        if product_category:
                            variation['product_category'] = VARIATION_PRODUCT_CATEGORY_MAPPING[product_category[0].lower()]

    return database


def add_productTypeNonoperative(database: Dict) -> Dict:
    for series_info in database['series'].values():
        # For series's units
        for product_line in series_info['units']:
            for unit in product_line['details']:
                if unit:
                    product_category = unit.get('product_category', '')
                    productTypeNonoperative = re.search(r'gas (fireplaces|stoves|inserts|pellets)',
                                                        product_category, flags=re.IGNORECASE)
                    if productTypeNonoperative:
                        unit['productTypeNonoperative'] = 'Option Product'
                    else:
                        unit['productTypeNonoperative'] = 'Product'

        # For series's variants
        if series_info.get('variations'):
            for product_line in series_info['variations']:
                for variation in product_line['details']:
                    if variation:
                        variation['productTypeNonoperative'] = 'Variation Product'

    return database


def add_display_name(database: Dict) -> Dict:
    for series_info in database['series'].values():
        # For series's units
        for product_line in series_info['units']:
            for unit in product_line['details']:
                if unit:
                    series_name_number = f'{unit.get("series_name", "")} {unit.get("series_number", "")}'.strip()

                    product_category = unit.get("product_category", "").rstrip('s')

                    if unit['fuel_type'] == 'Gas':
                        # unit['display_name'] = f'Napoleon {series_name_number} {unit.get("vent_type", "")} {unit.get("style", "")} {product_category} | {unit.get("base_sku", "")}'
                        # ! remove 'style' for now
                        unit['display_name'] = f'Napoleon {series_name_number} {unit.get("vent_type", "")} {product_category} | {unit.get("base_sku", "")}'
                    else:
                        # unit['display_name'] = f'Napoleon {series_name_number} {unit.get("style", "")} {product_category} | {unit.get("base_sku", "")}'
                        # ! remove 'style' for now
                        unit['display_name'] = f'Napoleon {series_name_number} {product_category} | {unit.get("base_sku", "")}'

        # For series's variants
        if series_info.get('variations'):
            for product_line in series_info['variations']:
                variation_name = product_line['name']
                for variation in product_line['details']:
                    if variation:
                        variation['display_name'] = f'Napoleon {variation_name} | {variation.get("manufacturerSku", "")}'

    return database


def save_db(database: Dict, file: PurePath):
    # Save the new database into json file
    with open(file, 'w') as fp:
        json.dump(database, fp,  indent=2)


if __name__ == "__main__":
    parser = init_argparse()
    debug = parser.parse_args().debug
    reload_db = parser.parse_args().reload_database

    database = {}

    progress = Progress(SpinnerColumn(),
                        "[magenta]{task.description}",
                        BarColumn(),
                        TimeElapsedColumn(),
                        console=console,
                        transient=True)

    if debug:
        # Reload the database using the pricebook
        if reload_db:
            log.info('[bold red blink]Regenerating database from pricebook. Please wait![/]', extra={"markup": True})
            database = extract_napoleon_data_from_catalog()

            # Save the new database into json file
            with open(NAPOLEON_CRUDE_DATA_FILE, 'w') as fp:
                json.dump(database, fp,  indent=2)

        # Otherwise, read from the json file
        else:
            log.info(f'Loading database from {NAPOLEON_CRUDE_DATA_FILE}.')
            with open(NAPOLEON_CRUDE_DATA_FILE, 'r') as fin:
                database = json.load(fin)
    else:
        with progress:
            # Reload the database using the pricebook
            if reload_db:
                log.info('[bold red blink]Regenerating database from pricebook. Please wait![/]', extra={"markup": True})
                task1 = progress.add_task('Creating database...', start=True)
                database = extract_napoleon_data_from_catalog()

                # Save the new database into json file
                with open(NAPOLEON_CRUDE_DATA_FILE, 'w') as fp:
                    json.dump(database, fp,  indent=2)

            # Otherwise, read from the json file
            else:
                log.info(f'Loading database from {NAPOLEON_CRUDE_DATA_FILE}.')
                task1 = progress.add_task('Loading database...', start=True)
                with open(NAPOLEON_CRUDE_DATA_FILE, 'r') as fin:
                    database = json.load(fin)

            progress.update(task1, completed=100)


    # Printing info about the database/catalog
    log.info('This database/catalog contains:')
    log.info(f"Number of series: {len(database['series'])}")
    log.info(f"Number of variations: {len(database['variations'])}")
    log.info(f"Number of products: {len(database['products'])}")

    build_db(database=database)

    # with console.status("[bold green]Validating NCF file...") as status:
    #     # Validate NCF file
    #     validate_ncf(file_to_validate=NCF_CSV_FILE,
    #                 database=database,
    #                 target_file=VALIDATED_NCF_CSV_FILE,
    #                 #  target_file=VALIDATED_NCF_FILE,
    #                 )
    #     console.log('NCF file is populated and validated!')


    # with console.status("[bold green]Uploading validated file to Google sheet...") as status:
    #     # Upload validated file to google sheet
    #     sheet_url = write_csv_to_google_sheet(VALIDATED_NCF_CSV_FILE)
    #     console.log('Validated file upload to googlesheet!')
    #     console.log(f'Sheet URL: {sheet_url}')

    # Print CLI helper if the code was not called with any argument
    if not (debug or reload_db):
        console.print('\n\nCLI info:', style='bold red')
        parser.print_help()