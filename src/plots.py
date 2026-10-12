"""
Figures for EveSense.

Called by evesense.main() once every experiment has finished. Keeps the
matplotlib noise out of the protocol code.
"""

from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

RESULTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results"
)


def _save(fig: plt.Figure, name: str) -> None:
    path = os.path.join(RESULTS_DIR, name)
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {path}")


def _style() -> None:
    plt.rcParams.update({
        "figure.facecolor": "white",
        "axes.grid": True,
        "grid.alpha": 0.3,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "font.size": 11,
    })


def fig_interception(sweep: list[dict]) -> None:
    _style()
    p = [r["p_eve"] for r in sweep]
    q = [r["qber"] for r in sweep]
    ideal = [0.25 * x for x in p]

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(p, np.array(q) * 100, "o-", color="#1f77b4", label="simulated QBER")
    ax.plot(p, np.array(ideal) * 100, "--", color="#888", label="theoretical 25% * p")
    ax.set_xlabel("probability that Eve intercepts a round")
    ax.set_ylabel("quantum bit error rate (%)")
    ax.set_title("More interception, more errors. A clean channel makes it obvious.")
    ax.legend(frameon=False)
    _save(fig, "fig1_interception.png")


def fig_noise(noise: list[dict]) -> None:
    _style()
    p = [r["p_dep"] for r in noise]
    q = [r["qber"] for r in noise]

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(p, np.array(q) * 100, "s-", color="#d62728")
    ax.axhline(11, color="#444", linestyle=":", linewidth=1.2)
    ax.text(0.005, 11.4, "BB84 secrecy limit (~11%)", fontsize=9, color="#444")
    ax.set_xlabel("channel depolarising probability")
    ax.set_ylabel("quantum bit error rate (%)")
    ax.set_title("Fiber noise alone pushes the error rate up, without any attacker")
    _save(fig, "fig2_noise.png")


def fig_detection(det: list[dict]) -> None:
    _style()
    fig, ax = plt.subplots(figsize=(9, 5))

    colours = {
        "no eve": "#2ca02c",
        "p_eve=0.1": "#ff7f0e",
        "p_eve=0.3": "#d62728",
    }
    for idx, entry in enumerate(det):
        kind = "no eve" if entry["p_eve"] == 0 else (f"p_eve={entry['p_eve']}")
        samples = np.array(entry["samples"]) * 100
        jitter = np.random.default_rng(idx).normal(0, 0.05, len(samples))
        ax.scatter(np.full_like(samples, idx) + jitter, samples,
                   color=colours.get(kind, "#333"), s=26, alpha=0.9)
        ax.plot([idx - 0.2, idx + 0.2], [np.mean(samples)] * 2, color="black", linewidth=2)

    ax.set_xticks(range(len(det)))
    ax.set_xticklabels(
        [d["label"].replace(", ", "\n").replace("link", "link") for d in det],
        rotation=45, ha="right", fontsize=8,
    )
    ax.set_ylabel("measured QBER (%)")
    ax.axhline(11, color="#444", linestyle=":", linewidth=1.2)
    ax.text(len(det) - 0.4, 11.3, "secrecy limit", fontsize=8, color="#444", ha="right")
    ax.set_title("Where an eavesdropper disappears: 10% interception on a 7% noisy link")
    _save(fig, "fig3_detection.png")


def fig_roc(det: list[dict]) -> None:
    """Hit rate against false alarm rate, clean link and noisy link."""
    _style()
    clean_no_eve = next(d for d in det if d["label"] == "clean link, no eve")
    noisy_no_eve = next(d for d in det if d["label"] == "noisy link p=0.07, no eve")

    fig, ax = plt.subplots(figsize=(6.5, 5))
    scenarios = [
        ("clean channel, p_eve=0.1", clean_no_eve,
         next(d for d in det if d["label"] == "clean link, p_eve=0.1"), "#1f77b4"),
        ("clean channel, p_eve=0.3", clean_no_eve,
         next(d for d in det if d["label"] == "clean link, p_eve=0.3"), "#174a7e"),
        ("noisy channel, p_eve=0.1", noisy_no_eve,
         next(d for d in det if d["label"] == "noisy link p=0.07, p_eve=0.1"), "#ffbb78"),
        ("noisy channel, p_eve=0.3", noisy_no_eve,
         next(d for d in det if d["label"] == "noisy link p=0.07, p_eve=0.3"), "#9467bd"),
    ]
    for name, base, tapped, colour in scenarios:
        grid = np.linspace(
            min(base["samples"] + tapped["samples"]),
            max(base["samples"] + tapped["samples"]), 60
        )
        hit = [float(np.mean(np.array(tapped["samples"]) > t)) for t in grid]
        false = [float(np.mean(np.array(base["samples"]) > t)) for t in grid]
        ax.plot(false, hit, "-o", color=colour, markersize=3, label=name)

    ax.plot([0, 1], [0, 1], "--", color="#999", linewidth=1)
    ax.set_xlabel("false alarm rate")
    ax.set_ylabel("detection rate")
    ax.set_title("Detector performance drops on dirty fiber")
    ax.legend(frameon=False, fontsize=8)
    _save(fig, "fig4_roc.png")


def fig_key_rate(rate: list[dict]) -> None:
    _style()
    e = [r["qber"] * 100 for r in rate]
    r_ = [r["rate"] for r in rate]

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(e, r_, "-", color="#2ca02c", linewidth=2)
    ax.axvline(11, color="#d62728", linestyle=":", linewidth=1.5)
    ax.text(11.3, 0.55, "secrecy breaks", color="#d62728", fontsize=9)
    ax.set_xlabel("QBER (%)")
    ax.set_ylabel("secure key rate (bits per sifted bit)")
    ax.set_title("The key is worthless once error correction eats everything")
    _save(fig, "fig5_key_rate.png")


def make_all(sweep, noise, det, rate) -> None:
    fig_interception(sweep)
    fig_noise(noise)
    fig_detection(det)
    fig_roc(det)
    fig_key_rate(rate)

# ---
# This document was developed with the assistance of generative AI tools for research, structuring, and content generation. Final content has been reviewed and validated by the author. Full compliance with: Reg. (EU) 2024/1689 (AI Act) Art. 50 - Italian Law 132/2025 Art. 13 - EU Code of Practice on AI Transparency (2026) - U.S. AI Labeling Act (S. 4915) - U.S. H.R.8479 - U.S. Executive Order on AI (Dec 2025) - California TFAIA & AB 2013 (eff. Jan 2026).
