"""
Builds the submission deck (report/evesense_deck.pptx) from the figures
that evesense.py produced. Needs python-pptx, which is not part of the
simulation requirements.
"""

import os

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Inches, Pt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(ROOT, "results")
OUT = os.path.join(ROOT, "report", "evesense_deck.pptx")

INK = RGBColor(0x1A, 0x1A, 0x1A)
ACCENT = RGBColor(0x1F, 0x4E, 0x79)
MUTED = RGBColor(0x66, 0x66, 0x66)


def blank(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])


def textbox(slide, left, top, width, height, text, size=18, bold=False,
            colour=INK, space_after=10):
    """Add a text box. A blank line starts a new paragraph, a single newline
    inside a block becomes a tight line break."""
    box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = box.text_frame
    tf.word_wrap = True
    used = False
    for block in text.split("\n\n"):
        lines = block.split("\n")
        for li, line in enumerate(lines):
            if not used:
                para = tf.paragraphs[0]
                used = True
            else:
                para = tf.add_paragraph()
            run = para.add_run()
            run.text = line.strip()
            run.font.size = Pt(size)
            run.font.bold = bold
            run.font.color.rgb = colour
            para.space_after = Pt(space_after if li == len(lines) - 1 else 2)
    return box


def title_slide(prs):
    s = blank(prs)
    textbox(s, 0.7, 1.9, 8.6, 1.2, "EveSense", size=52, bold=True, colour=ACCENT)
    textbox(s, 0.7, 3.0, 8.6, 1.6,
            "Catching an eavesdropper on a BB84 link that is already noisy",
            size=22)
    textbox(s, 0.7, 4.3, 8.6, 1.4,
            "Chiara De Venuto - Team ChiaraDev\n\nQiskit Fall Fest 2026 @ MPSTME, IBM Quantum\n\n"
            "Quantum Secure Communication track",
            size=14, colour=MUTED)


def slide_problem(prs):
    s = blank(prs)
    textbox(s, 0.7, 0.5, 8.6, 0.8, "The question", size=30, bold=True, colour=ACCENT)
    textbox(s, 0.7, 1.5, 8.6, 5.2,
            "BB84 security rests on one fact: measuring a qubit in the wrong basis\n"
            "disturbs it. An intercept-resend attacker inserts errors, the two ends\n"
            "read those errors as QBER, and above roughly 11% QBER the link stops\n"
            "producing usable key.\n\n"
            "Deployed fiber is never clean. Raman scattering, dark counts and\n"
            "polarization drift put real links at a few percent QBER with nobody\n"
            "listening. So the receiver is not comparing a measurement against\n"
            "zero. It is comparing against a baseline that moves.\n\n"
            "Eve knows the baseline. A patient attacker keeps her interception\n"
            "rate under the noise floor. The receiver has one number and one\n"
            "threshold, and has to decide whether a rise in QBER is Eve or the\n"
            "weather.",
            size=16)


def slide_approach(prs):
    s = blank(prs)
    textbox(s, 0.7, 0.5, 8.6, 0.8, "What we built", size=30, bold=True, colour=ACCENT)
    textbox(s, 0.7, 1.5, 8.6, 5.4,
            "A BB84 link in Qiskit with a tunable attacker and a tunable channel,\n"
            "then a detection study across nine conditions.\n\n"
            "One round is one qubit: Alice prepares |0>, |1>, |+> or |->, Eve\n"
            "intercept-measures and resends when she is active, the channel adds\n"
            "depolarizing and readout noise, Bob measures in the basis he picked.\n\n"
            "Rounds are packed into batches of 64 qubits in a single stabilizer\n"
            "circuit, so 30000 rounds cost milliseconds. Eve's outcome is drawn\n"
            "from the Born rule, which is what a mid-circuit measure-and-resend\n"
            "gives.\n\n"
            "Four experiments: interception sweep, channel noise sweep, detection\n"
            "study with 12 repeats per condition, and the secure key rate curve.",
            size=16)


def figure_slide(prs, title, img, caption):
    s = blank(prs)
    textbox(s, 0.7, 0.4, 8.6, 0.7, title, size=26, bold=True, colour=ACCENT)
    s.shapes.add_picture(os.path.join(RESULTS, img), Inches(0.7), Inches(1.25),
                         height=Inches(4.4))
    textbox(s, 0.7, 5.85, 8.6, 1.3, caption, size=13, colour=MUTED)


