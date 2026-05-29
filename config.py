# ============================================================
# QDT-DisasterNet — Global Configuration
# All hyperparameters, paths, and settings in ONE place.
# Change things here — everything else adapts automatically.
# ============================================================

import os
import torch

# ── Paths ────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
DATA_DIR    = os.path.join(BASE_DIR, "data", "raw")
PROC_DIR    = os.path.join(BASE_DIR, "data", "processed")
RESULTS_DIR = os.path.join(BASE_DIR, "results")
MODELS_DIR  = os.path.join(BASE_DIR, "saved_models")

for d in [DATA_DIR, PROC_DIR, RESULTS_DIR, MODELS_DIR]:
    os.makedirs(d, exist_ok=True)

# ── Hardware ─────────────────────────────────────────────────
DEVICE      = "cuda" if torch.cuda.is_available() else "cpu"
NUM_WORKERS = 8        # i9-12900K has 24 logical cores — use 8 for data loading
PIN_MEMORY  = DEVICE == "cuda"

# ── Dataset ──────────────────────────────────────────────────
DATASET         = "FLAME2"          # Options: "FLAME2", "D-Fire"
IMAGE_SIZE      = 224               # Resize all images to 224x224
BATCH_SIZE      = 32
TRAIN_RATIO     = 0.8
VAL_RATIO       = 0.1
TEST_RATIO      = 0.1
NUM_CLASSES     = 2                 # fire / no-fire

# ── Federated Learning ───────────────────────────────────────
NUM_CLIENTS         = 10            # Simulates 10 drone clients
FL_ROUNDS           = 50            # Number of federated rounds
LOCAL_EPOCHS        = 3             # Local training epochs per round
FRACTION_FIT        = 0.8          # 80% of drones participate per round
DROPOUT_RATE        = 0.3          # 30% of drones disconnect mid-round (for DT exp)
NON_IID_ALPHA       = 0.5          # Dirichlet alpha — lower = more non-IID
                                    # 0.1 = very non-IID, 1.0 = nearly IID
AGGREGATION         = "DMWA"        # Options: "FedAvg", "FedProx", "DMWA"
FEDPROX_MU          = 0.01          # FedProx proximal term

# ── Quantum Circuit (VQC) ────────────────────────────────────
N_QUBITS            = 6             # Number of qubits
N_LAYERS            = 3             # VQC depth (shallow to avoid barren plateaus)
QUANTUM_BACKEND     = "default.qubit"   # PennyLane simulator
                                        # Switch to "qiskit.aer" for Qiskit backend
SHOTS               = 1024          # Measurement shots

# ── Quantum Differential Privacy ─────────────────────────────
EPSILON             = 1.0           # Privacy budget ε (lower = more private)
DELTA               = 1e-5          # Privacy delta δ
NOISE_MULTIPLIER    = 1.1           # Gaussian noise multiplier for DP-SGD
MAX_GRAD_NORM       = 1.0           # Gradient clipping threshold

# ── QAOA (Swarm Path Planning) ───────────────────────────────
N_DRONES            = 8             # Number of drones in swarm
GRID_SIZE           = 10            # 10x10 disaster grid map
N_QAOA_LAYERS       = 2             # QAOA circuit depth (p parameter)
QAOA_SHOTS          = 2048          # Shots for QAOA measurement
MAX_QAOA_ITER       = 100           # Classical optimizer iterations for QAOA

# ── Digital Twin ─────────────────────────────────────────────
DT_SYNC_INTERVAL    = 5             # Sync real drone state every 5 FL rounds
DT_PRED_HORIZON     = 3             # Predict drone state 3 rounds ahead
FIRE_GRID_SIZE      = 50            # Fire simulation grid (50x50 cells)
FIRE_SPREAD_RATE    = 0.3           # Probability fire spreads to adjacent cell
WIND_SPEED          = 5.0           # m/s
WIND_DIRECTION      = 45.0          # degrees (NE)

# ── Training ─────────────────────────────────────────────────
LEARNING_RATE       = 1e-3
WEIGHT_DECAY        = 1e-4
SCHEDULER           = "cosine"      # Options: "cosine", "step", "none"
EARLY_STOP_PATIENCE = 10

# ── Logging ──────────────────────────────────────────────────
LOG_EVERY           = 5             # Log every N rounds
SAVE_BEST           = True
SEED                = 42

# ── Baselines ────────────────────────────────────────────────
BASELINES = {
    "FedAvg":        {"aggregation": "FedAvg",   "quantum": False, "dt": False},
    "FedProx":       {"aggregation": "FedProx",  "quantum": False, "dt": False},
    "QFL_no_DT":     {"aggregation": "DMWA",     "quantum": True,  "dt": False},
    "DT_FL_no_Q":    {"aggregation": "FedAvg",   "quantum": False, "dt": True},
    "QDT_DisasterNet": {"aggregation": "DMWA",   "quantum": True,  "dt": True},
}

if __name__ == "__main__":
    print("=" * 55)
    print("  QDT-DisasterNet Configuration")
    print("=" * 55)
    print(f"  Device       : {DEVICE}")
    print(f"  Dataset      : {DATASET}")
    print(f"  Clients      : {NUM_CLIENTS} drones")
    print(f"  FL Rounds    : {FL_ROUNDS}")
    print(f"  Qubits       : {N_QUBITS}")
    print(f"  QAOA Drones  : {N_DRONES}")
    print(f"  Non-IID α    : {NON_IID_ALPHA}")
    print(f"  Privacy ε    : {EPSILON}")
    print(f"  Results dir  : {RESULTS_DIR}")
    print("=" * 55)
    print("  Config loaded successfully.")
