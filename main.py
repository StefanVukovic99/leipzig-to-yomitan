import argparse
import json
from collections import defaultdict
import re
import zipfile
from bs4 import BeautifulSoup
import requests
from iso639 import languages
import os
import tarfile
import tempfile
import shutil
from datetime import datetime
import country_converter as coco

# get current date as calver
calver = datetime.now().strftime("%Y.%m.%d")

PATTERNS = {
    'spa': re.compile(r'^[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ ]+$'),
}

def get_info_from_filename(filename):
    parts = filename.split('_')
    if(len(parts) < 3 or len(parts) > 4):
        print(f"Invalid filename: {filename}")
        return None, None, None, None
    if len(parts) == 3:
        lang, source, year = parts
        size = '0'
    if len(parts) == 4:
        lang, source, year, size = parts
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
        
def write_index_json(title):
    with open('index.json', 'w', encoding='utf8') as fd:
        json.dump({
            "title": title,
            "revision": calver,
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
        if lang is None:
            print(f"Invalid filename: {file}")
            continue
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

def get_download_anchors(lang):
    resp = requests.get(f'https://wortschatz.uni-leipzig.de/en/download/{lang}')
    parsed_html = BeautifulSoup(resp.content)
    return parsed_html.body.select('a.link_corpora_download')

def get_download_urls(lang):
    download_links = get_download_anchors(lang)

    options_tree = build_options_tree(download_links)
    filtered_options_tree = filter_options_tree(options_tree)
    files = get_files_from_tree(filtered_options_tree)
    return files

def get_files_from_tree(filtered_options_tree):
    files = []
    for lang, lang_options in filtered_options_tree.items():
        for source, source_options in lang_options.items():
            for year, size in source_options.items():
                filename = f"{lang}_{source}_{year}"
                size = convert_int_to_shorthand(size)
                if size != '0':
                    filename += f'_{size}'
                filename += '.tar.gz'
                files.append(f'https://downloads.wortschatz-leipzig.de/corpora/{filename}')
    return files

def get_lang_and_country(lang):
    parts = lang.split('-')
    country = ''
    if(len(parts) == 1):
        return lang, country
    if(len(parts) == 2):
        lang, country = parts
        converted_country = coco.convert(names=country, to="name")
        if converted_country == 'not found':
            converted_country = country
        return lang, converted_country
    if(len(parts) == 3):
        lang, part2, part3 = parts
        converted_country = coco.convert(names=part2, to="name")
        if converted_country != 'not found':
            return lang, f'{converted_country}-{part3}'
        
        converted_country = coco.convert(names=part3, to="name")
        if converted_country == 'not found':
            return lang, f'{part2}-{part3}'
        else:
            return lang, f'{converted_country}-{part2}'
    print(f"Invalid language: {lang}")
    return None, None
    
def processFile(requested_lang, input_file):
    print(f"Processing {input_file.name}...")
    filename = os.path.basename(input_file.name)
    file_lang, source, year, size = get_info_from_filename(filename)
    file_lang, country = get_lang_and_country(file_lang)
    if country:
        country = f" ({country})"
    try:
        file_lang_name = languages.get(part3=file_lang).name
    except KeyError:
        file_lang_name = file_lang

    cleaned_data = defaultdict(int)
    rows = []
    
    for line in input_file:
        rank, word, occurrence = get_line_data(line)
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

    title = f"Leipzig {file_lang_name}{country} {source.title()} (Rank)"
    write_index_json(title)
    create_zip(f"{title}.zip")

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

    title = f"Leipzig {file_lang_name}{country} {source.title()} (Occurrence)"
    write_index_json(title)
    create_zip(f"{title}.zip")

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

    title = f"Leipzig {file_lang_name}{country} {source.title()}"
    write_index_json(title)
    create_zip(f"{title}.zip")

def get_line_data(line):
    parts = line.strip().split('\t')
    if len(parts) == 3:
        return parts
    elif len(parts) == 4:
        return parts[0], parts[1], parts[3]
    else:
        print(f"Invalid line: {line}")
        return None, None, None
    
def download_file(url, output_path):
    response = requests.get(url, stream=True)
    response.raise_for_status()
    with open(output_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

def extract_tarball(tar_path, extract_path):
    with tarfile.open(tar_path, 'r:gz') as tar:
        tar.extractall(path=extract_path)

def find_words_file(extract_path):
    for root, dirs, files in os.walk(extract_path):
        for file in files:
            if file.endswith('-words.txt'):
                return os.path.join(root, file)
    return None

def process_downloaded_file(file_path, lang):
    extract_dir = tempfile.mkdtemp()
    try:
        extract_tarball(file_path, extract_dir)
        words_file = find_words_file(extract_dir)
        if words_file:
            with open(words_file, 'r', encoding='utf-8') as f:
                processFile(lang, f)
        else:
            print(f"No -words.txt file found in {file_path}")
    finally:
        shutil.rmtree(extract_dir)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('lang', type=str, help='Language code (e.g., "spa" for Spanish)')
    args = parser.parse_args()

    download_urls = get_download_urls(args.lang)
    if (len(download_urls) == 0):
        print("No files found for the specified language.")
        exit(1)

    for url in download_urls:
        file_name = url.split('/')[-1]
        print(f"Downloading {file_name}...")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.tar.gz') as temp_file:
            download_file(url, temp_file.name)
            print(f"Downloaded {file_name}")
            
            print(f"Processing {file_name}...")
            process_downloaded_file(temp_file.name, args.lang)
            print(f"Processed {file_name}")
        
        os.unlink(temp_file.name)

    print("All files processed successfully.")