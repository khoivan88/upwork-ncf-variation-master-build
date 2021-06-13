# __Author__: Khoi Van 2021

import argparse
import csv
import json
import logging
import re
import xml.etree.ElementTree as ET
from collections import defaultdict, namedtuple
from dataclasses import dataclass, field
from functools import lru_cache
from itertools import zip_longest
from pathlib import Path, PurePath
from typing import Dict, List, Optional, Set, Union
from xml.dom import minidom

import pandas as pd
import xmltodict
# from openpyxl import load_workbook
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import BarColumn, Progress, SpinnerColumn, TimeElapsedColumn

from extract_napoleon_data_from_catalog import \
    extract_napoleon_data_from_catalog

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
XML_RESULT_FOLDER = DATA_FOLDER / '_xml'
XML_RESULT_FOLDER.mkdir(exist_ok=True)

PRICEBOOK_FILE = ORIGINAL_DATA_FOLDER / 'Napoleon 2021-sanitized.xlsx'
NAPOLEON_CRUDE_DATA_FILE = BUILD_DATA_FOLDER / 'napoleon-crude-data.json'
NAPOLEON_DATABASE_FILE = BUILD_DATA_FOLDER / 'napoleon-database.json'
CSV_EXTRA_INFO_FILE = ORIGINAL_DATA_FOLDER / 'ncfCatalogTemplate.csv'
CURRENT_XML_FILE = ORIGINAL_DATA_FOLDER / 'ncf-mc-all-6.4.21-bu.xml'
XML_TEMPLATE = ORIGINAL_DATA_FOLDER / 'xml_template.xml'
NAPOLEON_XML_FILE = XML_RESULT_FOLDER / 'napoleon.xml'

# NCF_CSV_FILE = DATA_FOLDER / 'ncfNapoleonCatalogTemplate.csv'
OPTIONAL_LOOKUP = {'mandatory': 'Required',
                   'optional': 'Optional'}
# IGNITION_TYPE_LOOKUP = {'mandatory': 'Required',
#                    'optional': 'Optional'}
ADDITIONAL_OPTIONAL_LOOKUP = {'INC': 'Included',
                              'OPT': 'Optional',
                              'N/A': 'Not Available'}

Unit = namedtuple('Unit', 'sku info')


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


def create_xml_object(database_file: PurePath,
                      csv_extra_info_file: PurePath,
                      xml_extra_info_file: PurePath,
                      ):
    db = load_db(database_file)
    csv_extra_info = load_csv_info(csv_extra_info_file)
    xml_extra_info = load_xml_info(xml_extra_info_file)

    data = []

    # for unit in db['series']['series-7']['units'][0]['details']:
    # for unit in db['series']['series-16']['units'][0]['details']:   # has 'Electronic or Millivolt' ignition type option
    # for unit in db['series']['series-28']['units'][0]['details']:   # does not have need the fuelType or ignitionType option tags
    # for unit in db['series']['series-10']['units'][0]['details']:    # has venting 'Top or Rear', not exist in current XML
    # for unit in db['series']['series-23']['units'][0]['details']:    # Wood Fireplace
    # for unit in db['series']['series-17']['units'][0]['details']:    # venting 'Top & Rear', should NOT have `'selectOptionVentConfiguration'`

    # 'Option Product'
    test_series = [
        'series-7',
        'series-16',
        'series-28',
        'series-10',
        'series-17'
    ]
    for series in test_series:
        for unit in db['series'][series]['units'][0]['details']:    # venting 'Top & Rear', should NOT have `'selectOptionVentConfiguration'`
            test_item_sku = unit['manufacturerSku']
            # test_item_catalog_info = db['series']['series-7']
            test_item_brand = 'Napoleon'
            test_item_extra_info = get_item_extra_info(csv_extra_info=csv_extra_info,
                                                    xml_extra_info=xml_extra_info,
                                                    sku=test_item_sku)
            # breakpoint()
            product = Option_Product(sku=test_item_sku,
                                    brand=test_item_brand,
                                    catalog_info=db,
                                    extra_info=test_item_extra_info)

            data.append(product.to_xml())

    # # 'Product'
    # test_series = [
    #     'series-23',
    # ]
    # for series in test_series:
    #     for unit in db['series'][series]['units'][0]['details']:    # venting 'Top & Rear', should NOT have `'selectOptionVentConfiguration'`
    #         test_item_sku = unit['manufacturerSku']
    #         # test_item_catalog_info = db['series']['series-7']
    #         test_item_brand = 'Napoleon'
    #         test_item_extra_info = get_item_extra_info(csv_extra_info=csv_extra_info,
    #                                                 xml_extra_info=xml_extra_info,
    #                                                 sku=test_item_sku)
    #         # breakpoint()
    #         product = Product(sku=test_item_sku,
    #                                 brand=test_item_brand,
    #                                 catalog_info=db,
    #                                 extra_info=test_item_extra_info)

    #         data.append(product.to_xml())

    write_xml(target_file=NAPOLEON_XML_FILE,
              current_xml_file=CURRENT_XML_FILE,
              data=data)
    # print(f'{test=}')


