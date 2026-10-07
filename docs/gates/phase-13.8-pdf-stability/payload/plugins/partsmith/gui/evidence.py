"""@package partsmith.gui.evidence
@brief Presents retained source evidence and deliberately selected AI requests.
@details Original text and coordinates remain inspectable beside unreviewed
provider candidates; previews never grant engineering acceptance.
"""

from __future__ import annotations

import copy
import re

from partsmith.ai import AIRequest
from partsmith.extraction.coordinates import overlay_box


def parse_pages(text):
    """@brief Parses explicit one-based page and range selection.
    @param text All Pages or comma-separated numbers and inclusive ranges.
    @return Sorted unique page list or None for all pages.
    @details Rejects zero, duplicates and malformed selections without cuts.
    """
    if text.strip().casefold() == "all pages":
        return None
    pages = []
    for item in text.split(","):
        if not re.fullmatch(r"\s*[1-9]\d*(?:\s*-\s*[1-9]\d*)?\s*", item):
            raise ValueError("Use All Pages or one-based pages such as 1,3-5")
        ends = [int(value.strip()) for value in item.split("-")]
        if len(ends) == 2:
            if ends[1] < ends[0] or ends[1] > 5000:
                raise ValueError(
                    "Invalid page range; maximum page number is 5000"
                )
            pages.extend(range(ends[0], ends[1] + 1))
        else:
            pages.append(ends[0])
    if not pages or len(pages) != len(set(pages)) or max(pages) > 5000:
        raise ValueError("Select unique one-based pages up to 5000")
    return sorted(pages)


def selected_request(session, task, evidence_ids, targets=(), language="en"):
    """@brief Constructs the exact deliberate provider request.
    @param session Retained local extraction session.
    @param task Supported interpretation task.
    @param evidence_ids Explicitly selected immutable evidence identities.
    @param targets Trusted engineering target paths selected for this task.
    @param language Translation target language.
    @return Validated AIRequest including its canonical byte snapshot.
    @details The adapter enforces 1-128 records and 512 KiB without truncation.
    """
    if not evidence_ids:
        raise ValueError(
            "Select evidence records before requesting AI interpretation"
        )
    extraction = session.display_extraction()
    if extraction is None:
        extraction = session.extraction()
    if extraction is None:
        raise ValueError(
            "Extract local evidence before requesting interpretation"
        )
    return AIRequest.from_extraction(
        extraction,
        task,
        session.state["setup"]["part_number"],
        evidence_ids,
        targets,
        language,
    )


def evidence_overlay(extraction, evidence):
    """@brief Maps an original source region into its retained page image.
    @param extraction Complete retained extraction metadata.
    @param evidence Selected original evidence record.
    @return Render transform and overlay rectangle in original image pixels.
    @details Native text uses the page render; rotation, crop and DPI mappings
    are taken from extraction rather than guessed from displayed dimensions.
    """
    source = copy.deepcopy(evidence["source"])
    if source["region"] is None:
        return None, None
    if source["render_transform"] is None:
        page = next(
            item
            for item in extraction["pages"]
            if item["page"] == source["page"]
        )
        source["render_transform"] = page["render_transform"]
    return source["render_transform"], overlay_box(source)
