import hashlib
import os

# Simulated device secret – should be constant per edge device in real-world
DEVICE_SECRET = "ABC-7GZR-PQVK"

def PUF(challenge: str) -> str:
    """
    Simulates a PUF response.
    Given a challenge C, returns a unique but deterministic response R.
    In real-world, this would be derived from physical randomness.
    """
    combined = DEVICE_SECRET + challenge
    response = hashlib.sha256(combined.encode()).hexdigest()
    #print(response)
    return response

def PUF_unstable(challenge: str, noise_level: float = 0.0) -> str:
    """
    Simulates unstable PUF (with optional noise).
    `noise_level` determines how many bits may flip (0.0 = perfect reproducibility).
    """
    raw = PUF(challenge)
    if noise_level == 0:
        return raw

    bits = list(bin(int(raw, 16))[2:].zfill(256))
    import random
    for i in range(len(bits)):
        if random.random() < noise_level:
            bits[i] = '1' if bits[i] == '0' else '0'

    noisy_hex = hex(int(''.join(bits), 2))[2:]
    return noisy_hex.zfill(64)

