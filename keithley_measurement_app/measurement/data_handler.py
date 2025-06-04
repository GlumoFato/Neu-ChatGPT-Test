"""Utility functions for exporting measurement data."""

import csv


def export_to_csv(filename: str, rows):
    """Write rows of data to a CSV file."""
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerows(rows)
