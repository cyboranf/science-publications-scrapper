from typing import List, Tuple
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
import requests
import json
import re


def clean_string(raw: str) -> str:
    """
    Cleans string of any excessive spaces

    :param raw: raw string to clean
    :return: String without excessive spaces
    """
    raw = raw.lower().lstrip().rstrip()

    if len(raw) <= 1:
        return raw.upper()

    clean_text = re.sub(r'[-/().,!?;:^*%+=~<>\"\']+', ' ', raw)
    clean_text = re.sub(r'\d+', '', clean_text)
    clean_text = re.sub(r'[^\W\d_a-zA-Z]', '', clean_text)
    clean_text = re.sub(r'\s+', ' ', clean_text)
    splitted = clean_text.split(' ')
    connected = '-'.join([value[0].upper() + value[1::] for value in splitted if len(value) > 1])
    clean_text2 = re.sub(r'[♭]', 'flat', connected)
    clean_text2 = re.sub(r'[♯]', 'sharp', clean_text2)

    if clean_text2 == "":
        return ""

    result = clean_text2[0].upper() + clean_text2[1::]

    return result


def year_to_text(raw: str) -> str:
    result = ""

    for part in raw:
        single = ""
        match part:
            case '0':
                single = "-Zero"
            case '1':
                single = "-One"
            case '2':
                single = "-Two"
            case '3':
                single = "-Three"
            case '4':
                single = "-Four"
            case '5':
                single = "-Five"
            case '6':
                single = "-Six"
            case '7':
                single = "-Seven"
            case '8':
                single = "-Eight"
            case '9':
                single = "-Nine"
        result += single

    return result.lstrip('-')  # Remove the leading hyphen




def process() -> None:

    page = 0
    total_counter = 0

    stopper = -1  # quantity of pages to be scrapped -1 for all pages available
    while stopper != 0:
        print(f"Scrapping page {page+1}")
        prompts = []
        links = []

        # accessing composers page
        target_url = f'https://arxiv.org/search/?query=%22quantum+gravity%22&searchtype=all&abstracts=show&order=announced_date_first&size=50&start={page*50}'

        # try:
        # accessing url and parsing html
        response = requests.get(target_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        divs = soup.find_all('li', class_='arxiv-result')

        if len(divs) < 50:
            break

        total_prompt = ""

        for div in divs:
            title = clean_string(div.find('p', class_='title is-5 mathjax').get_text())

            if title == "":
                continue

            authors_div = div.find('p', class_="authors")
            authors_list = authors_div.find_all('a')
            authors = []

            for author in authors_list:
                authors.append(clean_string(author.get_text()))

            date_div = div.find('p', class_="is-size-7")
            date_text = date_div.get_text().split(";")[0]

            date_split = date_text.split(" ")
            date_year = year_to_text(date_split[3])

            prompt = f"{title} is an article.\n"

            for author in authors:
                prompt += f"{author} is an author.\n"
                prompt += f"{title} is-written-by {author}.\n"

            prompt += f"{date_year} is year.\n"
            prompt += f"{title} is-written-in {date_year}.\n"

            total_prompt += prompt + "\n"

        file = open("prompts-fluent.txt", "a+", encoding="utf-8")

        file.write(total_prompt)

        # except Exception as e:
        #     print(e)

        stopper -= 1
        page += 1
        print(f"finished scrapping page {page}")

    print(f'\n\n Scrapping completed!!\n\n')


if __name__ == "__main__":
    process()
