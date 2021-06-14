# __Author__: Khoi Van 2021

import os
import sys

sys.path.append(os.path.realpath('src'))

import json
from pathlib import Path
from typing import Dict

import pytest
from src.extract_napoleon_data_from_catalog import (check_base_sku, check_parent_sku,
                                        is_shared_variation_product,
                                        is_step_variation_product, is_unit,
                                        required_or_optional_variation)


CURRENT_FILEPATH = Path(__file__).resolve().parent.parent.parent
DATA_FOLDER = CURRENT_FILEPATH / 'src' / 'data'
DATABASE_FILE = DATA_FOLDER / '_build' / 'napoleon-crude-data.json'


@pytest.fixture
def database() -> Dict[str, Dict]:
    """[summary]

    Returns
    -------
    Dict[str, Dict]
        The local database/catalog saved as JSON
    """
    with open(DATABASE_FILE, 'r') as fin:
        database = json.load(fin)
    return database


@pytest.mark.parametrize(
    "row, expect", [
        ({'manufacturerSKU': 'gdsll-kt'}, ''),                  # Typo in input file, should have been uppercase
        ({'manufacturerSKU': 'w175-0726'}, ''),                 # Typo in input file, should have been uppercase
        ({'manufacturerSKU': 'S20i'}, 'TRUE'),                  # Typo in input file, should have been uppercase
        ({'manufacturerSKU': 'LV62N'}, 'TRUE'),
        ({'manufacturerSKU': '2200-1'}, 'TRUE'),
        ({'manufacturerSKU': 'NEFI18H'}, 'TRUE'),
        ({'manufacturerSKU': 'WHVF31N'}, 'Not found'),
        ({'manufacturerSKU': 'W175-0178'}, 'Not found'),
        ({'manufacturerSKU': 'W565-0274-SER'}, 'Not found'),
        ({'manufacturerSKU': 'REK'}, 'Not found'),
        ({'manufacturerSKU': 'NEFL32FH'}, 'Not found'),
        ({'manufacturerSKU': 'FPWI3-H'}, ''),
        ({'manufacturerSKU': 'BFKXL'}, ''),
        ({'manufacturerSKU': 'CP'}, ''),
        ({'manufacturerSKU': 'GV825KT'}, ''),
        ({'manufacturerSKU': 'PVA52'}, ''),                     # 'product'
        ({'manufacturerSKU': 'PVAL50'}, ''),                    # 'product'
    ]
)
def test_is_unit(database, row, expect):
    answer = is_unit(row, database)
    assert answer == expect


