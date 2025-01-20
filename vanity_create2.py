import multiprocessing
import os
import time
from concurrent.futures import ProcessPoolExecutor

from eth_utils import keccak
from web3 import Web3

w3 = Web3()

# Pre-compute constants
FF_CONSTANT = b'\xff'


def generate_random_salt_bytes():
    """Generate random bytes directly instead of hex string."""
    return os.urandom(32)


def calculate_create2_address_optimized(deployer_bytes, salt_bytes, bytecode_bytes):
    """Optimized CREATE2 address calculation."""
    return keccak(FF_CONSTANT + deployer_bytes + salt_bytes + bytecode_bytes)[-20:]


def search_chunk(args):
    """Search a chunk of iterations for vanity address."""
    deployer_bytes, bytecode_bytes, vanity_prefix, iterations = args

    for _ in range(iterations):
        salt_bytes = generate_random_salt_bytes()
        address_bytes = calculate_create2_address_optimized(
            deployer_bytes,
            salt_bytes,
            bytecode_bytes
        )

        # Convert to checksummed address and check prefix
        raw_address = '0x' + address_bytes.hex()
        checksummed = w3.to_checksum_address(raw_address)
        if checksummed.startswith(vanity_prefix):
            return salt_bytes.hex()
    return None


def find_vanity_address_parallel(deployer, bytecode, vanity_prefix, num_processes=None):
    """Find vanity address using parallel processing."""
    # Convert inputs to bytes once
    deployer_bytes = bytes.fromhex(deployer.lower().replace("0x", "").zfill(40))
    bytecode_bytes = bytes.fromhex(bytecode)
    # Keep vanity_prefix as string for checksum comparison
    if not vanity_prefix.startswith("0x"):
        vanity_prefix = "0x" + vanity_prefix

    if num_processes is None:
        num_processes = multiprocessing.cpu_count()

    chunk_size = 100_000

    # Create argument tuples for each process
    args = [(deployer_bytes, bytecode_bytes, vanity_prefix, chunk_size)
            for _ in range(num_processes)]

    start_time = time.time()
    iterations = 0

    with ProcessPoolExecutor(max_workers=num_processes) as executor:
        while True:
            # Run chunks in parallel
            results = list(executor.map(search_chunk, args))
            iterations += chunk_size * num_processes

            # Check if we found a result
            for result in results:
                if result:
                    end_time = time.time()
                    duration = end_time - start_time
                    iterations_per_second = int(iterations / duration)
                    print(f"\nSpeed: {iterations_per_second:,} iterations/second")

                    # Calculate the final address for verification
                    final_address = "0x" + calculate_create2_address_optimized(
                        deployer_bytes,
                        bytes.fromhex(result),
                        bytecode_bytes
                    ).hex()

                    return result, final_address

            # Print progress
            if iterations % 1_000_000 == 0:
                current_time = time.time()
                duration = current_time - start_time
                iterations_per_second = int(iterations / duration)
                print(f"\rSpeed: {iterations_per_second:,} iterations/second", end="")


def run():
    # Test parameters
    deployer = "0x4e59b44847b379578588920cA78FbF26c0B4956C"
    vanity_prefix = "0xFFFF00"
    bytecode_hash = "3ba2837b92a48b70fada56d28bb24dd6bc2931085d07026c06e5977ac5fe3d07"

    salt, address = find_vanity_address_parallel(deployer, bytecode_hash, vanity_prefix)
    print(f"\nFound salt: {salt}")
    print(f"Vanity address: {address}")


if __name__ == "__main__":
    run()
