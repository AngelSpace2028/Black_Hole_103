import os
import sys
import zlib
import random
import struct
import logging

# Attempt to import the paq module
try:
    import paq
except ImportError:
    print("Error: 'paq' module is not installed or accessible.")
    sys.exit(1)

# === Dictionary file list ===
DICTIONARY_FILES = [
    "1.txt",
    "eng_news_2005_1M-sentences.txt",
    "eng_news_2005_1M-words.txt",
    "eng_news_2005_1M-sources.txt",
    "eng_news_2005_1M-co_n.txt",
    "eng_news_2005_1M-co_s.txt",
    "eng_news_2005_1M-inv_so.txt",
    "eng_news_2005_1M-meta.txt",
    "Dictionary.txt",
    "the-complete-reference-html-css-fifth-edition.txt",
    "words.txt.paq",
    "lines.txt.paq",
    "sentence.txt.paq"
]

# === Smart Compressor ===
class SmartCompressor:
    def __init__(self):
        self.dictionaries = self.load_dictionaries()

    def load_dictionaries(self):
        data = []
        for filename in DICTIONARY_FILES:
            if os.path.exists(filename):
                try:
                    with open(filename, "r", encoding="utf-8", errors="ignore") as f:
                        data.append(f.read())
                except Exception as e:
                    logging.warning(f"Could not read {filename}: {e}")
            else:
                logging.warning(f"Missing: {filename}")
        return data

    def huffman_compress(self, data):
        return zlib.compress(data)

    def huffman_decompress(self, data):
        return zlib.decompress(data)

    def reversible_transform(self, data):
        return bytes([b ^ 0xAA for b in data])

    def reverse_reversible_transform(self, data):
        return self.reversible_transform(data)

    def compress(self, input_file, output_file):
        with open(input_file, "rb") as f:
            original_data = f.read()
        transformed = self.reversible_transform(original_data)
        compressed = self.huffman_compress(transformed)
        if len(compressed) < len(original_data):
            with open(output_file, "wb") as f:
                f.write(compressed)
            print(f"Smart compression successful. Saved to {output_file}")
        else:
            print("Compression not efficient. File not saved.")

    def decompress(self, input_file, output_file):
        with open(input_file, "rb") as f:
            compressed_data = f.read()
        decompressed = self.huffman_decompress(compressed_data)
        original = self.reverse_reversible_transform(decompressed)
        with open(output_file, "wb") as f:
            f.write(original)
        print(f"Smart decompression complete. Saved to {output_file}")

# === XOR + PAQ Compressor ===
def transform_with_pattern(data, chunk_size=4):
    return bytearray([b ^ 0xFF for b in data])

def is_prime(n):
    if n < 2: return False
    if n == 2: return True
    if n % 2 == 0: return False
    for i in range(3, int(n**0.5)+1, 2):
        if n % i == 0: return False
    return True

def find_nearest_prime_around(n):
    offset = 0
    while True:
        if is_prime(n - offset): return n - offset
        if is_prime(n + offset): return n + offset
        offset += 1

def encode_with_paq():
    input_file = input("Enter input file: ")
    output_file = input("Enter output base name (.enc will be added): ")
    if not os.path.exists(input_file):
        print("Input file not found.")
        return
    with open(input_file, 'rb') as f:
        original = f.read()
    transformed = transform_with_pattern(original)
    compressed = paq.compress(bytes(transformed))
    with open(output_file + ".enc", 'wb') as f:
        f.write(compressed)
    size = len(compressed)
    prime = find_nearest_prime_around(size // 2)
    print(f"Compressed size: {size} bytes. Nearest prime: {prime}")

def decode_with_paq():
    input_file = input("Enter .enc file: ")
    output_file = input("Enter output file: ")
    if not os.path.exists(input_file):
        print("File not found.")
        return
    with open(input_file, 'rb') as f:
        compressed = f.read()
    decompressed = paq.decompress(compressed)
    recovered = transform_with_pattern(decompressed)
    with open(output_file, 'wb') as f:
        f.write(recovered)
    print("Decoded and saved.")

# === Main Menu ===
def main():
    print("Created by Jurijus Pacalovas")
    print("Choose compression system:")
    print("1. Smart Compressor (Huffman, reversible, dictionary)")
    print("2. XOR + PAQ Compressor")
    choice = input("Enter 1 or 2: ")

    if choice == "1":
        compressor = SmartCompressor()
        print("1. Compress\n2. Decompress")
        action = input("Select action: ")
        if action == "1":
            i = input("Input file: ")
            o = input("Output file: ")
            compressor.compress(i, o)
        elif action == "2":
            i = input("Compressed file: ")
            o = input("Output file: ")
            compressor.decompress(i, o)
    elif choice == "2":
        print("1. Encode\n2. Decode")
        action = input("Select action: ")
        if action == "1":
            encode_with_paq()
        elif action == "2":
            decode_with_paq()
    else:
        print("Invalid choice.")

if __name__ == "__main__":
    main()