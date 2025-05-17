import heapq
import os
import re
import hashlib
import zlib
import paq  # Placeholder module for PAQ
from tqdm import tqdm

# === Huffman & Utility Functions ===

def build_huffman_tree(frequencies):
    heap = [[weight, [symbol, ""]] for symbol, weight in frequencies.items()]
    heapq.heapify(heap)
    while len(heap) > 1:
        lo = heapq.heappop(heap)
        hi = heapq.heappop(heap)
        for pair in lo[1:]:
            pair[1] = "0" + pair[1]
        for pair in hi[1:]:
            pair[1] = "1" + pair[1]
        heapq.heappush(heap, [lo[0] + hi[0]] + lo[1:] + hi[1:])
    return sorted(heapq.heappop(heap)[1:], key=lambda p: p[1])

def create_huffman_codes(tree):
    return {symbol: code for symbol, code in tree}

def int_to_3bytes(value):
    return bytes([(value >> 16) & 0xFF, (value >> 8) & 0xFF, value & 0xFF])

def bytes3_to_int(b):
    return (b[0] << 16) | (b[1] << 8) | b[2]

def sha256_hash(data):
    return hashlib.sha256(data).hexdigest()

def transform_with_pattern(data):
    return bytearray([b ^ 0xFF for b in data])

# === Leading Zero Compression Logic ===

def encode_leading_zeros(data):
    count = 0
    max_count = 31
    while count < len(data) and data[count] == 0x00 and count < max_count:
        count += 1
    remainder = data[count:]
    header = bytes([(count & 0x1F) << 3])
    return header + remainder

def decode_leading_zeros(data):
    if not data:
        return data
    count = (data[0] >> 3) & 0x1F
    leading = bytes([0x00] * count)
    return leading + data[1:]

# === Compression Steps ===

def compress_bytes_paq_xor(data):
    transformed_data = transform_with_pattern(data)
    encoded = encode_leading_zeros(transformed_data)
    return paq.compress(encoded)

def decompress_bytes_paq_xor(data):
    try:
        decompressed_data = paq.decompress(data)
        restored = decode_leading_zeros(decompressed_data)
        return transform_with_pattern(bytearray(restored))
    except Exception as e:
        print(f"Decompression error: {e}")
        return None

# === Dictionary Handling ===

def build_multiple_dictionaries(text):
    words = set(re.findall(r'\b\w+\b', text))
    lines = set(text.splitlines())
    sentences = set(re.split(r'(?<=[.!?]) +', text))

    with open("words.txt", 'w', encoding='utf-8') as f:
        for word in sorted(words):
            f.write(f"{word}\n")

    with open("lines.txt", 'w', encoding='utf-8') as f:
        for line in sorted(lines):
            f.write(f"{line}\n")

    with open("sentences.txt", 'w', encoding='utf-8') as f:
        for sentence in sorted(sentences):
            f.write(f"{sentence}\n")

    for fname in ("words.txt", "lines.txt", "sentences.txt"):
        with open(fname, 'rb') as f:
            data = f.read()
        with open(fname + ".paq", 'wb') as f:
            f.write(paq.compress(data))

def load_dictionary(filename, max_lines=2**24):
    dictionary = {}
    try:
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            for idx, line in enumerate(tqdm(f, total=max_lines, desc=f"Loading {filename}")):
                if idx >= max_lines:
                    break
                item = line.strip()
                if item:
                    dictionary[item] = idx
        return dictionary
    except Exception as e:
        print(f"Dictionary load error for {filename}: {e}")
        return None

# === Encoding / Decoding ===

def compress_text_with_dictionary(text, word_dict, line_dict, sent_dict):
    result = bytearray()
    lines = text.splitlines(keepends=True)
    for line in tqdm(lines, desc="Encoding lines"):
        if line.strip() in line_dict:
            result.append(3)
            result += int_to_3bytes(line_dict[line.strip()])
        else:
            sentences = re.split(r'(?<=[.!?]) +', line)
            for sentence in sentences:
                if sentence.strip() in sent_dict:
                    result.append(2)
                    result += int_to_3bytes(sent_dict[sentence.strip()])
                else:
                    words = re.findall(r'\S+|\s+', sentence)
                    for token in words:
                        if token.isspace():
                            result.append(5)
                            encoded = token.encode('utf-8')
                            result += len(encoded).to_bytes(2, 'big')
                            result += encoded
                        else:
                            code = word_dict.get(token)
                            if code is not None:
                                result.append(1)
                                result += int_to_3bytes(code)
                            else:
                                result.append(0)
                                raw = token.encode('utf-8')
                                result += len(raw).to_bytes(2, 'big')
                                result += raw
    return bytes(result)

