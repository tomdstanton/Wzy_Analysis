#!/usr/bin/env python3

from typing import TextIO, Generator
from pathlib import Path
from itertools import chain
from json import dumps
from argparse import ArgumentParser


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('fastas', type=Path, help='FASTA files', nargs='+')
    parser.add_argument('-o', '--outdir', type=Path, default=Path('.'))
    return parser.parse_args()


def parse_fasta(handle: TextIO) -> Generator[tuple[str, str], None, None]:
    header, seq = '', []
    for line in chain(handle, ['>']):
        if not (line := line.strip()):
            continue
        if line.startswith('>'):
            if header and seq:
                yield header.strip().split()[0], ''.join(seq)
            header, seq = line[1:], []
        else:
            seq.append(line)


def generate_seq_json(record: tuple[str, str], path: Path):
    name, seq = record
    json = {
      "name": name,
      "sequences": [{"protein": {"id": "A", "sequence": seq}}],
      "modelSeeds": [1],
      "dialect": "alphafold3",
      "version": 1
    }
    outfile = path / f"{name}.json"
    return outfile.write_text(dumps(json))


def main():
    args = parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)
    for fasta in args.fastas:
        for record in parse_fasta(fasta.open()):
            generate_seq_json(record, args.outdir)


if __name__ == '__main__':
   main()
