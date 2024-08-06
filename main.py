import argparse
import json
from collections import defaultdict
import re
import zipfile
from bs4 import BeautifulSoup
import requests
from iso639 import languages
from collections import defaultdict

# load languages.json 
PATTERNS = {
    'spa': re.compile(r'^[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ ]+$'),
}

def get_info_from_filename(filename):
    lang, source, year, size = filename.split('_')
    return lang, source, year, size

def convert_shorthand_to_int(value):
    value = value.upper().strip() 
    if value.endswith('K'):
        return int(float(value[:-1]) * 1_000)
    elif value.endswith('M'):
        return int(float(value[:-1]) * 1_000_000)
    else:
        return int(value)
    
def convert_int_to_shorthand(value):
    if value < 1_000:
        return str(value)
    elif value < 1_000_000:
        return f"{value // 1_000}K"
    else:
        return f"{value // 1_000_000}M"
        
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

def build_options_tree(download_links):
    options_tree = defaultdict(lambda: defaultdict(dict))
    
    for link in download_links:
        file = link.get('data-corpora-file')
        if not file.endswith('.tar.gz'):
            print(f"File not tarball: {file}")
            continue
        
        file = file[:-7]
        lang, source, year, size = get_info_from_filename(file)
        size_int = convert_shorthand_to_int(size)
        
        options_tree[lang][source][year] = max(options_tree[lang][source].get(year, 0), size_int)

    return options_tree

def filter_options_tree(options_tree):
    filtered_tree = {}
    
    for lang, lang_options in options_tree.items():
        filtered_tree[lang] = {}
        
        for source, source_options in lang_options.items():
            max_size = max(source_options.values())
            newest_year = max(year for year, size in source_options.items() if size == max_size)
            
            filtered_tree[lang][source] = {newest_year: max_size}
    
    return filtered_tree

def fetch(lang):
    lang_name = languages.get(part3=lang).name
    resp = requests.get(f'https://wortschatz.uni-leipzig.de/en/download/{lang_name}')
    if(resp.status_code == 404): exit('404 Not Found')

    parsed_html = BeautifulSoup(resp.content)

    download_links = parsed_html.body.select('a.link_corpora_download')

    options_tree = build_options_tree(download_links)
    filtered_options_tree = filter_options_tree(options_tree)
    files = get_files_from_tree(filtered_options_tree)
    return files

def get_files_from_tree(filtered_options_tree):
    files = []
    for lang, lang_options in filtered_options_tree.items():
        for source, source_options in lang_options.items():
            for year, size in source_options.items():
                filename = f"{lang}_{source}_{year}_{convert_int_to_shorthand(size)}.tar.gz"
                files.append(f'https://downloads.wortschatz-leipzig.de/corpora/{filename}')
    return files

def processFile(write_index_json, create_zip, args):
    with args.input_file as input_file:
        # Assume files are in this format: spa_news_2023_10K-words.txt
        lang, source, year, size = args.input_file.name.split('-')[0].split('_')
        cleaned_data = defaultdict(int)
        rows = []
        for line in input_file.readlines():
            rank, word, occurrence = line.strip().split('\t')
            rows.append([rank, word, occurrence])
            if args.lang in PATTERNS and not PATTERNS[args.lang].match(word):
                continue
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

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('lang', type=str, help='Language of the input file')
    parser.add_argument('input_file', type=argparse.FileType('r'), help='CSV file to read')
    parser.add_argument('--output', type=str, help='Output file')
    args = parser.parse_args()
    download_urls = fetch(args.lang)
    
    for url in download_urls:
        # Download the file
    
        processFile(write_index_json, create_zip, args)