@pytest.mark.parametrize(
    "row, expect", [
        ({'manufacturerSKU': 'gdsll-kt'}, ''),              # Typo in input file, should have been uppercase
        ({'manufacturerSKU': 'w175-0726'}, ''),             # Typo in input file, should have been uppercase
        ({'manufacturerSKU': 'S20i'}, 'S20i'),              # Special cases, to make sure baseSku conform to the PDF instruction (just first letters and numbers)
        ({'manufacturerSKU': 'BHD4PGN'}, 'BHD4-Glass'),     # Special cases, to make sure baseSku conform to the PDF instruction (just first letters and numbers)
        ({'manufacturerSKU': 'BHD4STGN'}, 'BHD4-Cradle'),   # Special cases, to make sure baseSku conform to the PDF instruction (just first letters and numbers)
        ({'manufacturerSKU': 'NEFB33H'}, 'NEFB33'),         # Special cases, to make sure baseSku conform to the PDF instruction (just first letters and numbers)
        ({'manufacturerSKU': 'NEFB40H'}, 'NEFB40'),         # Special cases, to make sure baseSku conform to the PDF instruction (just first letters and numbers)
        ({'manufacturerSKU': 'NEFBD50HE'}, 'NEFBD50'),      # Special cases, to make sure baseSku conform to the PDF instruction (just first letters and numbers)
        ({'manufacturerSKU': 'NEFB36H-BS'}, 'NEFB36'),      # Special cases, to make sure baseSku conform to the PDF instruction (just first letters and numbers)
        ({'manufacturerSKU': 'GDIZC-NSB'}, 'GDIZC'),        # Special cases, to make sure baseSku conform to the PDF instruction (just first letters and numbers)
        ({'manufacturerSKU': 'GDI3NE'}, 'GDI3'),            # Special cases, to make sure baseSku conform to the PDF instruction (just first letters and numbers)
        ({'manufacturerSKU': 'GDIG3N'}, 'GDIG3'),           # Special cases, to make sure baseSku conform to the PDF instruction (just first letters and numbers)
        ({'manufacturerSKU': 'GDIX3N'}, 'GDIX3'),           # Special cases, to make sure baseSku conform to the PDF instruction (just first letters and numbers)
        ({'manufacturerSKU': 'GDIX4N'}, 'GDIX4'),           # Special cases, to make sure baseSku conform to the PDF instruction (just first letters and numbers)
        ({'manufacturerSKU': 'GD82NT-PAESB'}, 'GD82'),      # Special cases, to make sure baseSku conform to the PDF instruction (just first letters and numbers)
        # ({'manufacturerSKU': 'GSS36CFN'}, 'GSS36'),         # Special cases, to make sure baseSku conform to the PDF instruction (just first letters and numbers)
        ({'manufacturerSKU': 'NEFP33-0214W'}, 'NEFP33'),    # Special cases, to make sure baseSku conform to the PDF instruction (just first letters and numbers)
        ({'manufacturerSKU': 'NEFB50H-3SV'}, 'NEFB50'),     # Special cases, to make sure baseSku conform to the PDF instruction (just first letters and numbers)
        ({'manufacturerSKU': 'NEFB60H-3SV'}, 'NEFB60'),     # Special cases, to make sure baseSku conform to the PDF instruction (just first letters and numbers)
        ({'manufacturerSKU': 'GDS20NSB'}, 'GDS20'),
        ({'manufacturerSKU': 'HDX52NT-2'}, 'HDX52'),
        ({'manufacturerSKU': 'GSS42CFN'}, 'GSS42'),
        ({'manufacturerSKU': 'GDIZC-NSB'}, 'GDIZC'),
        ({'manufacturerSKU': 'AS35WI'}, 'Not found'),
        ({'manufacturerSKU': 'W565-0274-SER'}, 'Not found'),
        ({'manufacturerSKU': 'NZ3000H'}, 'Not found'),
        ({'manufacturerSKU': 'GS200-G'}, 'Not found'),
        ({'manufacturerSKU': 'B440-KT'}, ''),
        ({'manufacturerSKU': 'W660-0081'}, ''),
        ({'manufacturerSKU': 'BANB100'}, ''),
        ({'manufacturerSKU': 'RP5'}, ''),           # 'product'
        ({'manufacturerSKU': 'AVS811KT-1'}, ''),    # 'product'
        ({'manufacturerSKU': 'PVA-ASCENT'}, ''),    # 'product'
    ]
)
def test_check_base_sku(database, row, expect):
    answer = check_base_sku(row, database)
    assert answer == expect


