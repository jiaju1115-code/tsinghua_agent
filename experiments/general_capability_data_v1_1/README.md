# General Capability Data Acquisition V1.1

Actual selective acquisition via the official Hugging Face Dataset Server. It downloads only bounded training rows from OASST1, MathInstruct, and GEmO, preserves raw selected rows and provenance, filters and deduplicates candidates, and never touches benchmark eval splits or Campus assets. Run `python src/acquire.py`.
