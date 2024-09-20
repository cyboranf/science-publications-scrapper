import requests
from neo4j import GraphDatabase
from bs4 import BeautifulSoup
import re

# URL główny arXiv
base_url = "https://arxiv.org"

# Funkcja formatowania podkategorii: zamienia spacje na myślniki i tytułuje tekst
def format_subcategory(text):
    text_with_single_dash = text.replace(' ', '-')  # Zamienia spacje na pojedyncze myślniki
    capitalized_text = text_with_single_dash.title()  # Wielkie litery na początku każdego słowa
    return capitalized_text

# Funkcja formatowania kategorii: zamienia na małe litery i myślniki
def format_category(text):
    text_with_single_dash = text.replace(' ', '-')  # Zamienia spacje na myślniki
    lowercase_text = text_with_single_dash.lower()  # Zamienia na małe litery
    return lowercase_text

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

# Funkcja do pobierania artykułów z sekcji "new" danej podkategorii
def scrape_new_papers(category_name, new_papers_url ):
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
response = requests.get(base_url)
# Sprawdzenie, czy zapytanie zakończyło się sukcesem
if response.status_code == 200:
    # Parsowanie treści stronmatch (n:Node {title:"test"})  
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
                    new_papers_url = base_url + li_tag.find('a', id=lambda x: x and "new" in x)['href']


                        # Wchodzimy na stronę "new" danej podkategorii i pobieramy tytuły oraz autorów
                    scrape_new_papers(main_link_text, new_papers_url)

                    
else:
    print("Nie udało się pobrać strony.")

print("Scraping zakończony, dane zapisane do arxiv_papers.txt.")