@pytest.mark.xfail
@pytest.mark.parametrize(
    "row, expect", [
        ({'manufacturerSKU': 'gdsll-kt'},
         'GDS60-1NNSB,GDS60-1NSB,GDS25N-1,GDS25NN-1,GDS25NW-1,GDS20NE,GDS20NNE,GDS20NNSB,GDS20NSB'),    # Typo in input file, should have been uppercase; 'variation'
        ({'manufacturerSKU': 'w175-0726'}, 'GDIX4N'),                   # Typo in input file, should have been uppercase; 'variation'
        ({'manufacturerSKU': 'S20i'}, ''),                              # Typo in input file, should have been uppercase; 'unit'
        ({'manufacturerSKU': '2200-1'}, ''),                            # 'units'
        ({'manufacturerSKU': 'GDS25N-1'}, ''),                          # 'units'
        ({'manufacturerSKU': 'GD82NT-PAESB'}, ''),                      # 'units'
        ({'manufacturerSKU': 'NEFP33-0214W'}, ''),                      # 'units'
        ({'manufacturerSKU': 'NEFL32FH'}, ''),                          # 'Not found' + 'units'
        ({'manufacturerSKU': 'DLE, RAK35/40'}, ''),                     # 'Not found' + 'units'
        ({'manufacturerSKU': 'PVA36-1'}, ''),                           # 'Not found' + 'variation'?
        ({'manufacturerSKU': 'PVA52'}, ''),                             # 'product'
        ({'manufacturerSKU': 'PVAL50'}, ''),                            # 'product'
        ({'manufacturerSKU': 'SZCSB'}, 'GDIZC-NSB'),                    # 'variation'
        ({'manufacturerSKU': 'GIFBK6SB'}, 'GI3600-4NSB,GDIZC-NSB'),     # 'variation'
        ({'manufacturerSKU': 'BKGDIX3'},
         'GDI3N,GDI3NE,GDIG3N,GDIX3N,GDIX4N,GDIZC-NSB,GI3600-4NSB'),    # 'variation'
        ({'manufacturerSKU': 'BKGDI3'},
         'GDI3N,GDI3NE,GDIG3N,GDIX3N,GDIX4N,GDIZC-NSB,GI3600-4NSB'),    # 'variation'
        ({'manufacturerSKU': 'GICSK'}, 'GI3600-4NSB'),                  # 'variation'
        ({'manufacturerSKU': 'NEP70'}, 'S20-1,S25'),                    # 'variation'
        ({'manufacturerSKU': 'BFKXL'},
         ','.join(['LVX62NX-1,LVX62N2X-1,LVX74NX-1,LVX74N2X-1,LVX74PX,LVX74P2X',
                   'LV62N,LV62N2,LV74N,LV74N2,LV74P,LV74P2'])),         # 'variation'
        ({'manufacturerSKU': 'MKBA'},
         ','.join(['LVX38NX-1,LVX38N2X-1,LVX50NX-1,LVX50N2X-1,LVX62NX-1,LVX62N2X-1,LVX74NX-1,LVX74N2X-1,LVX74PX,LVX74P2X',
                   'LV38N-1,LV38N2-1,LV50N-2,LV50N2-2,LV62N,LV62N2,LV74N,LV74N2,LV74P,LV74P2',
                   'BL36NTE-1,BL46NTE',
                   'L38N,L38N2,L50N,L50N2',
                   'HDX52NT-2,HDX52PT-2',
                   'HD81NT-1',
                   'D42NTRE,D42PTRE',
                   'DX42NTRE,DX42PTRE',
                   'GX36NTRE-1,GX36PTRE-1,GX36NTR-1,GX36PTR-1',
                   'GX42NTRE,GX42PTRE',
                   'GX70NTE-1,GX70PTE-1',
                   'B30NTRE-1,B30NTR-1,B36NTRE-1,B36PTRE-1,B36NTR-1,B36PTR-1,B42NTRE,B42PTRE,B42NTR,B42PTR,B46NTRE,B46NTR',
                   'BHD4STFCN,BHD4PFCN,BHD4STGN,BHD4PGN,BHD4STN,BHD4PN',
                   'WHD31NSB,WHD48N,WHD48P',
                   'WHVF24N,WHVF24P,WHVF31N,WHVF31P',
                   'GVF36-2N,GVF36-2P,GVF42-1N,GVF42-1P',
                   'GVFT8N,GVFT8P',
                   'GDI3N,GDI3NE,GDIG3N,GDIX3N,GDIX4N',
                   'GDIZC-NSB',
                   'GI3600-4NSB',
                   'GSS48,GSS48ST',
                   'GSS42CFN',
                   'GSS36CFN',
                   'GPFL48MHP,GPFL48,GPFS60,GPFR60,GPFGN-2,GPFGP-2'])),      # 'variation'
        ({'manufacturerSKU': 'EFCN'},
         ','.join(['AX36NTE,AX36PTE,AX42NTE,AX42PTE',
                   'B30NTR-1,B30NTRE-1,B36NTR-1,B36NTRE-1,B36PTR-1,B36PTRE-1,B42NTR,B42NTRE,B42PTR,B42PTRE,B46NTR,B46NTRE',
                   'BHD4PFCN,BHD4PGN,BHD4PN,BHD4STFCN,BHD4STGN,BHD4STN',
                   'BL36NTE-1,BL46NTE',
                   'D42NTRE,D42PTRE,DX42NTRE,DX42PTRE',
                   'EX36NTEL,EX36PTEL,EX42NTEL,EX42PTEL',
                   'GDI3N,GDI3NE,GDIG3N,GDIX3N,GDIX4N,GDIZC-NSB',
                   'GDS20NE,GDS20NNE,GDS20NNSB,GDS20NSB',
                   'GDS25N-1,GDS25NN-1,GDS25NW-1',
                   'GDS26N-1,GDS26NN-1,GDS26NW-1',
                   'GDS28-1NE,GDS28-1NSB',
                   'GDS50-1NE,GDS50-1NSB',
                   'GDS60-1NNSB,GDS60-1NSB',
                   'GI3600-4NSB',
                   'GX36NTR-1,GX36NTRE-1,GX36PTR-1,GX36PTRE-1,GX42NTRE,GX42PTRE,GX70NTE-1,GX70PTE-1',
                   'HD81NT-1',
                   'HDX52NT-2,HDX52PT-2',
                   'L38N,L38N2,L50N,L50N2',
                   'LV38N-1,LV38N2-1,LV50N-2,LV50N2-2,LV62N,LV62N2,LV74N,LV74N2,LV74P,LV74P2',
                   'LVX38N2X-1,LVX38NX-1,LVX50N2X-1,LVX50NX-1,LVX62N2X-1,LVX62NX-1,LVX74N2X-1,LVX74NX-1,LVX74P2X,LVX74PX',
                   'WHD31NSB,WHD48N,WHD48P'])),             # 'variation' + 'Included/Optional'
        ({'manufacturerSKU': '111KT'},
         ','.join(['GVF36-2N,GVF36-2P,GVF42-1N,GVF42-1P',
                   'GVFT8N,GVFT8P',
                   'NZ3000H-1,NZ5000-T,NZ8000',
                   'S20-1,S25',
                   'WHVF24N,WHVF24P,WHVF31N,WHVF31P'])),    # 'variation' + 'Optional'
    ]
)
def test_check_parent_sku(database, row, expect):
    answer = check_parent_sku(row, database)
    sorted_answer = ','.join(sorted(answer.split(',')))
    sorted_expect = ','.join(sorted(expect.split(',')))
    assert sorted_answer == sorted_expect