def load_db(database_file: PurePath):
    with open(database_file, 'r') as fin:
        return json.load(fin)


def load_csv_info(csv_file: PurePath) -> List[Dict[str, str]]:
    with open(csv_file, 'r') as fin:
        dict_reader = csv.DictReader(fin)
        # return {key: value
        #         for line in dict_reader
        #         for key, value in line.items()}
        return [line for line in dict_reader]


def load_xml_info(xml_file: PurePath) -> Dict[str, str]:
    with open(xml_file) as fd:
        return xmltodict.parse(fd.read())


def get_item_extra_info(csv_extra_info: List[Dict[str, str]],
                        xml_extra_info: Dict[str, str],
                        sku: str
                        ) -> Dict[str, Dict[str, str]]:
    # Get extra info from CSV file
    csv_info = get_item_csv_info(csv_extra_info, sku)
    item_id = csv_info.get('ID')
    if item_id:
        xml_info = get_item_xml_info(xml_extra_info, item_id)
    else:
        log.info(f'There is no info for item with SKU "{sku}" in current XML file')
        xml_info = {}
    extra_info = {'csv': csv_info, 'xml': xml_info}
    return extra_info


def get_item_csv_info(csv_extra_info: List[Dict[str, str]],
                      sku: str
                      ) -> Dict[str, str]:
    return {key: value
            for item in csv_extra_info
            if item.get('manufacturerSKU').lower() == sku.lower()
            for key, value in item.items()}


def get_item_xml_info(xml_extra_info: Dict[str, str],
                      item_id: str
                      ) -> Dict[str, str]:
    return {key: value
            for product in xml_extra_info['catalog']['product']
            if product['@product-id'] == item_id
            for key, value in product.items()}


def write_xml(target_file: PurePath,
              current_xml_file: PurePath,
              data: str) -> None:
    # * Using ET
    # # To prevent ET from adding `ns` as namespace
    # ET.register_namespace('', 'http://www.demandware.com/xml/impex/catalog/2006-10-31')
    # # Parse XML in with `ET.canonicalize` to remove any white space
    # canonical_tree = ET.canonicalize(XML_TEMPLATE.read_text(), strip_text=True)
    # root = ET.fromstring(canonical_tree)
    # elements = ET.fromstring(data)
    # root.append(elements)
    # target_file.write_bytes(prettify(root))

    # * Using xmltodict
    result_xml = load_xml_info(current_xml_file)

    # ! Remove `<variation-attribute>` tags for now,
    # TODO remove this later for completion
    remove_tags = ['variation-attribute', 'product-option', 'header', 'category']
    for tag in remove_tags:
        del result_xml['catalog'][tag]

    # Update `<product>` tags with all new info
    # result_xml['catalog'].update(xmltodict.parse(data))
    result_xml['catalog']['product'] = []
    for item in data:
        result_xml['catalog']['product'].append(item['product'])

    target_file.write_text(xmltodict.unparse(result_xml,
                                             encoding='UTF-8',
                                             pretty=True,
                                             short_empty_elements=True,
                                             indent='    '))


