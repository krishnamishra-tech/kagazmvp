"""
Reference implementation: mapping/render layer.

Takes a canonical profile (dict) + a form template (JSON, like
forms/income_certificate_UP.json) and produces a filled PDF.

Two rendering strategies are supported:
  - "overlay": form's govt PDF is a flat scan (no fillable fields) ->
    we draw text at fixed (x, y) coordinates on a transparent layer,
    then merge it onto the original PDF. Works for almost any govt PDF.
  - "acroform": the govt PDF already has fillable form fields (rare but
    some e-Sathi/RTPS PDFs do) -> fill those fields directly, more robust
    than coordinate guessing.

Install: pip install pypdf reportlab --break-system-packages
"""

import json
from datetime import datetime
from io import BytesIO

from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4


def apply_transform(value, transform):
    if transform is None or value is None:
        return value
    if transform == "title_case":
        return str(value).title()
    if transform == "date_ddmmyyyy":
        # profile stores dates as YYYY-MM-DD; govt forms usually want DD-MM-YYYY
        try:
            return datetime.strptime(value, "%Y-%m-%d").strftime("%d-%m-%Y")
        except ValueError:
            return value
    if transform == "wrap_2line":
        # crude wrap for long addresses drawn at fixed coordinates
        words = str(value).split()
        mid = len(words) // 2
        return " ".join(words[:mid]) + "\n" + " ".join(words[mid:])
    return value


def resolve_field_value(profile: dict, field: dict):
    canonical_key = field["canonical"]
    value = profile.get(canonical_key)
    if value is None:
        if field.get("required"):
            raise ValueError(
                f"Required field '{canonical_key}' missing from profile "
                f"for form field '{field['id']}'."
            )
        return None
    return apply_transform(value, field.get("transform"))


def render_overlay(template: dict, profile: dict, output_path: str):
    """Draw resolved field values at their fixed coordinates, then merge
    that layer onto the original government PDF template."""

    overlay_buffer = BytesIO()
    c = canvas.Canvas(overlay_buffer, pagesize=A4)
    c.setFont("Helvetica", 11)

    for field in template["fields"]:
        value = resolve_field_value(profile, field)
        if value is None:
            continue
        x, y = field["coordinates"]
        for i, line in enumerate(str(value).split("\n")):
            c.drawString(x, y - (i * 14), line)

    c.save()
    overlay_buffer.seek(0)

    base_pdf = PdfReader(template["pdf_template"])
    overlay_pdf = PdfReader(overlay_buffer)

    writer = PdfWriter()
    base_page = base_pdf.pages[0]
    base_page.merge_page(overlay_pdf.pages[0])
    writer.add_page(base_page)

    with open(output_path, "wb") as f:
        writer.write(f)


def collect_confirmation_fields(template: dict, profile: dict):
    """Fields the user must explicitly confirm before this form is
    generated - either because extraction confidence was low/medium, or
    because the field is legally load-bearing (income, caste_category)."""
    to_confirm = []
    for field in template["fields"]:
        if field.get("user_must_confirm"):
            to_confirm.append({
                "field_id": field["id"],
                "label_hi": field.get("label_hi"),
                "current_value": profile.get(field["canonical"]),
            })
    return to_confirm


if __name__ == "__main__":
    with open("forms/income_certificate_UP.json", encoding="utf-8") as f:
        template = json.load(f)

    # Example profile - in production this comes from the merged
    # extraction output, not hardcoded.
    example_profile = {
        "name": "ramesh kumar",
        "father_name": "suresh kumar",
        "dob": "1998-04-12",
        "address_line1": "village rampur, dist gorakhpur",
        "district": "Gorakhpur",
        "tehsil": "Sadar",
        "occupation": "Farmer",
        "annual_income": 85000,
        "mobile": "9876543210",
    }

    confirmations = collect_confirmation_fields(template, example_profile)
    print("Fields requiring user confirmation before fill:", confirmations)

    render_overlay(template, example_profile, "output_income_certificate.pdf")
    print("Filled PDF written to output_income_certificate.pdf")
