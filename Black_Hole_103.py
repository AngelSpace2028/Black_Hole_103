import os
import sys
import random
import struct
import logging
import hashlib
from tqdm import tqdm

# === Try to import paq ===
try:
    import paq
except ImportError:
    print("Error: 'paq' module is not installed or accessible.")
    sys.exit(1)

# === Dictionary file list ===
DICTIONARY_FILES = [
    "1.txt", "eng_news_2005_1M-sentences.txt", "eng_news_2005_1M-words.txt",
    "eng_news_2005_1M-sources.txt", "eng_news_2005_1M-co_n.txt",
    "eng_news_2005_1M-co_s.txt", "eng_news_2005_1M-inv_so.txt",
    "eng_news_2005_1M-meta.txt", "Dictionary.txt",
    "the-complete-reference-html-css-fifth-edition.txt",
    "words.txt.paq", "lines.txt.paq", "sentence.txt.paq"
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
        # paq.compress expects bytes
        compressed = paq.compress(data)
        return compressed

    def huffman_decompress(self, data):
        # paq.decompress expects bytes
        decompressed = paq.decompress(data)
        return decompressed

    def reversible_transform(self, data):
        # XOR each byte with 0xAA
        return bytes([b ^ 0xAA for b in tqdm(data, desc="Transforming", unit="B")])

    def reverse_reversible_transform(self, data):
        # The transform is symmetrical
        return self.reversible_transform(data)

    def generate_8byte_sha(self, file_path):
        try:
            with open(file_path, "rb") as f:
                data = f.read()
                full_hash = hashlib.sha256(data).digest()
                return full_hash[:8]  # First 8 bytes
        except Exception as e:
            logging.error(f"Failed to generate SHA for {file_path}: {e}")
            return None

    def compress(self, input_file, output_file):
        # Special case: For certain .paq dictionary files output only 8-byte SHA in one file
        if input_file.endswith(".paq") and any(x in input_file for x in ["words", "lines", "sentence"]):
            sha = self.generate_8byte_sha(input_file)
            if sha:
                original_size = os.path.getsize(input_file)
                if 8 < original_size:
                    with open(output_file, "wb") as f:
                        f.write(sha)
                    print(f"SHA-8 written to {output_file}: {sha.hex()}")
                else:
                    print("Original file smaller than SHA hash, skipping write.")
            return

        # Normal compression flow
        with open(input_file, "rb") as f:
            original_data = f.read()

        transformed = self.reversible_transform(original_data)
        transformed = bytes(tqdm(transformed, desc="Preparing Data", unit="B"))

        compressed = self.huffman_compress(transformed)
        compressed = bytes(tqdm(compressed, desc="Compressed Output", unit="B"))

        if len(compressed) < len(original_data):
            with open(output_file, "wb") as f:
                f.write(compressed)
            print(f"Smart compression successful. Saved to {output_file}")
        else:
            print("Compression not efficient. File not saved.")

    def decompress(self, input_file, output_file):
        with open(input_file, "rb") as f:
            compressed_data = f.read()

        decompressed = self.huffman_decompress(bytes(compressed_data))
        decompressed = bytes(tqdm(decompressed, desc="Huffman Decompress", unit="B"))

        original = self.reverse_reversible_transform(decompressed)

        with open(output_file, "wb") as f:
            f.write(original)

        print(f"Smart decompression complete. Saved to {output_file}")


# === XOR + PAQ Compressor ===
def transform_with_pattern(data, chunk_size=4):
    transformed = bytearray()
    for i in tqdm(range(0, len(data), chunk_size), desc="XOR Transform", unit="chunks"):
        chunk = data[i:i + chunk_size]
        transformed.extend([b ^ 0xFF for b in chunk])
    return transformed

def is_prime(n):
    if n < 2: return False
    if n == 2: return True
    if n % 2 == 0: return False
    for i in range(3, int(n**0.5)+1, 2):
        if n % i == 0:
            return False
    return True

def find_nearest_prime_around(n):
    offset = 0
    while True:
        if is_prime(n - offset):
            return n - offset
        if is_prime(n + offset):
            return n + offset
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
    compressed = bytearray(tqdm(compressed, desc="PAQ Compress", unit="B"))

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

    decompressed = paq.decompress(bytes(compressed))
    decompressed = bytearray(tqdm(decompressed, desc="PAQ Decompress", unit="B"))
    recovered = transform_with_pattern(decompressed)

    with open(output_file, 'wb') as f:
        f.write(recovered)

    print("Decoded and saved.")


# === Main Menu ===
def main():
    print("Created by Jurijus Pacalovas")
    print("Choose compression system:")
    print("1. Smart Compressor (Huffman + Reversible)")
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