def make_item_id(sku: str) -> str:
    return re.sub(r'[\./]', '_', sku.lower().replace(' ', '-'))


# def get_base_sku(sku: str, database: Dict[str, Dict]) -> str:
#     """Return the baseSku string for 'unit'

#     Generally, the baseSku = first letters of manufacturerSku + first digits
#     There are exceptions such as 'S20i', 'S25i', 'BHD4-Glass', 'BHD4-Cradle'

#     Parameters
#     ----------
#     row : pd.Series
#         pandas Series, passed in by the `pd.DataFrame.apply()`
#     database : Dict[str, Dict]
#         the local database/catalog

#     Returns
#     -------
#     str
#         The baseSku if 'unit',
#         '' (blank) if found but not a 'unit' or not found
#     """
#     # To tolerate input typo (lower case) in ncf that causes issue: e.g,  in ncf file, line 748, 603, 543
#     # Cannot fix with a simple `str.upper()` due to there is SKU such as 'S20i' and 'S25i'
#     manufacturerSku = sku
#     if not re.search(r'[A-Z]', manufacturerSku):
#         manufacturerSku = sku.upper()
#     baseSku = ''
#     variation = database['variations'].get(manufacturerSku)
#     product = database['products'].get(manufacturerSku)
#     if not variation and not product:
#         for series in database['series'].values():
#             if manufacturerSku in (i['manufacturerSku']
#                                    for unit in series['units']
#                                    for i in unit['details']
#                                    if i):
#                 # Most of the series have 'baseSku'
#                 if series['baseSku']:
#                     # baseSku = ','.join(sku for sku in series['baseSku'] if manufacturerSku.startswith(sku))
#                     baseSku = next((sku for sku in series['baseSku']
#                                     if manufacturerSku.startswith(sku)),
#                                    None)

#                     # For cases such as pricebook lines 614-615. 'manufacturerSku': 'BHD4STFCN' <--> 'baseSku': 'BHD4-Cradle'
#                     if not baseSku:
#                         unit_details = next((unit
#                                              for unit in series['units']
#                                              for item in unit['details']
#                                              if item and manufacturerSku == item['manufacturerSku']),
#                                             None)
#                         unit_index = series['units'].index(unit_details)
#                         baseSku = series['baseSku'][unit_index]

#                     # Special cases such as for ncf lines: 112, 113, 262, 372, 663, 821, 836, 837, 853, 637-40 and 727
#                     # Example: 'BHD4-Glass', 'BHD4-Cradle', 'NEFB33H', 'NEFB40H',
#                     # 'NEFBD50HE', 'NEFB36H-BS', 'GDIZC', 'GDI3N', 'GDIG3N',
#                     # 'GDIX3N', 'GDIX4N', 'GD82NT-PA', 'GSS36CF', 'S20i',
#                     # 'NEFP33-0214W', 'NEFB50H-3SV', 'NEFB60H-3SV',
#                     # !IMPORTANT: leave these baseSku the way they are: 'BHD4-Glass', 'BHD4-Cradle', 'S20i'
#                     if not baseSku[-1].islower():
#                         baseSku = re.search(r'^[A-Z]*\d*', baseSku)[0]

#                 # For some rare case without 'baseSku', e.g. pricebook lines 1818-1819, 1841-1842
#                 else:
#                     # console.log(manufacturerSku)
#                     # See here for info on the regex: https://regex101.com/r/E9id2S/1/
#                     baseSku = re.search(r'^[A-Z]*\d*', manufacturerSku)[0]

#                 break
#         else:
#             baseSku = ''
#     return baseSku


# def get_name_in_catalog(sku: str, database: Dict[str, Dict]) -> str:
#     """Return the name as in the catalog for the item

#     Parameters
#     ----------
#     sku : str
#         the manufacturer SKU
#     database : Dict[str, Dict]
#         the local database/catalog

