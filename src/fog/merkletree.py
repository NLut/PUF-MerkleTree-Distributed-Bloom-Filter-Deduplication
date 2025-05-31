# merkletree.py
import json
from hashlib import sha256

class MerkleTree:
    def __init__(self):
        self.leaves = []
        self.leaf_map = {}
        self.tree = []
        self.proofs = {}

    @staticmethod
    def hash_leaf(did, c, p):
        return sha256(f"{did}|{c}|{p}".encode()).hexdigest()

    def load_leaves_from_db(self, db):
        for did, crps in db.items():
            for entry in crps:
                h = self.hash_leaf(did, entry["C"], entry["P"])
                self.leaves.append(h)
                self.leaf_map[h] = {"DID": did, "C": entry["C"], "P": entry["P"]}

    def build_tree(self):
        level = self.leaves[:]
        self.tree = [level]
        while len(level) > 1:
            next_level = []
            for i in range(0, len(level), 2):
                left = level[i]
                right = level[i+1] if i+1 < len(level) else left
                combined = sha256((left + right).encode()).hexdigest()
                next_level.append(combined)
            level = next_level
            self.tree.append(level)

    def generate_proofs(self):
        self.proofs = {}
        for i, leaf in enumerate(self.leaves):
            proof = []
            idx = i
            for level in self.tree[:-1]:
                sibling = idx ^ 1
                if sibling < len(level):
                    is_left = sibling < idx
                    proof.append({
                        "isLeft": is_left,
                        "hash": level[sibling]
                    })
                idx //= 2
            self.proofs[leaf] = proof

    def root(self):
        if self.tree:
            return self.tree[-1][0]
        return None

    def save_proofs(self, filepath="proof_db.json"):
        with open(filepath, "w") as f:
            json.dump(self.proofs, f, indent=2)

    def verify_proof(leaf_hash, proof, root):
        current = leaf_hash
        for step in proof:
            sibling = step["hash"]
            if step["isLeft"]:
                current = sha256((sibling + current).encode()).hexdigest()
            else:
                current = sha256((current + sibling).encode()).hexdigest()
        return current == root

