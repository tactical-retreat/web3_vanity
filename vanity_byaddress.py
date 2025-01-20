import multiprocessing
import os
import time
from concurrent.futures import ProcessPoolExecutor

import coincurve
from eth_utils import to_checksum_address, keccak


def generate_address_from_private_key(private_key_bytes):
    """Get the Ethereum address from a private key using coincurve."""
    # Use coincurve for faster public key generation
    public_key_bytes = coincurve.PublicKey.from_valid_secret(private_key_bytes).format(compressed=False)[1:]
    return keccak(public_key_bytes)[-20:]


def get_contract_address(sender_bytes, nonce=0):
    """Calculate the contract address using raw bytes operations."""
    if nonce == 0:
        # Pre-compute the constant parts of the RLP encoding
        return keccak(bytes([0xd6, 0x94]) + sender_bytes + bytes([0x80]))[-20:]
    else:
        return keccak(bytes([0xd6, 0x94]) + sender_bytes + bytes([nonce]))[-20:]


BATCH_SIZE = 1000  # Number of random keys to generate at once


def search_chunk(args):
    """Search a chunk of iterations for vanity address."""
    prefix_bytes, prefix_str, iterations = args
    prefix_len = len(prefix_bytes)

    # Get random bytes in larger chunks for efficiency
    for batch_start in range(0, iterations, BATCH_SIZE):
        # Generate multiple private keys at once
        batch_size = min(BATCH_SIZE, iterations - batch_start)
        random_bytes = os.urandom(32 * batch_size)

        for i in range(batch_size):
            private_key_bytes = random_bytes[i * 32:(i + 1) * 32]

            # Fast path: generate and check raw bytes first
            sender_bytes = generate_address_from_private_key(private_key_bytes)
            contract_bytes = get_contract_address(sender_bytes)

            # Only do case-insensitive comparison if the length matches
            if contract_bytes[:prefix_len].hex().upper() == prefix_bytes.hex().upper():
                # Only then do the expensive checksum comparison
                contract_addr = to_checksum_address('0x' + contract_bytes.hex())
                if contract_addr.startswith(prefix_str):
                    sender_addr = to_checksum_address('0x' + sender_bytes.hex())
                    return private_key_bytes.hex(), sender_addr, contract_addr
    return None


def find_vanity_address_parallel(vanity_prefix, num_processes=None, chunk_size=1_000_000):
    """Find vanity address using parallel processing."""
    if not vanity_prefix.startswith("0x"):
        vanity_prefix = "0x" + vanity_prefix

    # Pre-compute the prefix bytes for faster comparison
    try:
        prefix_bytes = bytes.fromhex(vanity_prefix[2:])
    except ValueError:
        raise ValueError(f"Invalid hex prefix: {vanity_prefix}")

    if num_processes is None:
        # Use physical cores instead of logical cores for better performance
        try:
            num_processes = len(os.sched_getaffinity(0))
        except AttributeError:
            num_processes = multiprocessing.cpu_count() // 2 or 1

    # Create argument tuples for each process
    args = [(prefix_bytes, vanity_prefix, chunk_size) for _ in range(num_processes)]

    start_time = time.time()
    iterations = 0
    last_print = time.time()
    print_interval = 1.0  # Update progress every second

    with ProcessPoolExecutor(max_workers=num_processes, mp_context=multiprocessing.get_context('spawn')) as executor:
        while True:
            # Run chunks in parallel
            results = list(executor.map(search_chunk, args))
            iterations += chunk_size * num_processes

            # Check if we found a result
            for result in results:
                if result:
                    private_key, deployer_address, contract_address = result
                    end_time = time.time()
                    duration = end_time - start_time
                    iterations_per_second = int(iterations / duration)
                    print(f"\nSpeed: {iterations_per_second:,} iterations/second")
                    return private_key, deployer_address, contract_address

            # Print progress at most once per second
            current_time = time.time()
            if current_time - last_print >= print_interval:
                duration = current_time - start_time
                iterations_per_second = int(iterations / duration)
                print(f"\rSpeed: {iterations_per_second:,} iterations/second", end="", flush=True)
                last_print = current_time


def run():
    # Example usage
    vanity_prefix = "0xFFFF00"  # Will match exactly against checksummed address

    print(f"Searching for contract address starting with {vanity_prefix}...")
    private_key, deployer_address, contract_address = find_vanity_address_parallel(vanity_prefix)

    print(f"\nFound matching addresses!")
    print(f"Private Key: 0x{private_key}")
    print(f"Deployer Address: {deployer_address}")
    print(f"Contract Address: {contract_address}")


if __name__ == "__main__":
    run()
