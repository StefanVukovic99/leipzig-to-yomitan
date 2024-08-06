import argparse
import json
from collections import defaultdict
import re
import zipfile


SPANISH_PATTERN = re.compile(r'^[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ ]+$')


def write_index_json(title, year):
    with open('index.json', 'w', encoding='utf8') as fd:
        json.dump({
            "title": title,
            "revision": year,
            "format": 3
        }, fd, indent=4)

def create_zip(file):
    # Create a zip consisting of index.json and term_meta_bank_1.json
    with zipfile.ZipFile(file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write('index.json')
        zipf.write('term_meta_bank_1.json')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('input_file', type=argparse.FileType('r'), help='CSV file to read')
    parser.add_argument('--output', type=str, help='Output file')
    args = parser.parse_args()



    with args.input_file as input_file:
        # Assume files are in this format: spa_news_2023_10K-words.txt
        lang, source, year, size = args.input_file.name.split('-')[0].split('_')
        cleaned_data = defaultdict(int)
        rows = []
        for line in input_file.readlines():
            rank, word, occurrence = line.strip().split('\t')
            rows.append([rank, word, occurrence])
            if bool(SPANISH_PATTERN.match(word)):
                cleaned_data[word.lower()] += int(occurrence)

        output = sorted(([word, occurence] for word, occurence in cleaned_data.items()), key=lambda x: x[1], reverse=True)

        # Rank dict
        with open(f"term_meta_bank_1.json", 'w', encoding='utf8') as fd:
            rank_output = [
                [
                    word,
                    "freq",
                    {"value": rank, "displayValue": f"{rank}"}
                ] for rank, (word, _) in enumerate(output, start=1)
            ]
            json.dump(rank_output, fd, indent=4, ensure_ascii=False)

        write_index_json(f"{source.title()} (Rank)", year)
        create_zip(f"{source.title()}_{year}_{size}_rank.zip")

        # Occurrence dict
        with open(f"term_meta_bank_1.json", 'w', encoding='utf8') as fd:
            rank_output = [
                [
                    word,
                    "freq",
                    {"value": rank, "displayValue": f"{occurrence}"}
                ] for rank, (word, occurrence) in enumerate(output, start=1)
            ]
            json.dump(rank_output, fd, indent=4, ensure_ascii=False)

        write_index_json(f"{source.title()} (Occurrence)", year)
        create_zip(f"{source.title()}_{year}_{size}_occurence.zip")

        # Both dict
        with open(f"term_meta_bank_1.json", 'w', encoding='utf8') as fd:
            rank_output = [
                [
                    word,
                    "freq",
                    {"value": rank, "displayValue": f"{rank} ({occurrence})"}
                ] for rank, (word, occurrence) in enumerate(output, start=1)
            ]
            json.dump(rank_output, fd, indent=4, ensure_ascii=False)

        write_index_json(f"{source.title()}", year)
        create_zip(f"{source.title()}_{year}_{size}_both.zip")