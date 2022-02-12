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
    return parser.parse_args(argv[1:])


def get_buh_page(driver: webdriver.Chrome, inn: str) -> None:
    """
    Получение страницы бух отчетности по ИНН
    :param driver: chrome driver
    :param inn: ИНН
    :return: None
    """
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
        ec.presence_of_element_located((By.CLASS_NAME, 'download-reports-wrapper'))
    )

    download_wrapper = driver.find_element(By.CLASS_NAME, 'download-reports-wrapper')
    button_link = download_wrapper.find_element(By.TAG_NAME, 'button')
    button_link.click()

    download_wrapper_report = download_wrapper.find_element(By.CLASS_NAME, 'download-reports')
    # Wait for modal is showing
    time.sleep(1)

    download_wrapper_buttons = download_wrapper_report.find_element(By.CLASS_NAME, 'download-reports-buttons')
    if download_wrapper_buttons is not None:
        button_link = download_wrapper_buttons.find_element(By.CLASS_NAME, 'button_link')
        if button_link is not None:
            button_link.click()

    button_md = download_wrapper_report.find_element(By.CLASS_NAME, 'button_md')
    button_md.click()


def open_chrom(download_folder: str = None) -> webdriver.Chrome:
    # Open chrome
    chrome_options = webdriver.ChromeOptions()
    prefs = {"download.default_directory": download_folder}
    chrome_options.add_experimental_option("prefs", prefs)
    driver = webdriver.Chrome(ChromeDriverManager().install(), options=chrome_options)
    return driver


def close_chrom(driver: webdriver.Chrome) -> None:
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

    # Если выходной папки нет - создать
    if not os.path.exists(folder):
        os.makedirs(folder)

    driver = open_chrom(folder)

    # While not eof read inns from stdin
    for line in sys.stdin:
        inns = line.strip().split(separator)
        if inns is not None and len(inns) > 0:
            inn = inns[0]
            try:
                print(f'{inn}', end='\t')
                get_buh_page(driver, inn)
                print('success')
            except Exception as ex:
                print('fail')
                logger.warning(f'{inn} exception {str(ex)}')
        time.sleep(wait_ival)

    close_chrom(driver)


#####################################################################
# Testing block (in order to do not install framework - use assert)
TEST_INNS = ['1435338862', '7801683256']


def test01():
    # Test for open chroe
    assert open_chrom() is not None


def test02():
    # Test get one inn
    driver = open_chrom()
    get_buh_page(driver, TEST_INNS[0])
    close_chrom(driver)


def test03():
    # Test get inns list
    driver = open_chrom()
    for inn in TEST_INNS:
        get_buh_page(driver, inn)
    close_chrom(driver)


def test():
    try:
        logger.info('Run tests...')
        test01()
        test02()
        test03()
        logger.info('...complete.')
    except Exception as ex:
        logger.exception(ex)


if 'DEBUG' in os.environ:
    test()
#####################################################################

if __name__ == '__main__':
    try:
        main(sys.argv)
    except Exception as e:
        logger.error(f'Exception {str(e)}')
