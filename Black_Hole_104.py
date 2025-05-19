import os
import sys
import math
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

# === Prime numbers from 2 to 255 ===
PRIMES = [p for p in range(2, 256) if all(p % d != 0 for d in range(2, int(p ** 0.5) + 1))]


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
        return paq.compress(data)

    def huffman_decompress(self, data):
        return paq.decompress(data)

    def reversible_transform(self, data):
        return transform_with_prime_xor_every_3_bytes(data)

    def reverse_reversible_transform(self, data):
        return transform_with_prime_xor_every_3_bytes(data)  # XOR is symmetrical

    def generate_8byte_sha(self, file_path):
        try:
            with open(file_path, "rb") as f:
                data = f.read()
                full_hash = hashlib.sha256(data).digest()
                return full_hash[:8]
        except Exception as e:
            logging.error(f"Failed to generate SHA for {file_path}: {e}")
            return None

    def compress(self, input_file, output_file):
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

        decompressed = self.huffman_decompress(compressed_data)
        decompressed = bytes(tqdm(decompressed, desc="Huffman Decompress", unit="B"))

        original = self.reverse_reversible_transform(decompressed)

        with open(output_file, "wb") as f:
            f.write(original)

        print(f"Smart decompression complete. Saved to {output_file}")


# === XOR with Prime (every 3 bytes, repeated 1000 times) ===
def transform_with_prime_xor_every_3_bytes(data, repeat=1000):
    transformed = bytearray(data)
    for prime in tqdm(PRIMES, desc="XOR with Primes", unit="prime"):
        xor_val = prime if prime == 2 else math.ceil(prime / 2)
        for _ in range(repeat):
            for i in range(0, len(transformed), 3):
                if i < len(transformed):
                    transformed[i] ^= xor_val
    return transformed


# === Simple Encoder/Decoder ===
def transform_with_pattern(data, chunk_size=4):
    transformed = bytearray()
    for i in range(0, len(data), chunk_size):
        chunk = data[i:i + chunk_size]
        transformed.extend([b ^ 0xFF for b in chunk])
    return transformed


def is_prime(n):
    if n < 2: return False
    if n == 2: return True
    if n % 2 == 0: return False
    for i in range(3, int(n ** 0.5) + 1, 2):
        if n % i == 0: return False
    return True


def find_nearest_prime_around(n):
    offset = 0
    while True:
        if is_prime(n - offset): return n - offset
        if is_prime(n + offset): return n + offset
        offset += 1


def encode_with_compression():
    print("\nSimple Encoder (XOR + PAQ Compression)")
    try:
        input_file = input("Enter input file: ").strip()
        output_base = input("Enter output base name (without .enc): ").strip()
    except EOFError:
        print("No input detected. Exiting encode mode.")
        return

    output_enc = output_base + ".enc"

    if not os.path.isfile(input_file):
        print(f"Error: File '{input_file}' does not exist.")
        return

    try:
        with open(input_file, 'rb') as f:
            original_data = f.read()

        transformed_data = transform_with_pattern(original_data)
        transformed_data_bytes = bytes(transformed_data)
        compressed_data = paq.compress(transformed_data_bytes)

        with open(output_enc, 'wb') as f:
            f.write(compressed_data)

        size = len(compressed_data)
        half_size = size // 2
        nearby_prime = find_nearest_prime_around(half_size)
        print(f"Compressed file size: {size} bytes")
        print(f"Nearest prime around half size: {nearby_prime}")
        print(f"Encoding complete. Saved to {output_enc}")
    except Exception as e:
        print(f"Encoding error: {e}")


def decode_with_compression():
    print("\nSimple Decoder (PAQ Decompression + XOR)")
    try:
        input_enc = input("Enter encoded file (.enc): ").strip()
        output_file = input("Enter output file: ").strip()
    except EOFError:
        print("No input detected. Exiting decode mode.")
        return

    if not os.path.isfile(input_enc):
        print(f"Error: File '{input_enc}' does not exist.")
        return

    try:
        with open(input_enc, 'rb') as f:
            encoded_data = f.read()

        decompressed_data = paq.decompress(encoded_data)
        recovered_data = transform_with_pattern(decompressed_data)

        with open(output_file, 'wb') as f:
            f.write(recovered_data)

        print(f"Decoding complete. Output saved to {output_file}")
    except Exception as e:
        print(f"Decoding error: {e}")


# === Unified Main Menu ===
def main():
    print("Software")
    print("Created by Jurijus Pacalovas.")
    print("Choose compression system:")
    print("1 - Smart Compressor (Huffman + XOR Prime)")
    print("2 - Simple Encoder/Decoder (XOR + PAQ)")
    choice = input("Enter 1 or 2: ").strip()

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
        else:
            print("Invalid action.")
    elif choice == "2":
        print("1 - Encode\n2 - Decode")
        sub_choice = input("Choose: ")
        if sub_choice == "1":
            encode_with_compression()
        elif sub_choice == "2":
            decode_with_compression()
        else:
            print("Invalid encode/decode choice.")
    else:
        print("Invalid main choice.")


if __name__ == "__main__":
    main()