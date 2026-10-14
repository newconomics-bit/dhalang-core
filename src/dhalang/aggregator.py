"""Manunggal aggregator - combines Wayang results into final answer."""

import json
from typing import List

from src.sabda.models import WayangResult, WayangStatus


class Manunggal:
    """Aggregates multiple WayangResults into a single human-readable answer."""

    def satukan(self, results: List[WayangResult], user_input: str) -> str:
        """Combine all results into a final answer.

        Args:
            results: List of WayangResult from agents.
            user_input: Original user input for context.

        Returns:
            Formatted final answer string.
        """
        if not results:
            return self._empty_response(user_input)

        lines = []

        # Opening line
        lines.append("=" * 60)
        lines.append(f"HASIL PROSES: {user_input}")
        lines.append("=" * 60)
        lines.append("")

        # Each result
        for i, result in enumerate(results, 1):
            lines.append(f"--- Agent {i}: {result.agent} ---")
            lines.append(f"Status: {result.status.value}")

            # Format result as JSON with indent
            if result.result:
                lines.append("Hasil:")
                formatted_result = json.dumps(result.result, indent=2, ensure_ascii=False)
                for line in formatted_result.split('\n'):
                    lines.append(f"  {line}")

            # Notes if present
            if result.notes:
                lines.append(f"Catatan: {result.notes}")

            lines.append("")

        # Closing line
        lines.append("=" * 60)
        failed_count = sum(1 for r in results if r.status == WayangStatus.FAILED)
        if failed_count == 0:
            lines.append("Proses selesai. Semua tugas telah diselesaikan.")
        else:
            lines.append(f"Proses selesai dengan catatan: {failed_count} agen gagal.")
        lines.append("=" * 60)

        return "\n".join(lines)

    def _empty_response(self, user_input: str) -> str:
        """Generate response when no results available."""
        lines = []
        lines.append("=" * 60)
        lines.append(f"HASIL PROSES: {user_input}")
        lines.append("=" * 60)
        lines.append("")
        lines.append("Tidak ada hasil dari agen. Mungkin antrian kosong atau")
        lines.append("tidak ada agen yang tersedia untuk menangani request ini.")
        lines.append("")
        lines.append("=" * 60)
        lines.append("Proses selesai (tanpa hasil).")
        lines.append("=" * 60)
        return "\n".join(lines)