# fuzzy_extractor.py
import os
import reedsolo
from typing import Tuple

class ReedSolomonFuzzyExtractor:
    def __init__(self, n_bytes: int = 32, ecc_bytes: int = 16):
        """
        n_bytes: length of input bytes (PUF response length)
        ecc_bytes: error-correcting bytes (strength of tolerance)
        """
        self.n_bytes = n_bytes
        self.ecc_bytes = ecc_bytes
        self.rs = reedsolo.RSCodec(ecc_bytes)

    def gen(self, raw: bytes) -> Tuple[bytes, bytes]:
        """
        Generates (helper P, key K) from raw input
        Returns:
            P: RS parity bytes (helper)
            K: original input (used as key)
        """
        if len(raw) < self.n_bytes:
            raise ValueError(f"Expected at least {self.n_bytes} bytes")
        
        key = raw[:self.n_bytes]
        encoded = self.rs.encode(key)
        helper = encoded[self.n_bytes:]  # Keep only parity part as P
        return helper, key

    def rep(self, noisy: bytes, helper: bytes) -> bytes:
        """
        Reconstructs key from noisy input and helper
        """
        if len(noisy) < self.n_bytes:
            raise ValueError(f"Expected at least {self.n_bytes} bytes of noisy input")
        
        # Reconstruct full encoded message
        encoded_attempt = noisy[:self.n_bytes] + helper
        try:
            decoded = self.rs.decode(encoded_attempt)
            return decoded  # Reconstructed key
        except reedsolo.ReedSolomonError:
            raise ValueError("Reconstruction failed: too much noise")


