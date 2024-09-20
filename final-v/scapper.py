import requests
from neo4j import GraphDatabase
from bs4 import BeautifulSoup
import re

# URL strony, którą będziemy scrapować
url = "https://arxiv.org/"

# Wysłanie żądania HTTP do strony
response = requests.get(url)


# Funkcja formatowania podkategorii: zamienia spacje na myślniki i tytułuje tekst
def format_subcategory(text):
    text_with_single_dash = text.replace(' ', '-')  # Zamienia spacje na pojedyncze myślniki
    capitalized_text = text_with_single_dash.title()  # Wielkie litery na początku każdego słowa
    return capitalized_text


# Funkcja formatowania kategorii: tytułuje tekst (wszystkie litery pierwsze wielkie) i zamienia spacje na myślniki
def format_category(text):
    text_with_single_dash = text.replace(' ', '-')  # Zamienia spacje na myślniki
    capitalized_text = text_with_single_dash.title()  # Zmienia wszystkie słowa na Title Case
    return capitalized_text

# Funkcja sprawdzająca, czy tekst jest jednym z ignorowanych podkategorii
def is_ignored_subcategory(text):
    ignored_words = ["New", "Recent", "Search"]
    return any(word.lower() == text.lower() for word in ignored_words)

# Funkcja do czyszczenia tytułów: usuwanie cyfr, zamienianie wszystkich spacji na myślniki i usuwanie podwójnych myślników
def clean_title(text):
    text = re.sub(r'[^a-zA-Z\s]', '', text)  # Usuwa wszystkie znaki specjalne i cyfry
    text = text.title()  # Zamienia wszystkie słowa na title case (każde słowo z dużej litery)
    text = re.sub(r'\s+', '-', text)  # Zamienia spacje na myślniki
    text = re.sub(r'-+', '-', text)  # Usuwa powtarzające się myślniki
    return text.strip('-')  # Usuwa myślniki na początku i końcu tekstu

# Funkcja do czyszczenia imion autorów: usuwanie cyfr, zamienianie spacji na myślniki i usuwanie podwójnych myślników
def clean_author(text):
    text = re.sub(r'[^a-zA-Z\s]', '', text)  # Usuwa wszystkie znaki specjalne i cyfry
    text = text.title()  # Zmienia każde słowo na title case (pierwsza litera wielka)
    text = re.sub(r'\s+', '-', text)  # Zamienia spacje na myślniki
    text = re.sub(r'-+', '-', text)  # Usuwa powtarzające się myślniki
    return text.strip('-')  # Usuwa myślniki na początku i końcu tekstu


# Sprawdzenie, czy zapytanie zakończyło się sukcesem
if response.status_code == 200:
    # Parsowanie treści strony
    soup = BeautifulSoup(response.text, 'html.parser')

    # Otwórz plik do zapisu
    with open("arxiv_categories.txt", "w", encoding="utf-8") as file:
        # Szukamy nagłówków sekcji głównych (np. Physics, Mathematics)
        sections = soup.find_all("h2")
        iterator = 0;
        for section in sections:
            iterator = iterator + 1
            # Nazwa głównej kategorii (np. Physics, Mathematics)
            main_category = format_category(section.get_text())  # Zmieniamy nazwę kategorii na Title Case

            # Zapisz główną kategorię w pliku w formacie: Nazwa-Kategorii is category
            file.write(f"Merge (P{iterator}:Category {{title: \"{main_category}\"}})\n")

            # Znalezienie listy podkategorii pod daną kategorią
            ul_tag = section.find_next_sibling("ul")
            if ul_tag:
                mini_iterator = 0
                # Przejście przez każdą kategorię w ramach listy
                for li_tag in ul_tag.find_all("li"):
                    # Znalezienie linków i podkategorii
                    main_link = li_tag.find("a", id=lambda x: x and "main-" in x)
                    if main_link:
                        # Zapisanie głównej podkategorii w formacie: Podkategoria is-subcategory-of Kategoria
                        main_link_text = format_subcategory(main_link.get_text())
                        file.write(f"Merge (P{iterator}{mini_iterator}:SubCategory {{title:\"{main_link_text}\"}})\n")
                        file.write(f"Merge (P{iterator}{mini_iterator})-[:isSubCategoryOf]->(P{iterator})\n")
                        mini_iterator = mini_iterator + 1

                    sub_links = li_tag.find_all("a", id=lambda x: x and "main-" not in x)
                    if sub_links:
                        for sub_link in sub_links:
                            # Sprawdzenie, czy podkategoria nie jest jedną z ignorowanych
                            if not is_ignored_subcategory(sub_link.get_text()):
                                # Zapisanie każdej podkategorii w formacie: Podkategoria is-subcategory-of Główna-Podkategoria
                                sub_link_text = format_subcategory(sub_link.get_text())
                                file.write(f"Merge (P{iterator}{mini_iterator}:SubCategory {{title:\"{sub_link_text}\"}})\n")
                                file.write(f"Merge (P{iterator}{mini_iterator})-[:isSubCategoryOf]->(P{iterator})\n")
                                mini_iterator = mini_iterator + 1