@pytest.mark.parametrize(
    "row, expect", [
        ({'manufacturerSKU': 'gdsll-kt'}, 'TRUE'),      # Typo in input file, should have been uppercase; 'variation'
        ({'manufacturerSKU': 'w175-0726'}, ''),         # Typo in input file, should have been uppercase; 'variation'
        ({'manufacturerSKU': 'S20i'}, ''),              # Typo in input file, should have been uppercase; 'unit'
        ({'manufacturerSKU': '2200-1'}, ''),            # 'units'
        ({'manufacturerSKU': 'GDS25N-1'}, ''),          # 'units'
        ({'manufacturerSKU': 'GD82NT-PAESB'}, ''),      # 'units'
        ({'manufacturerSKU': 'NEFP33-0214W'}, ''),      # 'units'
        ({'manufacturerSKU': 'NEFL32FH'}, ''),          # 'Not found' + 'units'
        ({'manufacturerSKU': 'DLE, RAK35/40'}, ''),     # 'Not found' + 'units'
        ({'manufacturerSKU': 'PVA36-1'}, ''),           # 'Not found' + 'variation'?
        ({'manufacturerSKU': 'PVA52'}, ''),             # 'product'
        ({'manufacturerSKU': 'PVAL50'}, ''),            # 'product'
        ({'manufacturerSKU': 'SZCSB'}, ''),             # 'variation'
        ({'manufacturerSKU': 'GIFBK6SB'}, 'TRUE'),      # 'variation'
        ({'manufacturerSKU': 'BKGDIX3'}, 'TRUE'),       # 'variation'
        ({'manufacturerSKU': 'BKGDI3'}, 'TRUE'),        # 'variation'
        ({'manufacturerSKU': 'GICSK'}, ''),             # 'variation'
        ({'manufacturerSKU': 'NEP70'}, 'TRUE'),         # 'variation'
        ({'manufacturerSKU': 'EFCN'}, 'TRUE'),          # 'variation' + 'Included/Optional'
        ({'manufacturerSKU': '111KT'},'TRUE'),          # 'variation' + 'Optional'
    ]
)
def test_is_shared_variation_product(database, row, expect):
    parent_sku = check_parent_sku(row, database)
    row['c__parentSku'] = parent_sku
    answer = is_shared_variation_product(row)
    assert answer == expect


