"""
EveSense — eavesdropper detection on a simulated BB84 QKD link.

The question this code answers: if someone taps a quantum key exchange,
can the two ends tell? And the harder follow-up: can they tell when the
fiber is already noisy?

Everything below runs on Qiskit Aer. Each batch is a single stabilizer
circuit carrying many independent BB84 rounds in parallel, one qubit per
round, so a run of a few thousand rounds costs milliseconds.

Protocol per round (see `run_batch`):
    Alice prepares |0>, |1>, |+> or |-> depending on her bit and basis.
    Eve, when she is active, measures in her own basis and resends the
    state her measurement implies. That is the textbook intercept-resend
    attack.
    The channel flips and depolarises whatever arrives.
    Bob measures in the basis he picked before the round started.
Rounds where Alice and Bob chose different bases are thrown away, which
is the sifting step of real BB84.

Author: Chiara De Venuto
"""

from __future__ import annotations

import csv
import os

import numpy as np
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, ReadoutError, depolarizing_error

BATCH_QUBITS = 64
RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")


# --------------------------------------------------------------------------
# noise
# --------------------------------------------------------------------------
def build_noise_model(p_dep: float, p_ro: float) -> NoiseModel | None:
    """Channel noise (p_dep on H/X) plus readout noise (p_ro on |0>/|1>)."""
    if p_dep <= 0 and p_ro <= 0:
        return None
    nm = NoiseModel()
    if p_dep > 0:
        err = depolarizing_error(p_dep, 1)
        nm.add_all_qubit_quantum_error(err, ["h", "x"])
    if p_ro > 0:
        nm.add_all_qubit_readout_error(
            ReadoutError([[1 - p_ro, p_ro], [p_ro, 1 - p_ro]])
        )
    return nm


def make_simulator(seed: int) -> AerSimulator:
    return AerSimulator(method="stabilizer", seed_simulator=seed)


# --------------------------------------------------------------------------
# one batch of rounds
# --------------------------------------------------------------------------
def run_batch(
    n_rounds: int,
    p_eve: float,
    p_dep: float,
    p_ro: float,
    rng: np.random.Generator,
    sim: AerSimulator,
) -> tuple[int, int, int, int]:
    """Run `n_rounds` BB84 rounds in parallel.

    Returns (shared_bits, errors, sifted, eve_rounds_shared) where the last
    count tells how many of the sifted bits actually passed through Eve.
    """
    # Alice's and Bob's choices, drawn before anything is transmitted
    alice_bit = rng.integers(0, 2, n_rounds)
    alice_basis = rng.integers(0, 2, n_rounds)
    bob_basis = rng.integers(0, 2, n_rounds)
    eve_active = rng.random(n_rounds) < p_eve
    eve_basis = rng.integers(0, 2, n_rounds)

    qc = QuantumCircuit(n_rounds, n_rounds)
    for i in range(n_rounds):
        # --- Alice -----------------------------------------------------
        if alice_bit[i]:
            qc.x(i)
        if alice_basis[i]:
            qc.h(i)

        # --- Eve: intercept, measure, resend ---------------------------
        # Her measurement collapses the qubit, so we undo Alice's
        # preparation and prepare the state her measurement implies. The
        # outcome comes from the Born rule, which is exactly what a
        # mid-circuit measure-and-resend would give.
        if eve_active[i]:
            if alice_basis[i] == eve_basis[i]:
                # same basis as Alice: the measurement is deterministic
                outcome = int(alice_bit[i])
            else:
                # orthogonal basis: Born rule gives 50/50 either way
                outcome = int(rng.integers(0, 2))
            if alice_basis[i]:
                qc.h(i)
            if alice_bit[i]:
                qc.x(i)
            if outcome:
                qc.x(i)
            if eve_basis[i]:
                qc.h(i)

        # --- Bob -------------------------------------------------------
        if bob_basis[i]:
            qc.h(i)

    qc.measure(range(n_rounds), range(n_rounds))

    noise = build_noise_model(p_dep, p_ro)
    if noise is not None:
        sim.set_options(noise_model=noise)

    job = sim.run(qc, shots=1)
    counts = job.result().get_counts()
    bitstring = next(iter(counts))
    # Qiskit returns the bitstring with qubit 0 on the right
    bob_bit = np.array([int(c) for c in bitstring[::-1]])

    sifted = alice_basis == bob_basis
    n_sifted = int(sifted.sum())
    if n_sifted == 0:
        return 0, 0, 0, 0
    errors = int(np.sum(bob_bit[sifted] != alice_bit[sifted]))
    eve_sifted = int((sifted & eve_active).sum())
    return n_sifted, errors, n_sifted, eve_sifted


