import requests
from neo4j import GraphDatabase
from bs4 import BeautifulSoup

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
                mini_iterator = 0;
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

print("Scraping zakończony, dane zapisane do arxiv_categories.txt.")
with open("arxiv_categories.txt", "r", encoding="utf-8") as file:
    driver = GraphDatabase.driver('neo4j://localhost:7687',
                                  auth=('neo4j', '12345678'))
    driver.session().run(file.read())
    driver.close()
