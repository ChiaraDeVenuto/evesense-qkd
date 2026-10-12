"""
Builds report/project_description.docx (and the PDF that goes with it).
python-docx gives us real column widths, which HTML import does not.
"""

import os

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT = os.path.join(ROOT, "report")
OUT = os.path.join(REPORT, "project_description.docx")

ACCENT = RGBColor(0x1F, 0x4E, 0x79)
GREY = RGBColor(0x55, 0x55, 0x55)


def heading(doc, text, size=13):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.bold = True
    run.font.size = Pt(size)
    run.font.color.rgb = ACCENT
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(3)
    return p


def body(doc, text, size=11, colour=None, space_after=8):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.size = Pt(size)
    if colour is not None:
        run.font.color.rgb = colour
    p.paragraph_format.space_after = Pt(space_after)
    return p


def build():
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

    for section in doc.sections:
        section.top_margin = Inches(0.85)
        section.bottom_margin = Inches(0.85)
        section.left_margin = Inches(0.95)
        section.right_margin = Inches(0.95)

    p = doc.add_paragraph()
    run = p.add_run("EveSense")
    run.bold = True
    run.font.size = Pt(24)
    run.font.color.rgb = ACCENT
    p.paragraph_format.space_after = Pt(2)

    body(doc, "Eavesdropper detection on a simulated BB84 link that is already noisy",
         size=12, space_after=2)
    body(doc, "Team ChiaraDev | Chiara De Venuto | Qiskit Fall Fest 2026 @ MPSTME, "
              "IBM Quantum", size=10, colour=GREY, space_after=4)

    heading(doc, "Problem addressed")
    body(doc,
         "BB84 gets its security from physics: measuring a qubit in the wrong basis "
         "disturbs it. An intercept-resend attacker inserts errors, and the two ends "
         "read those errors as a rising quantum bit error rate (QBER). Above roughly "
         "11% QBER the link stops producing usable key.")
    body(doc,
         "Deployed fiber is never clean. Raman scattering, detector dark counts and "
         "polarization drift put real links at a few percent QBER with nobody "
         "listening. So the receiver is not comparing a measurement against zero. It "
         "is comparing against a baseline that drifts, and it has to decide whether a "
         "rise in QBER is an attacker or the weather. That is a detection problem "
         "with a hit rate and a false alarm rate, and this project treats it that way.")

    heading(doc, "Quantum approach and Qiskit implementation")
    body(doc,
         "One BB84 round is one qubit. Alice prepares |0>, |1>, |+> or |-> from her "
         "bit and her basis choice. Eve, when active, intercepts, measures in her own "
         "basis and resends the state her measurement implies. The channel adds "
         "depolarizing noise on the gates and readout noise on the detectors. Bob "
         "measures in the basis he picked before the round started.")
    body(doc,
         "Rounds are packed into batches of 64 qubits inside a single circuit, so "
         "30000 rounds cost milliseconds. Aer's stabilizer method handles the whole "
         "circuit, which is legitimate here because every gate used is Clifford. "
         "Eve's measurement outcome is drawn from the Born rule, which is exactly "
         "what a mid-circuit measure-and-resend produces.")
    body(doc,
         "Built on Qiskit 2.5.2 and Qiskit Aer 0.17.2. Seeded throughout, so every "
         "figure in the repository reproduces exactly.")

    heading(doc, "Experiments")
    rows = [
        ("Experiment", "What it varies", "Rounds"),
        ("Interception sweep", "Eve's interception probability, 0 to 1, clean channel", "30000"),
        ("Channel noise sweep", "Depolarizing probability, 0 to 20%, no attacker", "30000"),
        ("Detection study", "9 conditions, 12 independent runs each", "1.3 million"),
        ("Key rate curve", "QBER against secure key rate", "closed form"),
    ]
    table = doc.add_table(rows=len(rows), cols=3)
    table.style = "Table Grid"
    widths = [Inches(1.5), Inches(3.3), Inches(1.0)]
    for ri, row in enumerate(rows):
        for ci, cell_text in enumerate(row):
            cell = table.cell(ri, ci)
            cell.width = widths[ci]
            para = cell.paragraphs[0]
            run = para.add_run(cell_text)
            run.font.size = Pt(10)
            run.bold = ri == 0
            if ri == 0:
                shading = cell._tc.get_or_add_tcPr()
                from docx.oxml.ns import qn
                from docx.oxml import OxmlElement
                shd = OxmlElement("w:shd")
                shd.set(qn("w:fill"), "EEF3F8")
                shading.append(shd)

    heading(doc, "Results")
    body(doc,
         "On a clean link the simulated QBER tracks the analytical prediction of 25% "
         "times the interception probability. The measured value at full interception "
         "is 0.2523 against a theoretical 0.25, which is the sanity check a QKD "
         "implementation has to pass before anything else it reports means anything.")
    body(doc,
         "Channel noise moves the same metric by the same order of magnitude. A 7% "
         "depolarizing channel produces about 7% QBER with nobody listening, and by "
         "12% the link crosses the 11% secrecy limit on its own.")
    body(doc,
         "The detection study is where the result lives. On a 7% noisy link with no "
         "attacker we measure 8.3% QBER with a standard deviation of 0.9. With the "
         "same link tapped at 10% interception probability we measure 10.3% with a "
         "standard deviation of 0.5. The distributions touch. A receiver with one "
         "threshold cannot separate them without paying either missed detections or "
         "false alarms, and the ROC curves show exactly that tradeoff: on clean fiber "
         "the detector separates tapped from untapped at almost any threshold, on "
         "dirty fiber the curve collapses toward the diagonal at low interception "
         "rates.")

    heading(doc, "Analysis and impact")
    body(doc,
         "The numbers point at a tradeoff rather than a fix. A quiet attacker stays "
         "under the noise floor, and no threshold on a single QBER measurement "
         "separates her from a bad day on the fiber. This is why real QKD deployments "
         "spend their budget making the link clean instead of making the detector "
         "clever: the security proof bounds the attacker, not the weather.")

    heading(doc, "Limitations and future scope")
    body(doc,
         "Eve here is a textbook intercept-resend attacker. Photon-number-splitting "
         "and coherent attacks are not modeled, and nothing in this work is a "
         "security proof. The channel is depolarizing plus symmetric readout noise, "
         "while real fiber drifts in polarization and loses differently per "
         "wavelength. The next version would estimate the baseline online and run "
         "detection on the residual error, which is the version that would survive "
         "contact with a real link.")

    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(16)
    run = p.add_run(
        "This document was developed with the assistance of generative AI tools for "
        "research, structuring, and content generation. Final content has been "
        "reviewed and validated by the author. Full compliance with: Reg. (EU) "
        "2024/1689 (AI Act) Art. 50 | Italian Law 132/2025 Art. 13 | EU Code of "
        "Practice on AI Transparency (2026) | U.S. AI Labeling Act (S. 4915) | U.S. "
        "H.R.8479 | U.S. Executive Order on AI (Dec 2025) | California TFAIA & AB "
        "2013 (eff. Jan 2026).")
    run.font.size = Pt(8)
    run.font.color.rgb = GREY

    os.makedirs(REPORT, exist_ok=True)
    doc.save(OUT)
    print("wrote", OUT)


if __name__ == "__main__":
    build()

# ---
# This document was developed with the assistance of generative AI tools for research, structuring, and content generation. Final content has been reviewed and validated by the author. Full compliance with: Reg. (EU) 2024/1689 (AI Act) Art. 50 - Italian Law 132/2025 Art. 13 - EU Code of Practice on AI Transparency (2026) - U.S. AI Labeling Act (S. 4915) - U.S. H.R.8479 - U.S. Executive Order on AI (Dec 2025) - California TFAIA & AB 2013 (eff. Jan 2026).