#     Returns
#     -------
#     str
#         The name of the item as appear in the catalog
#     """
#     # To tolerate input typo (lower case) in ncf that causes issue: e.g,  in ncf file, line 748, 603, 543
#     # Cannot fix with a simple `str.upper()` due to there is SKU such as 'S20i' and 'S25i'
#     manufacturerSku = sku
#     if not re.search(r'[A-Z]', manufacturerSku):
#         manufacturerSku = sku.upper()
#     name = ''
#     variation = database['variations'].get(manufacturerSku)
#     product = database['products'].get(manufacturerSku)
#     if variation or product:
#         name = variation.get('name') or product.get('name')
#     elif not variation and not product:
#         for series in database['series'].values():
#             if manufacturerSku in (i['manufacturerSku']
#                                    for unit in series['units']
#                                    for i in unit['details']
#                                    if i):
#                 # baseSku = ','.join(sku for sku in series['baseSku'] if manufacturerSku.startswith(sku))
#                 name = next((unit['name']
#                              for unit in series['units']
#                              for unit_detail in unit['details']
#                              if unit_detail and unit_detail['manufacturerSku'] == manufacturerSku),
#                             None)
#                 break
#         else:
#             name = ''
#     return name


# def get_ignition_type(name_in_catalog: str) -> str:
#     ignition_type = 'Electronic or Millivolt Ignition'
#     re_ignition_type = re.compile(r'electronic|millivolt', re.IGNORECASE)
#     ignition_type_result = re_ignition_type.search(name_in_catalog)
#     if ignition_type_result:
#         ignition_type = f'{ignition_type_result[0].title()} Ignition'
#     return ignition_type


# def get_units_with_same_series_number(sku: str,
#                                       database: Dict[str, Dict]
#                                       ) -> List[Unit]:
#     """Return the baseSku string for 'unit'

#     Generally, the baseSku = first letters of manufacturerSku + first digits
#     There are exceptions such as 'S20i', 'S25i', 'BHD4-Glass', 'BHD4-Cradle'

#     Parameters
#     ----------
#     row : pd.Series
#         pandas Series, passed in by the `pd.DataFrame.apply()`
#     database : Dict[str, Dict]
#         the local database/catalog

#     Returns
#     -------
#     str
#         The baseSku if 'unit',
#         '' (blank) if found but not a 'unit' or not found
#     """
#     # To tolerate input typo (lower case) in ncf that causes issue: e.g,  in ncf file, line 748, 603, 543
#     # Cannot fix with a simple `str.upper()` due to there is SKU such as 'S20i' and 'S25i'
#     manufacturerSku = sku
#     if not re.search(r'[A-Z]', manufacturerSku):
#         manufacturerSku = sku.upper()
#     series_unit = []
#     variation = database['variations'].get(manufacturerSku)
#     product = database['products'].get(manufacturerSku)
#     if not variation and not product:
#         # Extract the `units` part for the series that contains the units
#         for series in database['series'].values():
#             if manufacturerSku in (i['manufacturerSku']
#                                    for unit in series['units']
#                                    for i in unit['details']
#                                    if i):
#                 # Get series' unit containing the SKU
#                 unit_details = next((unit
#                                      for unit in series['units']
#                                      for item in unit['details']
#                                      if item and manufacturerSku == item['manufacturerSku']),
#                                     None)
#                 item_details = next((item
#                                      for item in unit_details['details']
#                                      if item and manufacturerSku == item['manufacturerSku']),
#                                     None)
#                 item_index = unit_details['details'].index(item_details)
#                 # Get all units that have the same index
#                 series_units = [Unit(unit['name'], unit['details'][item_index]['manufacturerSku'])
#                                 for unit in series['units']
#                                 if unit['details'] and unit['details'][item_index]]
#                 break
#     return series_units


def get_units_with_same_series_number(sku: str,
                                      database: Dict[str, Dict]
                                      ) -> List[Unit]:
    series_units = []
    series_info = get_series_info_from_catalog(sku=sku, type='series', database=database)

    # Get series' unit containing the SKU
    unit_details = next((unit
                            for unit in series_info['units']
                            for item in unit['details']
                            if item and sku == item['manufacturerSku']),
                        None)
    item_details = next((item
                            for item in unit_details['details']
                            if item and sku == item['manufacturerSku']),
                        None)
    # breakpoint()
    item_index = unit_details['details'].index(item_details)

    # Get all units that have the same index
    series_units = [Unit(unit['details'][item_index]['manufacturerSku'], unit['details'][item_index])
                    for unit in series_info['units']
                    if unit['details'] and unit['details'][item_index]]
    return series_units


