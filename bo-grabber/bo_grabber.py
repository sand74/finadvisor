#!/usr/bin/env python3
#  Скрипт для скачивания информации с bo.nalog.ru
#  Ввод из stdin последовательность строк - первое поле ИНН
#  Вывод в stdout - формат ИНН   результат
#  Скаченные архивы сохраняются в указанную папку или в текущий дипекторий если она не указана

import argparse
import logging.config
import os
import sys
import time
import pandas as pd

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {"format": "%(asctime)s %(name)-12s %(levelname)-8s %(message)s"},
    },
    "handlers": {
        "file_handler": {
            "level": "INFO",
            "formatter": "default",
            "class": "logging.FileHandler",
            "filename": 'grabber.log',
            "mode": "a",
        },
    },
    "loggers": {
        "": {"handlers": ["file_handler"], "level": "INFO", "propagate": False},
    },
}
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)

BASE_URL = "https://bo.nalog.ru/"
OUTPUT_DIR = ''
WAIT_IVAL = 5


def parse_args(argv):
    """
    Parse command-line args.
    """
    parser = argparse.ArgumentParser(
        prog='bo_grabber',
        formatter_class=argparse.MetavarTypeHelpFormatter)
    parser.add_argument('folder', metavar='OUTPUT_DIR', type=str, nargs='?', default='',
                        help='Output folder for inns')
    parser.add_argument('-w', '--wait', metavar='WAIT_IVAL', type=int, nargs='?', default=5,
                        help='Wait interval between queries')
    parser.add_argument('-s', '--sep', metavar='SEPARATOR', type=str, nargs='?', default=' ',
                        help='Input line separator')
    parser.add_argument('-y', '--year', metavar='YEAR', type=str, nargs='?', default=None,
                        help='Downoload this year else last year')
    parser.add_argument('--noxls', default=False, action='store_true',
                         help='Skip xls file')
    logger.info(f'Args: {parser.parse_args(argv[1:])}')
    return parser.parse_args(argv[1:])


def get_buh_page(driver: webdriver.Chrome, inn: str, load_xls: bool=True, year: str=None) -> dict:
    """
    Получение страницы бух отчетности по ИНН
    :param driver: chrome driver
    :param inn: ИНН
    :return: None
    """
    info = {'inn': inn}

    # Load base page
    driver.get(BASE_URL)

    # Find inn input field
    WebDriverWait(driver, 5).until(
        ec.presence_of_element_located((By.CLASS_NAME, 'input-search'))
    )

    input_form = driver.find_element(By.CLASS_NAME, 'input-search')
    input_field = input_form.find_element(By.ID, 'search')
    input_field.clear()
    input_field.send_keys(inn)

    input_form.submit()

    # Find result report link
    WebDriverWait(driver, 10).until(
        ec.presence_of_element_located((By.CLASS_NAME, 'results-search-content'))
    )

    driver.execute_script("""
                let modal = document.querySelector('#modal');
                if(modal) {
                    modal.remove();
                }
            """)

    result_table = driver.find_element(By.CLASS_NAME, 'results-search-content')
    result_link = result_table.find_elements(By.TAG_NAME, 'a')

    result_link[0].click()

    WebDriverWait(driver, 10).until(
        ec.presence_of_element_located((By.CLASS_NAME, 'header-card-content-date'))
    )

    create_header = driver.find_element(By.CLASS_NAME, 'header-card-content-date')
    create_date = create_header.find_element(By.TAG_NAME, 'p')
    info['create_date'] = create_date.text

    if load_xls:
        WebDriverWait(driver, 10).until(
            ec.presence_of_element_located((By.CLASS_NAME, 'download-reports-wrapper'))
        )

        download_wrapper = driver.find_element(By.CLASS_NAME, 'download-reports-wrapper')
        button_link = download_wrapper.find_element(By.TAG_NAME, 'button')
        button_link.click()

        download_wrapper_report = download_wrapper.find_element(By.CLASS_NAME, 'download-reports')
        # Wait for modal is showing
        time.sleep(1)

        download_years = download_wrapper.find_elements(By.CLASS_NAME, 'button_xs')
        is_year_exists = False
        if year is not None:
            for y in download_years:
                if year == y.text:
                    is_year_exists = True
                    y.click()
                    break
        if year is None or is_year_exists:
            download_wrapper_buttons = download_wrapper_report.find_element(By.CLASS_NAME, 'download-reports-buttons')
            if download_wrapper_buttons is not None:
                button_link = download_wrapper_buttons.find_element(By.CLASS_NAME, 'button_link')
                if button_link is not None:
                    button_link.click()

            button_md = download_wrapper_report.find_element(By.CLASS_NAME, 'button_md')
            button_md.click()

    return info

def open_chrome(download_folder: str = None) -> webdriver.Chrome:
    # Open chrome
    chrome_options = webdriver.ChromeOptions()
    prefs = {"download.default_directory": download_folder}
    chrome_options.add_experimental_option("prefs", prefs)
    driver = webdriver.Chrome(ChromeDriverManager().install(), options=chrome_options)
    return driver


def close_chrome(driver: webdriver.Chrome) -> None:
    # Close Chrome
    driver.close()
    driver.quit()


def main(argv):
    args = parse_args(argv)
    folder = args.folder.strip()
    if folder is None or len(folder) == 0:
        folder = os.path.dirname(os.path.realpath(__file__))
    elif folder[0] != '/':
        folder = os.path.dirname(os.path.realpath(__file__)) + '/' + folder

    wait_ival = args.wait
    separator = args.sep
    noxls = args.noxls
    year = args.year

    # Если выходной папки нет - создать
    if not os.path.exists(folder):
        os.makedirs(folder)

    driver = open_chrome(folder)

    org_info_list = []
    # While not eof read inns from stdin
    for line in sys.stdin:
        inns = line.strip().split(separator)
        if inns is not None and len(inns) > 0:
            inn = inns[0]
            try:
                print(f'{inn}', end='\t')
                info = get_buh_page(driver, inn, not noxls, year)
                org_info_list.append(info)
                print('success')
            except Exception as ex:
                print('fail')
                logger.warning(f'{inn} exception {str(ex)}')
        time.sleep(wait_ival)

    pd.json_normalize(org_info_list).to_csv(f'{folder}_info.csv')
    close_chrome(driver)


#####################################################################
# Testing block (in order to do not install framework - use assert)
TEST_INNS = ['0101009465', '0105030411']


def _test_open_chrome():
    # Test for open chroe
    assert open_chrome() is not None


def _test_one_inn():
    # Test get one inn
    driver = open_chrome()
    get_buh_page(driver, TEST_INNS[0])
    close_chrome(driver)


def _test_inn_list():
    # Test get inns list
    driver = open_chrome()
    for inn in TEST_INNS:
        get_buh_page(driver, inn)
    close_chrome(driver)


def _test():
    try:
        logger.info('Run tests...')
        _test_open_chrome()
        _test_one_inn()
        _test_inn_list()
        logger.info('...complete.')
    except Exception as ex:
        logger.exception(ex)


if 'DEBUG' in os.environ:
    _test()
#####################################################################

if __name__ == '__main__':
    try:
        main(sys.argv)
    except Exception as e:
        logger.error(f'Exception {str(e)}')