def slide_findings(prs):
    s = blank(prs)
    textbox(s, 0.7, 0.5, 8.6, 0.8, "What the numbers say", size=30, bold=True, colour=ACCENT)
    textbox(s, 0.7, 1.5, 8.6, 5.2,
            "On a clean link the protocol behaves exactly as theory predicts: QBER\n"
            "tracks 25% of the interception probability, and the measured curve\n"
            "sits on the analytical one.\n\n"
            "A 7% depolarizing channel on its own produces about 7% QBER. That\n"
            "is the same order of magnitude as a 10% interception rate on clean\n"
            "fiber. The receiver cannot tell those two apart from a single\n"
            "measurement.\n\n"
            "The ROC curves show the tradeoff. On clean fiber almost any\n"
            "threshold separates tapped from untapped. On dirty fiber the curve\n"
            "collapses toward the diagonal at low interception rates, which is\n"
            "where a patient attacker works.\n\n"
            "Past about 11% QBER error correction and privacy amplification take\n"
            "everything. The link stays up and stops being worth anything.",
            size=15)


def slide_limits(prs):
    s = blank(prs)
    textbox(s, 0.7, 0.5, 8.6, 0.8, "Limits and next steps", size=30, bold=True, colour=ACCENT)
    textbox(s, 0.7, 1.5, 8.6, 5.2,
            "Eve here is a textbook intercept-resend attacker. Photon-number-\n"
            "splitting and coherent attacks are not in the model, and nothing in\n"
            "this work is a security proof.\n\n"
            "The channel is depolarizing plus symmetric readout noise. Real fiber\n"
            "drifts in polarization and loses differently per wavelength.\n\n"
            "The detector is a single threshold. A real receiver discloses part of\n"
            "the key, estimates QBER on that subset and adapts the threshold\n"
            "against a measured baseline instead of a fixed number.\n\n"
            "The next version of this work would estimate the baseline online and\n"
            "run the detection on the residual, which is the version that would\n"
            "survive contact with a real link.",
            size=15)


def slide_disclosure(prs):
    s = blank(prs)
    textbox(s, 0.7, 0.5, 8.6, 0.8, "Disclosure", size=30, bold=True, colour=ACCENT)
    textbox(s, 0.7, 1.8, 8.6, 4.0,
            "This project was developed with the assistance of generative AI "
            "tools for research,\nstructuring and content generation. The "
            "final content has been reviewed and\nvalidated by the author.\n\n"
            "Full compliance with:\n"
            "Reg. (EU) 2024/1689 (AI Act) Art. 50\n"
            "Italian Law 132/2025 Art. 13\n"
            "EU Code of Practice on AI Transparency (2026)\n"
            "U.S. AI Labeling Act (S. 4915) - U.S. H.R.8479\n"
            "U.S. Executive Order on AI (Dec 2025)\n"
            "California TFAIA & AB 2013 (eff. Jan 2026)",
            size=15, colour=MUTED)


def main():
    prs = Presentation()
    prs.slide_width = Inches(10)
    prs.slide_height = Inches(7.5)

    title_slide(prs)
    slide_problem(prs)
    slide_approach(prs)
    figure_slide(
        prs, "Clean channel, tunable attacker",
        "fig1_interception.png",
        "Interception sweep. The simulated points fall on the analytical "
        "25% * p line, which is the sanity check every QKD demo should "
        "pass before claiming anything.")
    figure_slide(
        prs, "The baseline she hides in",
        "fig2_noise.png",
        "Channel noise with no attacker. By 12% depolarising probability "
        "the link crosses the 11% secrecy limit on its own.")
    figure_slide(
        prs, "Nine conditions, twelve runs each",
        "fig3_detection.png",
        "QBER distributions per condition. The overlap between a tapped "
        "noisy link and an untapped noisy link is the whole problem.")
    figure_slide(
        prs, "Detection cost",
        "fig4_roc.png",
        "Hit rate against false alarm rate. The noisy-channel curves fall "
        "toward the diagonal exactly where the attacker is quietest.")
    slide_findings(prs)
    slide_limits(prs)
    slide_disclosure(prs)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    prs.save(OUT)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()

# ---
# This document was developed with the assistance of generative AI tools for research, structuring, and content generation. Final content has been reviewed and validated by the author. Full compliance with: Reg. (EU) 2024/1689 (AI Act) Art. 50 - Italian Law 132/2025 Art. 13 - EU Code of Practice on AI Transparency (2026) - U.S. AI Labeling Act (S. 4915) - U.S. H.R.8479 - U.S. Executive Order on AI (Dec 2025) - California TFAIA & AB 2013 (eff. Jan 2026).