def get_unit_sku_with_specific_fuel_ignition(requirements: Dict[str, str],
                                             units: List[Unit]) -> str:
    desired_unit = ''
    for unit in units:
        # if re.search(requirements, unit.description, flags=re.IGNORECASE):
        #     desired_unit = unit.sku
        #     break
        for req, value in requirements.items():
            if not re.search(re.escape(value), unit.info.get(req, ''), flags=re.IGNORECASE):
                break
        else:
            desired_unit = unit.sku
            break
    return desired_unit


def has_top_and_rear_venting_options(sku: str,
                                     database: Dict[str, Dict]
                                     ) -> bool:
    return re.search(r'top or rear',
                     get_series_venting_options(sku=sku,
                                                database=database),
                     flags=re.IGNORECASE)


def get_series_venting_options(sku: str,
                               database: Dict[str, Dict]
                               ) -> str:
    # To tolerate input typo (lower case) in ncf that causes issue: e.g,  in ncf file, line 748, 603, 543
    # Cannot fix with a simple `str.upper()` due to there is SKU such as 'S20i' and 'S25i'
    manufacturerSku = sku
    if not re.search(r'[A-Z]', manufacturerSku):
        manufacturerSku = sku.upper()
    venting = ''
    # Extract the `units` part for the series that contains the units
    for series in database['series'].values():
        if manufacturerSku in (i['manufacturerSku']
                                for unit in series['units']
                                for i in unit['details']
                                if i):
            # Get series' venting option:
            venting = series.get('venting', '')
            break
    return venting


def get_series_info_from_catalog(sku: str,
                                 type: str,
                                 database: Dict[str, Dict]
                                 ) -> Dict[str, Dict]:
    '''Return the series containing the sku from the JSON database created from the catalog'''

    # To tolerate input typo (lower case) in ncf that causes issue: e.g,  in ncf file, line 748, 603, 543
    # Cannot fix with a simple `str.upper()` due to there is SKU such as 'S20i' and 'S25i'
    manufacturerSku = sku
    if not re.search(r'[A-Z]', manufacturerSku):
        manufacturerSku = sku.upper()
    if type in ['variations', 'products']:
        return database[type].get(manufacturerSku)
    elif type == 'series':
        for series in database['series'].values():
            if manufacturerSku in (i['manufacturerSku']
                                    for unit in series['units']
                                    for i in unit['details']
                                    if i):
                # Get series' venting option:
                return series


def get_info(sku: str,
             database: Dict[str, Dict],
             info_name: str
             ) -> Optional[str]:
    product_info = ''
    series_info = get_series_info_from_catalog(sku=sku, type='series', database=database)
    if info_name == 'ignition_type':
        ignition_types = {unit.get(info_name, '')
                          for product_line in series_info['units']
                          for unit in product_line['details']
                          if unit}
        # breakpoint()
        ignition_type_string = ' or '.join(sorted(ignition_types)).lower()
        count = ignition_type_string.count("ignition") - 1
        ignition_type_string = re.sub(r'\s{2,}', ' ', ignition_type_string.replace('ignition', '', count).title()).replace('Or', 'or')

        product_info = ignition_type_string
    else:
        product_info = next((unit[info_name]
                                 for product_line in series_info['units']
                                 for unit in product_line['details']
                                 if unit.get('manufacturerSku') and unit['manufacturerSku'] == sku),
                                None)
    return product_info


