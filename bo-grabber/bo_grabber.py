import sys
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

import os
import time
import argparse

BASE_URL = "https://bo.nalog.ru/"
OUTPUT_DIR = '/Users/sand/DataspellProjects/finadvisor_git/data/bo.nalog.ru/'
WAIT_IVAL = 5

def parse_args(argv):
    """
    Parse command-line args.
    """
    parser = argparse.ArgumentParser(
        prog = 'bo_grabber',
        formatter_class = argparse.MetavarTypeHelpFormatter)
    parser.add_argument('--out', metavar='OUTPUT_DIR', type=str, nargs=1, help='Output folder for inns')
    parser.add_argument('--wait', metavar='WAIT_IVAL', type=int, nargs='?', help='Wait interval between queries')
    print(parser.parse_args('X -- Y'.split()))
    return parser.parse_args(argv[1:])


def get_buh_page(driver: webdriver.Chrome, inn: str) -> None:
    '''
    Получение страницы бух отчетности по ИНН
    :param driver: chrome driver
    :param inn: ИНН
    :return: None
    '''
    # Load base page
    driver.get(BASE_URL)

    # Find inn input field
    WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.CLASS_NAME, 'input-search'))
    )

    input_form = driver.find_element(By.CLASS_NAME, 'input-search')
    input_field = input_form.find_element(By.ID, 'search')
    input_field.clear()
    input_field.send_keys(inn)

    input_form.submit()

    # Find result report link
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, 'results-search-content'))
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
        EC.presence_of_element_located((By.CLASS_NAME, 'download-reports-wrapper'))
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


def main(argv):
    # inns = ['1435338862', '7801683256']
    args = parse_args(argv)

    print(OUTPUT_DIR)

    # Open chrome
    chrome_options = webdriver.ChromeOptions()
    prefs = {"download.default_directory": OUTPUT_DIR}
    chrome_options.add_experimental_option("prefs", prefs)
    driver = webdriver.Chrome(ChromeDriverManager().install(), options=chrome_options)

    # Если выходной папки нет - создать
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # While not eof read inns from stdin
    for line in sys.stdin:
        inn = line.strip()
        try:
            print(f'{inn}\t', end='')
            get_buh_page(driver, inn)
            print('success')
        except Exception as e:
            print('fail', file=sys.stdout)
            print(f'{inn} exception {str(e)}', file=sys.stderr)
        time.sleep(WAIT_IVAL)

    # Close Chrome
    driver.close()
    driver.quit()


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    try:
        main(sys.argv)
    except Exception as e:
        print('Exception:', e)

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