@pytest.mark.parametrize(
    "row, expect", [
        ({'manufacturerSKU': 'gdsll-kt'}, 'TRUE'),      # Typo in input file, should have been uppercase; 'variation'
        ({'manufacturerSKU': 'w175-0726'}, 'TRUE'),     # Typo in input file, should have been uppercase; 'variation'
        ({'manufacturerSKU': 'S20i'}, ''),              # Typo in input file, should have been uppercase; 'unit'
        ({'manufacturerSKU': '2200-1'}, ''),            # 'units'
        ({'manufacturerSKU': 'GDS25N-1'}, ''),          # 'units'
        ({'manufacturerSKU': 'GD82NT-PAESB'}, ''),      # 'units'
        ({'manufacturerSKU': 'NEFP33-0214W'}, ''),      # 'units'
        ({'manufacturerSKU': 'NEFL32FH'}, ''),          # 'Not found' + 'units'
        ({'manufacturerSKU': 'DLE, RAK35/40'}, ''),     # 'Not found' + 'units'
        ({'manufacturerSKU': 'PVA36-1'}, ''),           # 'Not found' + 'variation'?
        ({'manufacturerSKU': 'PVA52'}, ''),             # 'product'
        ({'manufacturerSKU': 'PVAL50'}, ''),            # 'product'
        ({'manufacturerSKU': 'SZCSB'}, 'TRUE'),         # 'variation'
        ({'manufacturerSKU': 'GIFBK6SB'}, 'TRUE'),      # 'variation'
        ({'manufacturerSKU': 'BKGDIX3'}, 'TRUE'),       # 'variation'
        ({'manufacturerSKU': 'BKGDI3'}, 'TRUE'),        # 'variation'
        ({'manufacturerSKU': 'GICSK'}, 'TRUE'),         # 'variation'
        ({'manufacturerSKU': 'NEP70'}, 'TRUE'),         # 'variation'
        ({'manufacturerSKU': 'EFCN'}, 'TRUE'),          # 'variation' + 'Included/Optional'
        ({'manufacturerSKU': '111KT'},'TRUE'),          # 'variation' + 'Optional'
    ]
)
def test_is_step_variation_product(database, row, expect):
    parent_sku = check_parent_sku(row, database)
    row['c__parentSku'] = parent_sku
    answer = is_step_variation_product(row)
    assert answer == expect


@pytest.mark.parametrize(
    "row, expect", [
        ({'manufacturerSKU': 'gdsll-kt'}, 'Optional'),          # Typo in input file, should have been uppercase; 'variation'
        ({'manufacturerSKU': 'w175-0726'}, 'Optional'),         # Typo in input file, should have been uppercase; 'variation'
        ({'manufacturerSKU': 'S20i'}, ''),                      # Typo in input file, should have been uppercase; 'unit'
        ({'manufacturerSKU': '2200-1'}, ''),                    # 'units'
        ({'manufacturerSKU': 'GDS25N-1'}, ''),                  # 'units'
        ({'manufacturerSKU': 'GD82NT-PAESB'}, ''),              # 'units'
        ({'manufacturerSKU': 'NEFP33-0214W'}, ''),              # 'units'
        ({'manufacturerSKU': 'NEFL32FH'}, ''),                  # 'Not found' + 'units'
        ({'manufacturerSKU': 'DLE, RAK35/40'}, ''),             # 'Not found' + 'units'
        ({'manufacturerSKU': 'PVA36-1'}, ''),                   # 'Not found' + 'variation'?
        ({'manufacturerSKU': 'PVA52'}, ''),                     # 'product'
        ({'manufacturerSKU': 'PVAL50'}, ''),                    # 'product'
        ({'manufacturerSKU': 'SZCSB'}, 'Required'),             # 'variation'
        ({'manufacturerSKU': 'GIFBK6SB'}, 'Required/Optional'), # 'variation'
        ({'manufacturerSKU': 'BKGDIX3'}, 'Optional'),           # 'variation'
        ({'manufacturerSKU': 'BKGDI3'}, 'Optional'),            # 'variation'
        ({'manufacturerSKU': 'GICSK'}, 'Required/Optional'),    # 'variation'
        ({'manufacturerSKU': 'NEP70'}, 'Optional'),             # 'variation'
        ({'manufacturerSKU': 'EFCN'}, 'Included/Optional'),     # 'variation' + 'Included/Optional'
        ({'manufacturerSKU': '111KT'},'Optional'),              # 'variation' + 'Optional'
        ({'manufacturerSKU': 'GICSK'}, 'Required/Optional'),    # 'variation'
    ]
)
def test_required_or_optional_variation(database, row, expect):
    # Get 'parentSku' and add to the input (`row`)
    row['c__parentSku'] = check_parent_sku(row, database)
    # Get 'c__isStepVariationProduct' result and add to the input (`row`)
    row['c__isStepVariationProduct'] = is_step_variation_product(row)
    answer = required_or_optional_variation(row, database)
    assert answer == expect