@dataclass
class Item:
    sku: str
    catalog_info: Dict[str, Dict]
    extra_info: Dict[str, str]
    item_id: str = ''
    upc: str = ''
    display_name: str = ''
    classification_category: str = 'all'

    def __post_init__(self):
        if self.extra_info and self.sku:
            # * Get extra info from CSV file
            # self.upc = self.extra_info['csv'].get('UPC', '')
            # self.item_id = self.extra_info['csv'].get('ID', '')
            # self.display_name = self.extra_info['csv'].get('name__default', '').rstrip('|')

            # * Get extra info from XML file
            self.upc = self.extra_info['xml'].get('upc') or ''
            self.item_id = self.extra_info['xml'].get('@product-id', '')
            if not self.item_id:
                # raise RuntimeError(f'Item "{self.sku}" does not have info in current XML!')
                self.item_id = make_item_id(self.sku)

            # if self.extra_info['xml'].get('display-name'):
            #     self.display_name = self.extra_info['xml']['display-name'].get('#text', '').rstrip('|')
            self.display_name = get_info(sku=self.sku, database=self.catalog_info, info_name='display_name')


    def to_xml(self) -> ET.Element:
        XML_TAG_MAPPING = {'ean': {'text': ''},
                           'upc': {'text': self.upc},
                           'unit':{'text': '1'},
                           'min-order-quantity': {'text': '1'},
                           'step-quantity': {'text': '1'},
                           'display-name': {
                               'attributes': {'xml:lang': "x-default"},
                               'text': self.display_name},
                           'store-force-price-flag': {'text': 'false'},
                           'store-non-inventory-flag': {'text': 'false'},
                           'store-non-revenue-flag': {'text': 'false'},
                           'store-non-discountable-flag': {'text': 'false'},
                           'online-flag': {'text': 'true'},
                           'available-flag': {'text': 'true'},
                           'searchable-flag': {'text': 'true'},
                           'tax-class-id': {'text': 'standard'},
                           'classification-category': {
                               'attributes': {'catalog-id': "northcountryfire-storefront",},
                               'text': self.classification_category,},
                           'pinterest-enabled-flag': {'text': 'false'},
                           'facebook-enabled-flag': {'text': 'false'},
                           'store-attributes': {
                               'sub-tags' : {'force-price-flag': {'text': 'false',},
                                             'non-inventory-flag': {'text': 'false',},
                                             'non-revenue-flag': {'text': 'false',},
                                             'non-discountable-flag': {'text': 'false',},
                                             }},
                           }
        # create the file structure
        data = ET.Element('product')
        data.set('product-id', self.item_id)

        # Set trivial tags
        for name, var in XML_TAG_MAPPING.items():
            tag = ET.SubElement(data, name,
                                attrib=var.get('attributes', {}))
            tag.text = str(var.get('text', ''))
            # Create sub tags if exist
            sub_tags = var.get('sub-tags')
            if sub_tags:
                for sub_tag_name, sub_tag_attr in sub_tags.items():
                    sub_tag = ET.SubElement(tag, sub_tag_name)
                    sub_tag.text = str(sub_tag_attr.get('text'))

        # create a new XML file with the results
        return data


@dataclass
class Product(Item):
    brand: str = ''
    product_type_nonoperative: str = 'Product'
    classification_category: str = 'all'

    def __post_init__(self):
        super().__post_init__()
        self.base_sku = get_info(sku=self.sku, database=self.catalog_info, info_name='base_sku')
        self.product_set_id = f'{self.item_id}-set'

        # Use info from catalog
        self.product_category = get_info(sku=self.sku, database=self.catalog_info, info_name='product_category')
        self.series_name = get_info(sku=self.sku, database=self.catalog_info, info_name='series_name')
        self.series_number = get_info(sku=self.sku, database=self.catalog_info, info_name='series_number')
        self.fuel_type = get_info(sku=self.sku, database=self.catalog_info, info_name='fuel_type')

    def to_xml(self):
        data = xmltodict.parse(ET.tostring(super().to_xml()))
        page_attributes = self.extra_info['xml'].get('page-attributes', {})
        mapping = {
            'brand': {'#text': self.brand},
            'manufacturer-sku': {'#text': self.sku},
            'page-attributes': page_attributes,
            'custom-attributes': {
                'custom-attribute' : [
                    {'@attribute-id': 'baseSku', '#text': self.base_sku},
                    {'@attribute-id': 'configurableProduct', '#text': 'true'},
                    {'@attribute-id': 'fuelType', '#text': self.fuel_type},
                    {'@attribute-id': 'productCategory', '#text': self.product_category},
                    {'@attribute-id': 'productSetId', '#text': self.product_set_id},
                    {'@attribute-id': 'productTypeNonoperative', '#text': self.product_type_nonoperative},
                    {'@attribute-id': 'series', '#text': self.series_name},
                    {'@attribute-id': 'seriesNumber', '#text': self.series_number},
                    {'@attribute-id': 'sku', '#text': self.sku},
                    ]
                },
            }

        data['product'].update(mapping)
        return data


