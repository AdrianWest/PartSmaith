"""@package partsmith.gui.inspection
@brief Provides display-only layer, camera and measurement controls.
@details Measurements describe actual footprint coordinates or tessellated
STEP bounds, with explicit millimetre units and a declared mesh tolerance.
"""

import math

import wx

from partsmith.ir.canonical import canonical_json

PRESETS = {
    "Top": (0, 90),
    "Bottom": (0, -90),
    "Front": (0, 0),
    "Back": (180, 0),
    "Left": (90, 0),
    "Right": (-90, 0),
    "Isometric": (35, 28),
}
LAYERS = {
    "body": "3D body",
    "pads": "Pads",
    "silk": "Silkscreen",
    "courtyard": "Courtyard",
    "fab": "Fabrication",
    "origin": "Origin",
    "axes": "Axes",
    "pin1": "Pin 1",
}


def distance_mm(pads, first, second):
    """@brief Measures actual pad-centre distance in footprint coordinates.
    @param pads Independently parsed actual footprint pads.
    @param first First exact pad number or origin.
    @param second Second exact pad number or origin.
    @return Euclidean distance in millimetres.
    @details Missing pad identities fail rather than falling back to a point.
    """
    points = {pad["number"]: pad["centre"] for pad in pads}
    points["Origin"] = [0, 0]
    return math.dist(points[first], points[second])


class InspectionPanel(wx.Panel):
    """@brief Owns navigation, visibility and actual pin/pad inspection.
    @details Controls affect the display camera only.
    """

    def __init__(self, parent, viewer):
        """@brief Builds independent controls around a bound viewer scene.
        @param parent Scrollable viewer content owner.
        @param viewer Placement frame and exact source binding.
        @return None.
        @details Missing graphic layers remain absent without synthesized data.
        """
        super().__init__(parent)
        self.viewer = viewer
        layout = wx.BoxSizer(wx.VERTICAL)
        layout.Add(
            wx.StaticText(
                self,
                label="Drag: rotate; Shift-drag: pan; "
                "wheel: zoom. Camera changes are display only.",
            ),
            0,
            wx.EXPAND | wx.ALL,
            4,
        )
        presets = wx.WrapSizer(wx.HORIZONTAL)
        for name in [*PRESETS, "Fit view"]:
            button = wx.Button(self, label=name)
            button.Bind(
                wx.EVT_BUTTON, lambda event, key=name: self.preset(key)
            )
            presets.Add(button, 0, wx.ALL, 2)
        layout.Add(presets, 0, wx.EXPAND)
        layers = wx.WrapSizer(wx.HORIZONTAL)
        self.layers = {}
        visible = viewer.camera.setdefault("layers", {})
        for key, label in LAYERS.items():
            control = wx.CheckBox(self, label=label)
            control.SetValue(visible.get(key, True))
            control.Bind(
                wx.EVT_CHECKBOX, lambda event, layer=key: self.layer(layer)
            )
            layers.Add(control, 0, wx.ALL, 4)
            self.layers[key] = control
        layout.Add(layers, 0, wx.EXPAND)
        from .scene import parse_footprint

        self.pads = parse_footprint(viewer.source.footprint)
        choices = ["Origin", *(pad["number"] for pad in self.pads)]
        row = wx.WrapSizer(wx.HORIZONTAL)
        self.first = wx.Choice(self, choices=choices)
        self.second = wx.Choice(self, choices=choices)
        self.first.SetSelection(1)
        self.second.SetSelection(min(2, len(choices) - 1))
        for item in (self.first, self.second):
            row.Add(item, 0, wx.ALL, 4)
            item.Bind(wx.EVT_CHOICE, self.measure)
        layout.Add(row, 0, wx.EXPAND)
        self.measurement = wx.StaticText(self)
        layout.Add(self.measurement, 0, wx.EXPAND | wx.ALL, 4)
        self.placement = wx.TextCtrl(
            self, style=wx.TE_MULTILINE | wx.TE_READONLY
        )
        self.placement.SetMinSize((-1, 135))
        self.placement.ChangeValue(
            canonical_json(viewer.binding["placement"]).decode()
        )
        layout.Add(
            wx.StaticText(
                self,
                label="Artifact placement: offsets mm; "
                "rotations deg; XYZ scale dimensionless (read only); mirrors",
            ),
            0,
            wx.EXPAND | wx.ALL,
            4,
        )
        layout.Add(self.placement, 0, wx.EXPAND)
        self.SetSizer(layout)
        self.measure(None)

    def preset(self, name):
        """@brief Selects a display orientation or fits the retained scene.
        @param name Supported preset label.
        @return None.
        @details No IR, artifact hash or approval binding is written.
        """
        camera = self.viewer.camera
        if name in PRESETS:
            camera["yaw"], camera["elevation"] = PRESETS[name]
        camera.update(pan=[0, 0], zoom=1.0)
        self.viewer.request_frame()

    def layer(self, key):
        """@brief Changes one independent display layer.
        @param key Supported layer identity.
        @return None.
        @details Geometry and stored engineering placement remain unchanged.
        """
        self.viewer.camera["layers"][key] = self.layers[key].GetValue()
        self.viewer.request_frame()

    def measure(self, _event):
        """@brief Selects a pad and displays actual mapping and distance.
        @param _event wx selection event or initial refresh.
        @return None.
        @details Pad centres are exact footprint geometry; STEP bounds use
        the declared 0.01 mm tessellation tolerance.
        """
        first, second = (
            item.GetStringSelection() for item in (self.first, self.second)
        )
        self.viewer.camera["selected_pad"] = first
        pins = [
            pin
            for pin in self.viewer.binding.get("pins", [])
            if str(pin.get("number")) == first
        ]
        self.measurement.SetLabel(
            f"{first} → {second}: "
            f"{distance_mm(self.pads, first, second):.6f} mm\n"
            f"Pin mapping: {canonical_json(pins).decode()}\n"
            "STEP dimensions appear in viewport; mesh tolerance 0.01 mm."
        )
        self.measurement.Wrap(480)
        self.viewer.request_frame()