else:
    print("Nie udało się pobrać strony.")

with open("arxiv_categories.txt", "r", encoding="utf-8") as file:
    driver = GraphDatabase.driver('neo4j://localhost:7687',
                                  auth=('neo4j', '12345678'))
    driver.session().run(file.read())
    driver.close()

print("Scraping kategorii zakończony, dane zapisane do arxiv_categories.txt.")
print("Dalsze scrapowanie:")


def scrape_new_papers(category_name, new_papers_url):
    response = requests.get(new_papers_url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')

        # Znajdujemy wszystkie artykuły na stronie "new"
        papers = soup.find_all('dd')

        iterator = 0
        for paper in papers:
            file = open("arxiv_papers.txt", "w", encoding="utf-8")
            iterator += 1
            # Pobieramy tytuł artykułu
            title_tag = paper.find('div', class_='list-title')
            if title_tag:
                title = title_tag.get_text(strip=True).replace('Title:', '').strip()
                title = title.replace('\n', '').replace('\r', '')
                cleaned_title = clean_title(title)  # Czyścimy tytuł

                # Pobieramy autora(-ów) artykułu
                author_tag = paper.find('div', class_='list-authors')
                if author_tag:
                    authors = [clean_author(a.get_text()) for a in author_tag.find_all('a')]
                    
                    file.write(f"Merge (:Category {{title:\"{category_name}\"}})\n")
                    file.write(f"Merge (P{iterator}:Paper {{title:\"{cleaned_title}\"}})\n")
                    file.write(f"With P{iterator}\n")
                    file.write(f"Match (C{iterator}:Category {{title:\"{category_name}\"}})\n")
                    file.write(f"Merge (P{iterator})-[:isPaperIn]->(C{iterator})\n")

                    author_iterator = 0
                    for author in authors:
                        author_iterator += 1
                        file.write(f"Merge (A{iterator}A{author_iterator}:Author {{name:\"{author}\"}})\n")
                        file.write(f"Merge (P{iterator})-[:isWrittenBy]->(A{iterator}A{author_iterator})\n")
            file.close()
            with open("arxiv_papers.txt", "r", encoding="utf-8") as file:
                driver = GraphDatabase.driver('neo4j://localhost:7687',
                                                      auth=('neo4j', '12345678'))
                driver.session().run(file.read())

                driver.close()


# Wysłanie żądania HTTP do głównej strony
response = requests.get(url)
# Sprawdzenie, czy zapytanie zakończyło się sukcesem
if response.status_code == 200:
    soup = BeautifulSoup(response.text, 'html.parser')
    # Otwórz plik do zapisu
    sections = soup.find_all("h2")

    for section in sections:
        main_category = format_category(section.get_text())  # Zmieniamy nazwę kategorii na małe litery

        ul_tag = section.find_next_sibling("ul")
        if ul_tag:
            for li_tag in ul_tag.find_all("li"):
                main_link = li_tag.find("a", id=lambda x: x and "main-" in x)

                if main_link:
                    main_link_text = format_subcategory(main_link.get_text())
                    new_papers_url = url + li_tag.find('a', id=lambda x: x and "new" in x)['href']

                    scrape_new_papers(main_link_text, new_papers_url)

else:
    print("Nie udało się pobrać strony.")

print("Scraping zakończony, dane zapisane do arxiv_papers.txt.")