@dataclass
class Option_Product(Product):
    brand: str = ''
    product_type_nonoperative: str = 'Option Product'
    classification_category: str = 'gas-fireplaces'

    def __post_init__(self):
        super().__post_init__()
        # # self.base_sku = get_base_sku(sku=self.sku, database=self.catalog_info)
        # self.base_sku = get_info(sku=self.sku, database=self.catalog_info, info_name='base_sku')
        # self.name_in_catalog = get_name_in_catalog(sku=self.sku, database=self.catalog_info)
        # self.ignition_type = get_ignition_type(name_in_catalog=self.name_in_catalog)
        self.ignition_type = get_info(sku=self.sku, database=self.catalog_info, info_name='ignition_type')
        # self.product_set_id = f'{self.item_id}-set'

        # # ! Use current XML file, info not always correct
        # self.product_category = self.extra_info['csv'].get('c__productCategory', '')
        # self.series_name = self.extra_info['csv'].get('c__series', '')
        # self.series_number = self.extra_info['csv'].get('c__seriesNumber', '')

        # # Use info from catalog
        # self.product_category = get_info(sku=self.sku, database=self.catalog_info, info_name='product_category')
        # self.series_name = get_info(sku=self.sku, database=self.catalog_info, info_name='series_name')
        # self.series_number = get_info(sku=self.sku, database=self.catalog_info, info_name='series_number')

        units_with_same_series_number = get_units_with_same_series_number(sku=self.sku,
                                                                          database=self.catalog_info)

        # self.skuLP = get_unit_sku_with_specific_fuel_ignition(requirements=r'electronic.*propane',
        #                                                       units=units_with_same_series_number)
        # self.skuNG = get_unit_sku_with_specific_fuel_ignition(requirements=r'electronic.*natural gas',
        #                                                       units=units_with_same_series_number)
        self.skuLP = get_unit_sku_with_specific_fuel_ignition(
            requirements={"gas_fuel_type": "propane",
                          "ignition_type": "electronic",},
            units=units_with_same_series_number)
        self.skuNG = get_unit_sku_with_specific_fuel_ignition(
            requirements={"gas_fuel_type": "natural gas",
                          "ignition_type": "electronic",},
            units=units_with_same_series_number)

        # # SKU if fuel = propane + electronic ignition sku
        # self.skuLpIpi = get_unit_sku_with_specific_fuel_ignition(requirements=r'electronic.*propane',
        #                                                       units=units_with_same_series_number)
        self.skuLpIpi = get_unit_sku_with_specific_fuel_ignition(
            requirements={"gas_fuel_type": "propane",
                          "ignition_type": "electronic",},
            units=units_with_same_series_number)

        # # SKU if fuel = natural gas + electronic ignition
        # self.skuNgIpi = get_unit_sku_with_specific_fuel_ignition(requirements=r'electronic.*natural gas',
        #                                                       units=units_with_same_series_number)
        self.skuNgIpi = get_unit_sku_with_specific_fuel_ignition(
            requirements={"gas_fuel_type": "natural gas",
                          "ignition_type": "electronic",},
            units=units_with_same_series_number)

        # # SKU if fuel = propane + millivolt
        # self.skuLpMv = get_unit_sku_with_specific_fuel_ignition(requirements=r'millivolt.*propane',
        #                                                       units=units_with_same_series_number)
        self.skuLpMv = get_unit_sku_with_specific_fuel_ignition(
            requirements={"gas_fuel_type": "propane",
                          "ignition_type": "millivolt",},
            units=units_with_same_series_number)

        # # SKU if fuel = natural gas + millivolt
        # self.skuNgMv = get_unit_sku_with_specific_fuel_ignition(requirements=r'millivolt.*natural gas',
        #                                                       units=units_with_same_series_number)
        self.skuNgMv = get_unit_sku_with_specific_fuel_ignition(
            requirements={"gas_fuel_type": "natural gas",
                          "ignition_type": "millivolt",},
            units=units_with_same_series_number)

        # If a unit set (units with the same series + seriesNumber) has more than one ignition type
        self.selectOptionIgnitionType = bool(
            # get_unit_sku_with_specific_fuel_ignition(requirements=r'millivolt',
            #                                          units=units_with_same_series_number)
            # and
            # get_unit_sku_with_specific_fuel_ignition(requirements=r'electronic',
            #                                          units=units_with_same_series_number)
            get_unit_sku_with_specific_fuel_ignition(requirements={"ignition_type": "millivolt"},
                                                     units=units_with_same_series_number)
            and
            get_unit_sku_with_specific_fuel_ignition(requirements={"ignition_type": "electronic"},
                                                     units=units_with_same_series_number)

            )

        self.selectOptionVentConfiguration = has_top_and_rear_venting_options(sku=self.sku,
                                                                              database=self.catalog_info)

    def to_xml(self):
        data = super().to_xml()
        # page_attributes = self.extra_info['xml'].get('page-attributes', {})
        share_option = []
        if self.skuNG and self.skuLP:
            share_option.append({'@option-id': 'selectOptionFuelType'})
        if self.selectOptionIgnitionType:
            share_option.append({'@option-id': 'selectOptionIgnitionType'})
        if self.selectOptionVentConfiguration:
            share_option.append({'@option-id': 'selectOptionVentConfiguration'})
        mapping = {
            # 'brand': {'#text': self.brand},
            # 'manufacturer-sku': {'#text': self.sku},
            # 'page-attributes': page_attributes,
            'custom-attributes': {
                'custom-attribute' : [
                    # {'@attribute-id': 'baseSku', '#text': self.base_sku},
                    # {'@attribute-id': 'configurableProduct', '#text': 'true'},
                    # {'@attribute-id': 'fuelType', '#text': 'Gas'},
                    {'@attribute-id': 'ignitionType', '#text': self.ignition_type},
                    # {'@attribute-id': 'productCategory', '#text': self.product_category},
                    # {'@attribute-id': 'productSetId', '#text': self.product_set_id},
                    # {'@attribute-id': 'productTypeNonoperative', '#text': self.product_type_nonoperative},
                    # {'@attribute-id': 'series', '#text': self.series_name},
                    # {'@attribute-id': 'seriesNumber', '#text': self.series_number},
                    # {'@attribute-id': 'sku', '#text': self.sku},
                    {'@attribute-id': 'skuNG', '#text': self.skuNG},
                    {'@attribute-id': 'skuNgIpi', '#text': self.skuNgIpi},
                    {'@attribute-id': 'skuNgMv', '#text': self.skuNgMv},
                    {'@attribute-id': 'skuLP', '#text': self.skuLP},
                    {'@attribute-id': 'skuLpIpi', '#text': self.skuLpIpi},
                    {'@attribute-id': 'skuLpMv', '#text': self.skuLpMv},
                    ]
                },
            'options': {
                'shared-option' : share_option
                },
            }

        data['product']['custom-attributes']['custom-attribute'].extend(mapping['custom-attributes']['custom-attribute'])
        data['product'].update({k: v
                                for k, v in mapping.items()
                                if k != 'custom-attributes'})
        return data


def prettify(elem: ET.Element) -> bytes:
    """Return a pretty-printed XML string for the Element.
    """
    rough_string = ET.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="    ", newl="\n", encoding='UTF-8')



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

    create_xml_object(database_file=NAPOLEON_DATABASE_FILE,
                      csv_extra_info_file=CSV_EXTRA_INFO_FILE,
                      xml_extra_info_file=CURRENT_XML_FILE)

    # Print CLI helper if the code was not called with any argument
    if not (debug or reload_db):
        console.print('\n\nCLI info:', style='bold red')
        parser.print_help()