def decompress_text_with_dictionary(data, word_dict, line_dict, sent_dict):
    word_rev = {v: k for k, v in word_dict.items()}
    line_rev = {v: k for k, v in line_dict.items()}
    sent_rev = {v: k for k, v in sent_dict.items()}

    i = 0
    result = []
    while i < len(data):
        flag = data[i]
        i += 1
        if flag == 1:  # Word
            code = bytes3_to_int(data[i:i+3])
            result.append(word_rev.get(code, ""))
            i += 3
        elif flag == 0:  # Raw token
            length = int.from_bytes(data[i:i+2], 'big')
            i += 2
            result.append(data[i:i+length].decode('utf-8'))
            i += length
        elif flag == 2:  # Sentence
            code = bytes3_to_int(data[i:i+3])
            result.append(sent_rev.get(code, ""))
            i += 3
        elif flag == 3:  # Line
            code = bytes3_to_int(data[i:i+3])
            result.append(line_rev.get(code, "") + "\n")
            i += 3
        elif flag == 5:  # Space
            length = int.from_bytes(data[i:i+2], 'big')
            i += 2
            result.append(data[i:i+length].decode('utf-8'))
            i += length
    return ''.join(result)

# === Main Compression Interface ===

def compress_text(input_filename, output_filename):
    try:
        with open(input_filename, 'r', encoding='utf-8', errors='ignore') as infile:
            text = infile.read()

        original_hash = sha256_hash(text.encode('utf-8'))
        build_multiple_dictionaries(text)
        word_dict = load_dictionary("words.txt")
        line_dict = load_dictionary("lines.txt")
        sent_dict = load_dictionary("sentences.txt")
        if not word_dict or not line_dict or not sent_dict:
            print("Failed to load one or more dictionaries.")
            return

        encoded = compress_text_with_dictionary(text, word_dict, line_dict, sent_dict)
        compressed = compress_bytes_paq_xor(encoded)

        with open(output_filename, 'wb') as outfile:
            outfile.write(compressed)

        print(f"Compressed to {output_filename}")
        print(f"Original SHA-256: {original_hash}")
    except Exception as e:
        print(f"Compression error: {e}")

def compress_binary(input_filename, output_filename):
    try:
        with open(input_filename, 'rb') as infile:
            data = infile.read()
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
        if decompressed is None:
            return
        choice = input("Use dictionary for decoding? (yes/no): ").lower()
        if choice == 'yes':
            for file in ("words.txt.paq", "lines.txt.paq", "sentences.txt.paq"):
                with open(file, 'rb') as f:
                    raw = paq.decompress(f.read())
                with open(file.replace('.paq', ''), 'wb') as f:
                    f.write(raw)
            word_dict = load_dictionary("words.txt")
            line_dict = load_dictionary("lines.txt")
            sent_dict = load_dictionary("sentences.txt")
            text = decompress_text_with_dictionary(decompressed, word_dict, line_dict, sent_dict)
            with open(output_filename, 'w', encoding='utf-8') as outfile:
                outfile.write(text)
            print(f"Decompressed text to {output_filename}")
            print(f"SHA-256: {sha256_hash(text.encode('utf-8'))}")
        else:
            with open(output_filename, 'wb') as outfile:
                outfile.write(decompressed)
            print(f"Decompressed binary to {output_filename}")
    except Exception as e:
        print(f"Decompression error: {e}")

# === CLI ===

if __name__ == "__main__":
    print("Choose mode: [1] Compress text, [2] Compress binary, [3] Decompress binary")
    choice = input("Enter choice: ")
    if choice == "1":
        input_filename = input("Enter input text filename: ")
        output_filename = input("Enter output filename: ")
        compress_text(input_filename, output_filename)
    elif choice == "2":
        input_filename = input("Enter input binary filename: ")
        output_filename = input("Enter output filename: ")
        compress_binary(input_filename, output_filename)
    elif choice == "3":
        input_filename = input("Enter compressed filename: ")
        output_filename = input("Enter output filename: ")
        decompress_binary(input_filename, output_filename)
    else:
        print("Invalid choice.")
