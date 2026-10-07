"""@package partsmith.gui.symbol_panel
@brief Inspects the bound generated symbol inside the separate viewer.
@details Native preview, exact bytes, actual pins and mapping diagnostics are
read-only; missing data remains visible without blocking placement inspection.
"""

import wx
import wx.svg
from wx.lib.scrolledpanel import ScrolledPanel

from .artifact_panel import SVGPreview
from .symbol_inspection import bound_symbol


class SymbolInspectionPanel(ScrolledPanel):
    """@brief Hosts symbol drawing and actual pin-to-pad inspection.
    @details The report remains bound to the viewer snapshot after new work.
    """

    def __init__(self, parent, viewer):
        """@brief Builds a read-only review of the displayed attempt's symbol.
        @param parent Viewer review notebook.
        @param viewer Owned viewer with immutable source and binding metadata.
        @return None.
        @details An unavailable or malformed symbol leaves the 3D page usable.
        """
        super().__init__(parent)
        self.report = None
        self.binding = dict(viewer.binding)
        layout = wx.BoxSizer(wx.VERTICAL)
        self.summary = wx.StaticText(self)
        layout.Add(self.summary, 0, wx.EXPAND | wx.ALL, 6)
        self.preview = SVGPreview(self)
        self.preview.SetMinSize((220, 240))
        layout.Add(self.preview, 0, wx.EXPAND | wx.ALL, 6)
        layout.Add(
            wx.StaticText(
                self, label="Actual symbol pins → footprint pads (by number)"
            ),
            0,
            wx.ALL,
            6,
        )
        self.pins = wx.ListCtrl(self, style=wx.LC_REPORT)
        for index, (label, width) in enumerate(
            (
                ("Pin", 55),
                ("Name", 110),
                ("Electrical type", 110),
                ("Pad", 65),
                ("Comparison with reviewed IR / footprint", 330),
            )
        ):
            self.pins.InsertColumn(index, label, width=width)
        self.pins.SetMinSize((220, 150))
        self.pins.Bind(wx.EVT_LIST_ITEM_SELECTED, self.select_pin)
        layout.Add(self.pins, 0, wx.EXPAND | wx.ALL, 6)
        self.results = wx.TextCtrl(
            self, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL
        )
        self.results.SetMinSize((-1, 115))
        layout.Add(self.results, 0, wx.EXPAND | wx.ALL, 6)
        layout.Add(
            wx.StaticText(self, label="Exact generated symbol bytes"),
            0,
            wx.ALL,
            6,
        )
        self.bytes = wx.TextCtrl(
            self, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL
        )
        self.bytes.SetMinSize((-1, 160))
        layout.Add(self.bytes, 0, wx.EXPAND | wx.ALL, 6)
        self.viewer = viewer
        try:
            self.report = bound_symbol(
                viewer.GetParent().session,
                viewer.binding,
                viewer.inspection.pads,
            )
            self.display_report()
        except (
            ValueError,
            OSError,
            KeyError,
            TypeError,
            RuntimeError,
        ) as error:
            self.results.ChangeValue(f"Symbol inspection unavailable: {error}")
            viewer.log(f"[symbol inspection] {error}")
        self.mark_current(viewer.binding["stale"])
        self.SetSizer(layout)
        self.SetupScrolling(scroll_x=False)
        self.Bind(wx.EVT_SIZE, self.resize)

    def resize(self, event):
        """@brief Fits the page width while retaining vertical scrolling.
        @param event Symbol inspection page resize event.
        @return None.
        @details Shrinking a notebook page never retains an oversized preview.
        """
        width, height = self.GetClientSize()
        self.SetVirtualSize(
            (width, max(height, self.GetSizer().GetMinSize().height))
        )
        self.Layout()
        event.Skip()

    def display_report(self):
        """@brief Displays exact properties, pins, validation and native SVG.
        @return None.
        @details Preview display failure preserves textual inspection.
        """
        report = self.report
        self.bytes.ChangeValue(report["content"].decode("utf-8"))
        for row in report["mapping"]:
            index = self.pins.InsertItem(
                self.pins.GetItemCount(), row["number"]
            )
            for column, key in enumerate(
                ("name", "electrical_type", "pad", "diagnostic"), start=1
            ):
                self.pins.SetItem(index, column, row[key])
        lines = [f"Symbol: {report['name']}"]
        lines.extend(
            f"{key}: {value}" for key, value in report["properties"].items()
        )
        lines.append(
            "Mapping comparisons are display diagnostics; "
            "retained validators govern release."
        )
        lines.append("Retained checks bound to these symbol bytes:")
        lines.extend(
            f"{item['status']}  {item['rule_id']}: {item.get('message', '')}"
            for item in report["validation"]
        )
        if not report["validation"]:
            lines.append("No retained checks for these bytes.")
        if report["preview"] is not None:
            try:
                self.preview.svg = wx.svg.SVGimage.CreateFromBytes(
                    report["preview"]
                )
            except Exception:
                lines.append("Native symbol preview could not be displayed.")
                self.viewer.log("[symbol inspection] SVG_DISPLAY_ERROR")
        else:
            lines.append("Native symbol preview unavailable for this binding.")
        if report["preview_error"]:
            lines.append(f"Native preview error: {report['preview_error']}")
        self.results.ChangeValue("\n".join(lines))
        self.preview.Refresh()

    def mark_current(self, stale):
        """@brief Updates stale labeling without replacing retained content.
        @param stale Whether the displayed build or revision is outdated.
        @return None.
        @details No session, engineering bytes or decisions are written.
        """
        label = "STALE — " if stale else ""
        digest = (
            self.report["artifact"]["sha256"] if self.report else "Unavailable"
        )
        self.summary.SetLabel(
            f"{label}{self.binding['stage']} symbol / "
            f"build {self.binding['build_id']}\n"
            f"Revision {self.binding['revision_id']}\nSHA-256: {digest}\n"
            "Inspection does not grant release approval."
        )

    def select_pin(self, event):
        """@brief Highlights the selected symbol pin's existing footprint pad.
        @param event Selected actual mapping row event.
        @return None.
        @details Selection changes only display state, preserving pin data.
        """
        if self.report is None:
            return
        row = self.report["mapping"][event.GetIndex()]
        number = row["pad"]
        if self.viewer.inspection.first.SetStringSelection(number):
            self.viewer.inspection.measure(None)
