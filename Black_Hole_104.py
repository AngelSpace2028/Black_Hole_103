import os
import struct
import paq  # This must be your wrapper or handler for PAQ8PX

def transform_with_xor(data, chunk_size=4):
    """Apply XOR 0xFF transformation per chunk."""
    return bytearray([b ^ 0xFF for b in data])

def is_prime(n):
    if n < 2: return False
    if n == 2: return True
    if n % 2 == 0: return False
    for i in range(3, int(n**0.5) + 1, 2):
        if n % i == 0: return False
    return True

def find_nearest_prime_around(n):
    offset = 0
    while True:
        if is_prime(n - offset): return n - offset
        if is_prime(n + offset): return n + offset
        offset += 1

def divide_3bytes_by_prime(data):
    result = bytearray()
    metadata = bytearray()
    for i in range(0, len(data), 3):
        chunk = data[i:i+3]
        if len(chunk) < 3:
            chunk += b'\x00' * (3 - len(chunk))  # pad to 3 bytes
        val = int.from_bytes(chunk, 'big')
        prime = find_nearest_prime_around(max(3, val // 2))
        new_val = val // prime
        new_chunk = new_val.to_bytes(3, 'big')
        result.extend(new_chunk)
        metadata.append(prime % 256)  # Save prime metadata (1 byte only)
    return result, metadata

def encode_with_compression():
    print("Simple Encoder (XOR + Divide + Compression + Meta)")
    try:
        input_file = input("Enter input file: ").strip()
        output_file = input("Enter output .enc file: ").strip()
    except EOFError:
        print("No input detected. Exiting.")
        return

    if not os.path.isfile(input_file):
        print(f"Error: File '{input_file}' does not exist.")
        return

    try:
        with open(input_file, 'rb') as f:
            original_data = f.read()

        # Transform using XOR
        xor_data = transform_with_xor(original_data)

        # Divide each 3-byte block by a prime number and collect metadata
        divided_data, metadata = divide_3bytes_by_prime(xor_data)

        # Combine data and metadata
        full_data = divided_data + b"METADATA" + metadata

        # Compress all data
        compressed_data = paq.compress(full_data)

        with open(output_file, 'wb') as f:
            f.write(compressed_data)

        size = len(compressed_data)
        half_size = size // 2
        nearest_prime = find_nearest_prime_around(half_size)

        print(f"Compression complete. Size: {size}, Half: {half_size}, Nearest Prime: {nearest_prime}")
        print(f"Output saved as {output_file}")

    except Exception as e:
        print(f"Error during encoding: {e}")

def decode_with_compression():
    print("Simple Decoder (Decompression + Reverse XOR + Meta)")
    try:
        input_file = input("Enter .enc file: ").strip()
        output_file = input("Enter output file: ").strip()
    except EOFError:
        print("No input detected. Exiting.")
        return

    if not os.path.isfile(input_file):
        print(f"Error: File '{input_file}' not found.")
        return

    try:
        with open(input_file, 'rb') as f:
            compressed_data = f.read()

        decompressed = paq.decompress(compressed_data)

        # Separate data and metadata
        marker = decompressed.find(b"METADATA")
        if marker == -1:
            print("Metadata marker not found.")
            return

        divided_data = decompressed[:marker]
        metadata = decompressed[marker + len(b"METADATA"):]

        # Reconstruct XOR'd data
        recovered = bytearray()
        for i in range(0, len(divided_data), 3):
            chunk = divided_data[i:i+3]
            if len(chunk) < 3:
                chunk += b'\x00' * (3 - len(chunk))
            val = int.from_bytes(chunk, 'big')
            prime = metadata[i//3]
            new_val = val * prime
            recovered.extend(new_val.to_bytes(3, 'big'))

        original_data = transform_with_xor(recovered)

        with open(output_file, 'wb') as f:
            f.write(original_data)

        print(f"Decoded and saved to {output_file}")

    except Exception as e:
        print(f"Error during decoding: {e}")

if __name__ == "__main__":
    print("Software")
    print("Created by Jurijus Pacalovas.")
    print("File Encoding/Decoding System")
    print("1 - Encode file")
    print("2 - Decode file")

    try:
        choice = input("Enter 1 or 2: ").strip()
    except EOFError:
        choice = '1'

    if choice == '1':
        encode_with_compression()
    elif choice == '2':
        decode_with_compression()
    else:
        print("Invalid option.")