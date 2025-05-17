import os
import sys
import random
import struct
import logging
import hashlib
import re
from tqdm import tqdm

try:
    import paq
except ImportError:
    print("Error: 'paq' module is not installed or accessible.")
    sys.exit(1)

# Common dictionary files
DICTIONARY_FILES = [
    "1.txt", "eng_news_2005_1M-sentences.txt", 
    "eng_news_2005_1M-words.txt", "eng_news_2005_1M-sources.txt",
    "eng_news_2005_1M-co_n.txt", "eng_news_2005_1M-co_s.txt",
    "eng_news_2005_1M-inv_so.txt", "eng_news_2005_1M-meta.txt", 
    "Dictionary.txt", "the-complete-reference-html-css-fifth-edition.txt",
    "words.txt.paq", "lines.txt.paq", "sentence.txt.paq",
    "tag.txt", "words.txt"
]

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
        compressed = paq.compress(data)
        return compressed

    def huffman_decompress(self, data):
        decompressed = paq.decompress(data)
        return decompressed

    def reversible_transform(self, data):
        return bytes([b ^ 0xAA for b in tqdm(data, desc="Transforming", unit="B")])

    def reverse_reversible_transform(self, data):
        return self.reversible_transform(data)

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
    recovered = transform_with_pattern(decompressed)

    with open(output_file, 'wb') as f:
        f.write(recovered)
    print("Decoded and saved.")

class DictionaryCompressor:
    def __init__(self):
        self.dictionary = set()
        
    def load_full_dictionary(self):
        self.dictionary = set()
        for file in DICTIONARY_FILES:
            if not os.path.exists(file):
                continue
            file_size = os.path.getsize(file)
            with open(file, 'r', encoding='utf-8', errors='ignore') as f:
                chunk_size = 1024 * 1024
                with tqdm(total=file_size, unit='B', unit_scale=True, desc=f'Loading {file}') as pbar:
                    buffer = ""
                    while True:
                        data = f.read(chunk_size)
                        if not data:
                            break
                        buffer += data
                        lines = buffer.split('\n')
                        buffer = lines.pop()
                        for line in lines:
                            word = line.strip()
                            if word:
                                self.dictionary.add(word)
                        pbar.update(len(data))
                    if buffer.strip():
                        self.dictionary.add(buffer.strip())
        print(f"Loaded dictionary words: {len(self.dictionary)}")
    
    @staticmethod
    def sha256_hash(data):
        return hashlib.sha256(data.encode('utf-8')).digest()[:8]
    
    @staticmethod
    def xor_prime_fallback(word):
        prime = 2147483647
        total = sum(ord(c) for c in word)
        transformed = total ^ prime
        return transformed.to_bytes(8, 'big')
    
    def match_in_dictionary(self, line):
        line = line.strip()
        if line in self.dictionary:
            return self.sha256_hash(line), True
        
        words = line.split()
        for w in words:
            if w in self.dictionary:
                return self.sha256_hash(w), True
        
        sentences = re.split(r'[.!?]', line)
        for s in sentences:
            s = s.strip()
            if s and s in self.dictionary:
                return self.sha256_hash(s), True
        
        return self.xor_prime_fallback(line), False
    
    def compress_file(self, input_file, output_file):
        output_data = bytearray()
        with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            with tqdm(total=len(lines), desc="Compressing lines") as pbar:
                for line in lines:
                    encoded, is_dict = self.match_in_dictionary(line)
                    flag = b'\x01' if is_dict else b'\x00'
                    lz = len(encoded) - len(encoded.lstrip(b'\x00'))
                    output_data += flag + bytes([lz]) + encoded.lstrip(b'\x00')
                    pbar.update(1)

        final = paq.compress(bytes(output_data))
        with open(output_file, 'wb') as out:
            out.write(final)
        
        original_size = os.path.getsize(input_file)
        compressed_size = os.path.getsize(output_file)
        ratio = compressed_size / original_size
        print(f"Compressed file saved to: {output_file}")
        print(f"Original size: {original_size} bytes")
        print(f"Compressed size: {compressed_size} bytes")
        print(f"Compression ratio: {ratio:.4f}")
    
    def decompress_file(self, input_file, output_file):
        with open(input_file, 'rb') as f:
            data = paq.decompress(f.read())

        result = []
        i = 0
        while i < len(data):
            flag = data[i]
            lz = data[i + 1]
            chunk_len = 8 - lz
            chunk = data[i:i + 2 + chunk_len]
            
            compressed = b'\x00' * lz + chunk[2:]
            if flag == 1:
                found = False
                for word in self.dictionary:
                    if self.sha256_hash(word) == compressed:
                        result.append(word)
                        found = True
                        break
                if not found:
                    result.append("[UNKNOWN]")
            else:
                result.append(f"[FALLBACK:{int.from_bytes(compressed, 'big')}]")
            
            i += 2 + chunk_len

        with open(output_file, 'w', encoding='utf-8') as out:
            for line in result:
                out.write(line + '\n')
        print(f"Decompressed file saved to: {output_file}")

def main():
    print("=== Advanced Compression System ===")
    print("Created by Jurijus Pacalovas")
    print("1. Smart Compressor (Binary/General Data)")
    print("2. XOR + PAQ Compressor")
    print("3. Dictionary Compressor (Text Data)")
    choice = input("Choose option (1/2/3): ").strip()
    
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
        print("1. Encode\n2. Decode")
        action = input("Select action: ")
        if action == "1":
            encode_with_paq()
        elif action == "2":
            decode_with_paq()
        else:
            print("Invalid action.")
    
    elif choice == "3":
        compressor = DictionaryCompressor()
        print("1. Compress\n2. Decompress")
        action = input("Select action: ")
        use_dict = input("Use dictionary? (y/n): ").lower() == 'y'
        
        if use_dict:
            compressor.load_full_dictionary()
        
        i = input("Input file: ")
        o = input("Output file: ")
        
        if action == "1":
            compressor.compress_file(i, o)
        elif action == "2":
            compressor.decompress_file(i, o)
        else:
            print("Invalid action.")
    
    else:
        print("Invalid choice.")

if __name__ == "__main__":
    main()