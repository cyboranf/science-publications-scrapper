from typing import List, Tuple
from bs4 import BeautifulSoup
from neo4j import GraphDatabase
from concurrent.futures import ThreadPoolExecutor
import requests
import json
import re


def clean_string(raw: str) -> str:
    clean_text = re.sub(r'\s+', ' ', raw).lstrip().rstrip()
    clean_text = re.sub(r'[\\$/.,!?;:^*%+=~<>\"\']+', '', clean_text)
    return clean_text


def process() -> None:

    driver = GraphDatabase.driver('neo4j://localhost:7687',
                                  auth=('neo4j', '1234'))
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
    driver.close()

    page = 0
    total_counter = 0

    stopper = -1  # quantity of pages to be scrapped -1 for all pages available
    while stopper != 0:
        print(f"Scrapping page {page+1}")
        prompts = []
        links = []

        # accessing composers page
        target_url = f'https://arxiv.org/search/?query=%22quantum+gravity%22&searchtype=all&abstracts=show&order=announced_date_first&size=50&start={page*50}'

        try:
            # accessing url and parsing html
            response = requests.get(target_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            divs = soup.find_all('li', class_='arxiv-result')

            if len(divs) < 50:
                break

            prompt_list = []

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
                date_text = clean_string(date_div.get_text().split(";")[0])

                date_split = date_text.split(" ")
                date_day = date_split[1]
                date_month = date_split[2]
                date_year = date_split[3]

                prompt = f"MERGE (A:Article {{title:\"{title}\"}})\n"

                iterator = 0
                for author in authors:
                    prompt += f"MERGE (P{iterator}:Author {{title:\"{author}\"}})\n"
                    prompt += f"Merge (A)-[:WritedBy]->(P{iterator})\n"
                    iterator +=1

                prompt += f"MERGE (Y:Year {{number:\"{date_year}\"}})\n"
                prompt += f"Merge (A)-[:WritedIn {{month:\"{date_month}\", day:\"{date_day}\"}}]->(Y)\n"

                print()
                prompt_list.append(prompt)

            driver = GraphDatabase.driver('neo4j://localhost:7687',
                                          auth=('neo4j', '1234'))
            for pr in prompt_list:

                try:
                    driver.session().run(pr)
                except ValueError as e:
                    print(e)
                    continue

            driver.close()

        except Exception as e:
            print(e)

        stopper -= 1
        page += 1
        print(f"finished scrapping page {page}")


    print(f'\n\n Scrapping completed!!\n\n')


if __name__ == "__main__":
    process()
