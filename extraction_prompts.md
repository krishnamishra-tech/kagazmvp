# Extraction prompts — vision layer

One prompt per source document type. Each returns JSON matching a subset of
`canonical_profile_schema.json`. Keep these strict about masking sensitive
numbers — the mask happens *in the prompt*, not as a later cleanup step, so
full numbers never enter your logs, DB, or model context in the first place.

---

## Aadhaar card

```
You are extracting fields from a photo of an Indian Aadhaar card.
Return ONLY a JSON object, no other text, with these exact keys:

{
  "name": string,
  "name_hindi": string or null,
  "dob": string in YYYY-MM-DD format, or null if only age is shown,
  "gender": "male" | "female" | "other",
  "address_line1": string,
  "address_line2": string or null,
  "village_town": string or null,
  "tehsil": string or null,
  "district": string,
  "state": string,
  "pincode": string,
  "aadhaar_last4": string — ONLY the last 4 digits of the Aadhaar number,
      never return the full 12-digit number under any circumstances,
  "confidence": { "<field_name>": "high"|"medium"|"low", ... }
}

If any field is not clearly legible, set it to null and mark its confidence
as "low" rather than guessing. Do not infer a field from context — only
report what is visibly printed on the card.
```

---

## Marksheet / educational certificate

```
Extract fields from this photo of a marksheet or educational certificate.
Return ONLY this JSON object:

{
  "name": string,
  "father_name": string or null,
  "mother_name": string or null,
  "dob": string in YYYY-MM-DD format, or null,
  "institution_name": string,
  "roll_no": string or null,
  "year_of_passing": number or null,
  "highest_qualification": string (e.g. "10th", "12th", "B.A."),
  "confidence": { "<field_name>": "high"|"medium"|"low", ... }
}

Set any illegible field to null with "low" confidence instead of guessing.
```

---

## Old government certificate (income / caste / domicile — for re-issue or reference)

```
Extract fields from this photo of a previously issued government certificate.
Return ONLY this JSON object:

{
  "certificate_type": "income" | "caste" | "domicile" | "other",
  "name": string,
  "father_name": string or null,
  "caste_category": "general"|"obc"|"sc"|"st"|"ews"|null,
  "annual_income": number or null,
  "issuing_authority": string or null,
  "issue_date": string in YYYY-MM-DD format, or null,
  "certificate_number": string or null,
  "confidence": { "<field_name>": "high"|"medium"|"low", ... }
}

This document may be old, low-resolution, or partially damaged — set fields
to null with "low" confidence rather than guessing at damaged/unclear text.
```

---

## Ration card

```
Extract fields from this photo of a ration card.
Return ONLY this JSON object:

{
  "ration_card_no": string,
  "family_members": [
    { "name": string, "relation": string, "dob": string or null }
  ],
  "address_line1": string,
  "district": string,
  "state": string,
  "bpl_status": boolean or null,
  "confidence": { "<field_name>": "high"|"medium"|"low", ... }
}
```

---

## Bank passbook / cheque (for PM-Kisan, scholarships)

```
Extract fields from this photo of a bank passbook front page or cheque.
Return ONLY this JSON object:

{
  "bank_account_last4": string — ONLY last 4 digits, never the full account number,
  "ifsc": string,
  "bank_name": string,
  "confidence": { "<field_name>": "high"|"medium"|"low", ... }
}
```

---

## Merge logic (profile assembly)

After extraction, merge into the canonical profile with these rules:

1. **Never overwrite a "high" confidence field with a "low" confidence one**
   from a different document — flag the conflict for user review instead.
2. **Any field with confidence "low" or "medium" is shown to the user for
   confirmation** before it's used in a form fill — never silently trusted.
3. **Fields marked `user_must_confirm` in the canonical schema** (income,
   caste_category) are *always* shown for confirmation regardless of
   extraction confidence, since these carry legal weight on the form.
4. If two documents disagree on a field (e.g. name spelled differently on
   Aadhaar vs marksheet), surface both values and ask the user which is
   correct for this specific form — don't auto-pick either.
