// Types
type FileName = string;
type Language = string;
type Source = string;

interface LanguageData {
  [language: Language]: {
    [source: Source]: FileName[];
  };
}

// Constants
const INPUT_FILE_PATH = 'data/files.txt';
const OUTPUT_FILE_PATH = 'downloads.md';
const LANGUAGE_INDEX = 1;
const SOURCE_START_INDEX = 2;

const GITHUB_RELEASES_URL =
  'https://github.com/StefanVukovic99/leipzig-to-yomitan/releases/latest/download';

const MARKDOWN_HEADER = `# Downloads

The \`occurrence\` and \`rank\` differ in that the occurrence file contains the number of occurrences of each word in the source, while the rank file contains the rank of each word in the source. The rank file is useful for sorting the words by their frequency in the source.

Meanwhile the version of the file without \`occurrence\` or \`rank\` is rank-based but also displays the number of occurrences of each word in the source. **This is the recommended file to use for most purposes.**

Tip: Use \`ctrl + f\` to quickly search for a language.

`;

const getReleaseUrl = (fileName: string): string =>
  `${GITHUB_RELEASES_URL}/${fileName}`;

// Utility functions
const capitalize = (s: string): string =>
  s.charAt(0).toUpperCase() + s.slice(1);

const formatLanguageName = (name: string): string =>
  name
    .replace(/([A-Z])/g, ' $1')
    .trim()
    .split(' ')
    .map(capitalize)
    .join(' ');

const removeOccurrenceAndRank = (s: string): string =>
  s.replace(/(Occurrence|Rank)$/, '').trim();

const determineSource = (parts: string[]): string => {
  if (parts.length > 4) {
    return parts.slice(SOURCE_START_INDEX, -1).join(' ');
  }
  return parts[SOURCE_START_INDEX];
};

const createAnchor = (text: string): string =>
  text
    .toLowerCase()
    .replace(/\s+/g, '-')
    .replace(/[^\w-]+/g, '');

// Main functions
function generateTableOfContents(languages: string[]): string {
  let toc = '# Table of Contents\n\n';
  const groupedLanguages = groupLanguagesByFirstLetter(languages);

  for (const [letter, langs] of Object.entries(groupedLanguages).sort()) {
    toc += `## ${letter}\n\n`;
    toc += langs
      .map((lang) => {
        const anchor = createAnchor(lang);
        return `[${lang}](#${anchor})`;
      })
      .join('&nbsp;&nbsp;&nbsp;');
    toc += '\n\n';
  }

  return toc;
}

function groupLanguagesByFirstLetter(
  languages: string[]
): Record<string, string[]> {
  const grouped: Record<string, string[]> = {};
  for (const lang of languages) {
    const firstLetter = lang[0].toUpperCase();
    if (!grouped[firstLetter]) {
      grouped[firstLetter] = [];
    }
    grouped[firstLetter].push(lang);
  }
  return grouped;
}

function generateMarkdown(data: LanguageData): string {
  let markdown = MARKDOWN_HEADER;
  const sortedLanguages = Object.keys(data).sort();

  // Generate table of contents
  markdown += generateTableOfContents(sortedLanguages);

  for (const language of sortedLanguages) {
    markdown += `# ${language}\n\n`;

    const sortedSources = Object.keys(data[language]).sort();

    for (const source of sortedSources) {
      markdown += `## ${source}\n\n`;

      const sortedFiles = data[language][source].sort();

      for (const file of sortedFiles) {
        const trimmedFile = file.trim();
        const cleanFile = trimmedFile.replace(/\.zip$/, '');
        const url = getReleaseUrl(trimmedFile);
        markdown += `- [${cleanFile}](${url})\n`;
        // markdown += `- ${file}\n`;
      }

      markdown += '\n';
    }
  }

  return markdown;
}

function parseFilenames(filenames: FileName[]): LanguageData {
  const data: LanguageData = {};

  for (const filename of filenames) {
    const parts = filename.split('.');
    const language = formatLanguageName(parts[LANGUAGE_INDEX]);

    let source = determineSource(parts);
    source = removeOccurrenceAndRank(source);

    if (!data[language]) {
      data[language] = {};
    }
    if (!data[language][source]) {
      data[language][source] = [];
    }
    data[language][source].push(filename);
  }

  return data;
}

async function main() {
  try {
    // Read input file
    const inputFile = Bun.file(INPUT_FILE_PATH);
    const input = await inputFile.text();
    const filenames = input.trim().split('\n');

    // Parse filenames and generate markdown
    const data = parseFilenames(filenames);
    const markdown = generateMarkdown(data);

    // Write markdown to file
    await Bun.write(OUTPUT_FILE_PATH, markdown);

    console.log('Markdown file generated successfully!');
  } catch (error) {
    console.error('An error occurred:', error);
  }
}

// Run the script
main();