def measure_qber(
    total_rounds: int,
    p_eve: float,
    p_dep: float,
    p_ro: float,
    seed: int = 7,
    batches: int = 40,
) -> dict:
    """Run enough batches to collect `total_rounds` and return the stats."""
    rng = np.random.default_rng(seed)
    sim = make_simulator(seed)
    per_batch = max(BATCH_QUBITS, total_rounds // batches)

    sifted = errors = eve_sifted = 0
    rounds = 0
    while rounds < total_rounds:
        s, e, _, ev = run_batch(per_batch, p_eve, p_dep, p_ro, rng, sim)
        sifted += s
        errors += e
        eve_sifted += ev
        rounds += per_batch

    qber = errors / sifted if sifted else 0.0
    return {
        "rounds": rounds,
        "sifted": sifted,
        "errors": errors,
        "qber": qber,
        "eve_sifted": eve_sifted,
    }


# --------------------------------------------------------------------------
# Shannon entropy, for the key rate
# --------------------------------------------------------------------------
def shannon_h2(p: float) -> float:
    """Binary entropy in bits."""
    if p <= 0.0 or p >= 1.0:
        return 0.0 if p in (0.0, 1.0) else float("nan")
    return -p * np.log2(p) - (1 - p) * np.log2(1 - p)


def secure_key_rate(qber: float) -> float:
    """Privacy amplification + error correction for BB84.

    Standard bound: R = 1 - h2(e) - leak_ec, with leak_ec set to h2(e) for
    an ideal code. The rate goes to zero around e = 11 percent, which is
    the number people usually quote for BB84.
    """
    if qber >= 0.5:
        return 0.0
    return max(0.0, 1.0 - 2.0 * shannon_h2(qber))


# --------------------------------------------------------------------------
# experiments
# --------------------------------------------------------------------------
def experiment_interception_sweep(rounds: int = 30000) -> list[dict]:
    """QBER as Eve gets more aggressive. Channel stays clean."""
    rows = []
    for p_eve in np.linspace(0.0, 1.0, 11):
        r = measure_qber(rounds, float(p_eve), 0.0, 0.0, seed=11)
        rows.append({"p_eve": float(p_eve), "qber": r["qber"], "rate": secure_key_rate(r["qber"])})
        print(f"  intercept p={p_eve:0.2f}  QBER={r['qber']:.4f}  rate={secure_key_rate(r['qber']):.4f}")
    return rows


def experiment_noise_sweep(rounds: int = 30000) -> list[dict]:
    """Channel noise with Eve at home. This is the baseline she hides in."""
    rows = []
    for p_dep in np.linspace(0.0, 0.20, 11):
        r = measure_qber(rounds, 0.0, float(p_dep), float(p_dep) / 2, seed=23)
        rows.append({"p_dep": float(p_dep), "qber": r["qber"], "rate": secure_key_rate(r["qber"])})
        print(f"  channel p={p_dep:0.2f}  QBER={r['qber']:.4f}  rate={secure_key_rate(r['qber']):.4f}")
    return rows


def experiment_detection(repeats: int = 12, rounds: int = 12000) -> list[dict]:
    """Can a fixed threshold separate a clean link from a tapped one?

    We build the QBER distribution for each condition, then sweep the
    threshold and record hit rate against false alarm rate. The point of
    the whole project is in here: at low interception probability on a
    dirty channel the two distributions overlap and the alarm stops
    working.
    """
    conditions = [
        # label, p_eve, p_dep, p_ro
        ("clean link, no eve", 0.00, 0.00, 0.00),
        ("clean link, p_eve=0.1", 0.10, 0.00, 0.00),
        ("clean link, p_eve=0.3", 0.30, 0.00, 0.00),
        ("noisy link p=0.03, no eve", 0.00, 0.03, 0.015),
        ("noisy link p=0.03, p_eve=0.1", 0.10, 0.03, 0.015),
        ("noisy link p=0.03, p_eve=0.3", 0.30, 0.03, 0.015),
        ("noisy link p=0.07, no eve", 0.00, 0.07, 0.035),
        ("noisy link p=0.07, p_eve=0.1", 0.10, 0.07, 0.035),
        ("noisy link p=0.07, p_eve=0.3", 0.30, 0.07, 0.035),
    ]
    out = []
    for idx, (label, p_eve, p_dep, p_ro) in enumerate(conditions):
        samples = []
        for rep in range(repeats):
            r = measure_qber(rounds, p_eve, p_dep, p_ro, seed=100 + idx * 50 + rep, batches=10)
            samples.append(r["qber"])
        arr = np.array(samples)
        out.append(
            {
                "label": label,
                "p_eve": p_eve,
                "p_dep": p_dep,
                "mean_qber": float(arr.mean()),
                "std_qber": float(arr.std(ddof=1)),
                "samples": samples,
            }
        )
        print(f"  {label:34s} QBER={arr.mean():.4f} +/- {arr.std(ddof=1):.4f}")
    return out


def roc_points(noisy_eve: list[float], noisy_clean: list[float]) -> list[tuple[float, float]]:
    """Hit rate vs false alarm rate over every threshold we can pick."""
    grid = np.linspace(min(noisy_clean + noisy_eve), max(noisy_clean + noisy_eve), 60)
    pts = []
    for tau in grid:
        hit = float(np.mean(np.array(noisy_eve) > tau))
        false = float(np.mean(np.array(noisy_clean) > tau))
        pts.append((false, hit))
    return pts


def experiment_key_rate_curve() -> list[dict]:
    rows = []
    for e in np.linspace(0.0, 0.16, 17):
        rows.append({"qber": float(e), "rate": secure_key_rate(float(e))})
    return rows


# --------------------------------------------------------------------------
# output
# --------------------------------------------------------------------------
def write_csv(path: str, rows: list[dict], header: list[str]) -> None:
    with open(path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=header, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"  wrote {path}")


def main() -> None:
    os.makedirs(RESULTS_DIR, exist_ok=True)

    print("[1/5] interception sweep")
    sweep = experiment_interception_sweep()
    write_csv(os.path.join(RESULTS_DIR, "interception_sweep.csv"), sweep,
              ["p_eve", "qber", "rate"])

    print("[2/5] channel noise sweep")
    noise = experiment_noise_sweep()
    write_csv(os.path.join(RESULTS_DIR, "noise_sweep.csv"), noise,
              ["p_dep", "qber", "rate"])

    print("[3/5] detection study")
    det = experiment_detection()
    write_csv(
        os.path.join(RESULTS_DIR, "detection_summary.csv"),
        [{k: v for k, v in d.items() if k != "samples"} for d in det],
        ["label", "p_eve", "p_dep", "mean_qber", "std_qber"],
    )

    print("[4/5] key rate curve")
    rate = experiment_key_rate_curve()
    write_csv(os.path.join(RESULTS_DIR, "key_rate.csv"), rate, ["qber", "rate"])

    print("[5/5] figures")
    import plots

    plots.make_all(sweep, noise, det, rate)
    print("done")


if __name__ == "__main__":
    main()
