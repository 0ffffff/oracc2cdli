import os
import sys
import argparse

# Add the project root to sys.path so we can import from src
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.append(project_root)

from src.utils import convert_line_cdli_to_oracc, load_reverse_character_mapping

def convert_file(args, project_root):
    if args.mapping:
        mapping_path = args.mapping
    else:
        mapping_path = os.path.join(project_root, 'data', 'reference', 'ATF_Character_Conventions.csv')

    # 1. Load mapping
    if not os.path.exists(mapping_path):
        print(f"Error: Mapping file not found at {mapping_path}")
        sys.exit(1)
        
    print(f"Loading mapping from {mapping_path}...")
    mapping = load_reverse_character_mapping(mapping_path)

    # 2. Read input
    if not os.path.exists(args.input):
        print(f"Error: Input file {args.input} not found.")
        sys.exit(1)

    print(f"Reading from {args.input}...")
    with open(args.input, 'r', encoding='utf-8') as f:
        lines = f.read().splitlines()

    # 3. Convert
    print(f"Converting {len(lines)} lines...")
    converted = [
        convert_line_cdli_to_oracc(line, mapping, has_label=args.has_label)
        for line in lines
    ]

    # 4. Write output
    print(f"Writing output to {args.output}...")
    with open(args.output, 'w', encoding='utf-8') as f:
        for line in converted:
            f.write(line + '\n')
    print("Done.")

def clean_file(args):
    """
    Basic cleaning of input file.
    """
    if not os.path.exists(args.input):
        print(f"Error: Input file {args.input} not found.")
        sys.exit(1)

    print(f"Cleaning {args.input}...")
    with open(args.input, 'r', encoding='utf-8') as f:
        lines = f.read().splitlines()

    cleaned = [line.strip() for line in lines if line.strip()]

    print(f"Writing cleaned output to {args.output}...")
    with open(args.output, 'w', encoding='utf-8') as f:
        for line in cleaned:
            f.write(line + '\n')
    print("Done.")

def main():
    parser = argparse.ArgumentParser(description='Convert CDLI transliteration to ORACC format.')
    subparsers = parser.add_subparsers(dest='command', help='Subcommands')

    # Convert subcommand
    parser_convert = subparsers.add_parser('convert', help='Convert files')
    parser_convert.add_argument('input', help='Path to the input CDLI file')
    parser_convert.add_argument('output', help='Path to the output ORACC file')
    parser_convert.add_argument('--has-label', action='store_true', 
                        help='Indicate that lines start with an ID/label (e.g. P123:obv.1)')
    parser_convert.add_argument('--mapping', default=None,
                        help='Path to the character convention mapping CSV')
    
    # Clean subcommand
    parser_clean = subparsers.add_parser('clean', help='Clean input file')
    parser_clean.add_argument('input', help='Path to the input file')
    parser_clean.add_argument('output', help='Path to the output file')

    args = parser.parse_args()

    if args.command == 'convert':
        convert_file(args, project_root)
    elif args.command == 'clean':
        clean_file(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
