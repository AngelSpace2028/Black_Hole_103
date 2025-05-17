import heapq
import os
import re
import hashlib
import paq  # You must ensure this exists (placeholder for PAQ8PX or a wrapper)
import zlib
from tqdm import tqdm

# === Utility Functions ===

def int_to_3bytes(value):
    return bytes([(value >> 16) & 0xFF, (value >> 8) & 0xFF, value & 0xFF])

def bytes3_to_int(b):
    return (b[0] << 16) | (b[1] << 8) | b[2]

def sha256_hash(data):
    return hashlib.sha256(data).hexdigest()

def transform_with_pattern(data):
    return bytearray([b ^ 0xFF for b in data])  # XOR transform

def encode_leading_zeros(data):
    count = 0
    max_count = 31
    while count < len(data) and data[count] == 0x00 and count < max_count:
        count += 1
    remainder = data[count:]
    header = bytes([(count & 0x1F) << 3])  # 5 bits used
    return header + remainder

def decode_leading_zeros(data):
    if not data:
        return data
    count = (data[0] >> 3) & 0x1F
    leading = bytes([0x00] * count)
    return leading + data[1:]

# === Dictionary Builder ===

def build_dictionary_from_input(input_filename, dictionary_filename):
    words = set()
    with open(input_filename, 'r', encoding='utf-8', errors='ignore') as infile:
        for line in infile:
            for word in re.findall(r'\w+', line):
                words.add(word.strip())

    sorted_words = sorted(words)
    with open(dictionary_filename, 'w', encoding='utf-8') as outfile:
        for word in sorted_words:
            outfile.write(f"{word}\n")
    print(f"Dictionary saved as {dictionary_filename} with {len(sorted_words)} words.")

    # Optionally compress dictionary with PAQ
    with open(dictionary_filename, 'rb') as f:
        compressed = paq.compress(f.read())
    with open(dictionary_filename + ".paq", 'wb') as f:
        f.write(compressed)
    print(f"Dictionary compressed to {dictionary_filename}.paq")

# === Compression Helpers ===

def load_dictionary_from_file(filename, max_lines=2**24):
    dictionary = {}
    try:
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            for idx, line in enumerate(f):
                if idx >= max_lines:
                    break
                parts = line.strip().split()
                if len(parts) > 0:
                    dictionary[parts[0]] = idx
        return dictionary
    except Exception as e:
        print(f"Dictionary load error: {e}")
        return None

def compress_text_with_dictionary(text, dictionary):
    result = bytearray()
    tokens = re.findall(r'\S+|\s+', text)
    for token in tokens:
        if token.isspace():
            result.append(2)
            encoded = token.encode('utf-8')
            result.append(len(encoded))
            result += encoded
        else:
            code = dictionary.get(token)
            if code is not None:
                result.append(1)
                result += int_to_3bytes(code)
            else:
                result.append(0)
                raw = token.encode('utf-8', errors='ignore')
                result.append(len(raw))
                result += raw
    return bytes(result)

def decompress_text_with_dictionary(data, dictionary):
    reverse_dict = {v: k for k, v in dictionary.items()}
    i = 0
    result = []
    while i < len(data):
        flag = data[i]
        i += 1
        if flag == 1:
            code = bytes3_to_int(data[i:i+3])
            i += 3
            word = reverse_dict.get(code, "")
            result.append(word)
        elif flag == 0:
            length = data[i]
            i += 1
            word = data[i:i+length].decode('utf-8', errors='ignore')
            result.append(word)
            i += length
        elif flag == 2:
            length = data[i]
            i += 1
            space = data[i:i+length].decode('utf-8', errors='ignore')
            result.append(space)
            i += length
    return ''.join(result)

def compress_bytes_paq_xor(data):
    transformed = transform_with_pattern(data)
    encoded = encode_leading_zeros(transformed)
    return paq.compress(encoded)

def decompress_bytes_paq_xor(data):
    try:
        decompressed = paq.decompress(data)
        restored = decode_leading_zeros(decompressed)
        return transform_with_pattern(bytearray(restored))
    except Exception as e:
        print(f"Decompression error: {e}")
        return None

# === Main Compress/Decompress Wrappers ===

def compress_text(input_filename, output_filename, dictionary_filename):
    try:
        dictionary = load_dictionary_from_file(dictionary_filename)
        if dictionary is None:
            print("Failed to load dictionary.")
            return
        text = ""
        with open(input_filename, 'r', encoding='utf-8', errors='ignore') as infile:
            for line in infile:
                text += line
        original_hash = sha256_hash(text.encode('utf-8'))
        encoded = compress_text_with_dictionary(text, dictionary)
        compressed = compress_bytes_paq_xor(encoded)
        with open(output_filename, 'wb') as outfile:
            outfile.write(compressed)
        print(f"Text compressed to {output_filename}")
        print(f"Original SHA-256: {original_hash}")
    except Exception as e:
        print(f"Error: {e}")

def compress_binary(input_filename, output_filename):
    try:
        data = bytearray()
        with open(input_filename, 'rb') as infile:
            while chunk := infile.read(8192):
                data.extend(chunk)
        compressed = compress_bytes_paq_xor(data)
        with open(output_filename, 'wb') as outfile:
            outfile.write(compressed)
        print(f"Binary compressed to {output_filename}")
    except Exception as e:
        print(f"Binary compression error: {e}")

def decompress_binary(input_filename, output_filename):
    try:
        with open(input_filename, 'rb') as infile:
            data = infile.read()
        decompressed = decompress_bytes_paq_xor(data)
        if decompressed is not None:
            choice = input("Use dictionary for decoding? (yes/no): ").lower()
            if choice == 'yes':
                dict_filename = input("Enter dictionary filename: ")
                dictionary = load_dictionary_from_file(dict_filename)
                if dictionary is None:
                    print("Failed to load dictionary.")
                    return
                text = decompress_text_with_dictionary(decompressed, dictionary)
                with open(output_filename, 'w', encoding='utf-8') as outfile:
                    outfile.write(text)
                print(f"Text decompressed to {output_filename}")
                print(f"SHA-256: {sha256_hash(text.encode('utf-8'))}")
            else:
                with open(output_filename, 'wb') as outfile:
                    outfile.write(decompressed)
                print(f"Binary decompressed to {output_filename}")
    except Exception as e:
        print(f"Decompression error: {e}")

# === CLI ===

if __name__ == "__main__":
    print("Choose mode: [1] Build dictionary, [2] Compress text, [3] Compress binary, [4] Decompress binary")
    mode = input("Enter choice: ")
    if mode == "1":
        input_file = input("Enter input filename to extract dictionary from: ")
        dict_file = "words.txt"
        build_dictionary_from_input(input_file, dict_file)
    elif mode == "2":
        input_filename = input("Enter input text filename: ")
        output_filename = input("Enter output filename: ")
        dictionary_filename = input("Enter dictionary filename: ")
        compress_text(input_filename, output_filename, dictionary_filename)
    elif mode == "3":
        input_filename = input("Enter input binary filename: ")
        output_filename = input("Enter output filename: ")
        compress_binary(input_filename, output_filename)
    elif mode == "4":
        input_filename = input("Enter compressed filename: ")
        output_filename = input("Enter output filename: ")
        decompress_binary(input_filename, output_filename)
    else:
        print("Invalid choice.")