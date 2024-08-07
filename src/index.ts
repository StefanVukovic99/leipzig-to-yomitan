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

See the [readme](./readme.md) for more information.

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
  let toc = '';
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
      markdown += `- **${source}**\n\n`;

      const files = data[language][source];
      const recommended = files.find(file => !file.includes('Occurrence') && !file.includes('Rank'));
      const occurrence = files.find(file => file.includes('Occurrence'));
      const rank = files.find(file => file.includes('Rank'));

      const links = [];
      if (recommended) {
        links.push(`[Recommended](${getReleaseUrl(recommended)})`);
      }
      if (occurrence) {
        links.push(`[Occurrence](${getReleaseUrl(occurrence)})`);
      }
      if (rank) {
        links.push(`[Rank](${getReleaseUrl(rank)})`);
      }

      markdown += links.join(' | ') + '\n\n';
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
    data[language][source].push(filename.trim());
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
