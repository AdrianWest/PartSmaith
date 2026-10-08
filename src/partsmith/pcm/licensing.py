"""@package partsmith.pcm.licensing
@brief Verifies the recorded additional CAD vendor redistribution inputs.
@details This bounded supplement does not approve opaque native dependencies
in other wheels or the cached OCP/OCCT SDK's header-only build inputs.
"""

CAD_PREFIX = "runtime/Lib/site-packages/cadquery_ocp.libs/"
VENDORS = {
    "freeimage",
    "freetype",
    "imath",
    "jxrlib",
    "lcms2",
    "lerc",
    "libdeflate",
    "libjpeg-turbo",
    "liblzma",
    "libpng",
    "libraw",
    "libtiff",
    "libwebp-base",
    "libzlib",
    "openexr",
    "openjpeg",
    "openjph",
    "vc14_runtime",
    "vcomp14",
    "zstd",
}


def validate_cad_vendors(lock: dict, ledger: dict) -> None:
    """@brief Verifies source, notice, binary and component ownership coverage.
    @param lock Current production input lock.
    @param ledger Reviewed additional CAD vendor evidence.
    @return None.
    @details Unknown DLLs, changed identities, absent sources and missing
    original notices fail before packaging; this is not a full runtime audit.
    """
    if ledger.get("schema_version") != "partsmith-cad-vendors-1.0":
        raise ValueError("CAD_VENDOR_LEDGER_VERSION")
    wheel = lock["artifacts"].get(
        "cadquery_ocp-7.9.3.1.1-cp312-cp312-win_amd64.whl"
    )
    if ledger.get("wheel") != wheel or wheel is None:
        raise ValueError("CAD_VENDOR_WHEEL_CHANGED")
    vendors = ledger.get("vendors", [])
    if (
        len(vendors) != len(VENDORS)
        or {v.get("name") for v in vendors} != VENDORS
    ):
        raise ValueError("CAD_VENDOR_COMPONENT_COVERAGE")
    expected = {
        p
        for p in lock["files"]
        if p.startswith(CAD_PREFIX)
        and p.lower().endswith(".dll")
        and p not in ledger.get("occt_binaries", {})
    }
    for path, identity in ledger.get("occt_binaries", {}).items():
        if not path.startswith(CAD_PREFIX + "TK") or any(
            lock["files"].get(path, {}).get(k) != identity[k]
            for k in ("sha256", "size")
        ):
            raise ValueError("CAD_SDK_BINARY_IDENTITY_CHANGED")
    for material in ledger.get("core_source_material", []) + ledger.get(
        "producer_tools", []
    ):
        if any(
            lock["files"].get(material["path"], {}).get(k) != material[k]
            for k in ("sha256", "size")
        ):
            raise ValueError("CAD_VENDOR_SOURCE_MATERIAL_CHANGED")
    covered = set()
    for vendor in vendors:
        component = next(
            (
                c
                for c in lock["components"]
                if c["name"] == "cad-vendor-" + vendor["name"]
            ),
            None,
        )
        if component is None or component["version"] != vendor["version"]:
            raise ValueError("CAD_VENDOR_COMPONENT_CHANGED")
        original = lock["artifacts"].get(vendor["package"])
        if original != vendor["package_identity"] or (
            original["sha256"] != component["sha256"]
            or original["url"] != component["source"]
        ):
            raise ValueError("CAD_VENDOR_PACKAGE_CHANGED")
        if not vendor["notices"] or not vendor["sources"]:
            raise ValueError("CAD_VENDOR_REDISTRIBUTION_INPUT_MISSING")
        if (
            component["license_files"] != vendor["notices"]
            or component["license"] != vendor["selected_license"]
        ):
            raise ValueError("CAD_VENDOR_NOTICE_COVERAGE")
        records = (
            [
                {"path": path, **identity}
                for path, identity in vendor["notices"].items()
            ]
            + vendor["sources"]
            + list(vendor["build_inputs"].values())
        )
        for record in records:
            path = record["path"]
            identity = lock["files"].get(path, {})
            if not path.startswith("licenses/cad-native/") or (
                path not in component["files"]
                or any(
                    identity.get(k) != record[k] for k in ("sha256", "size")
                )
            ):
                raise ValueError("CAD_VENDOR_REDISTRIBUTION_INPUT_CHANGED")
        for binary in vendor["binaries"]:
            path = binary["path"]
            if (
                path not in expected
                or path in covered
                or (
                    binary.get("exact_repair_match") is not True
                    or binary["repaired_sha256"] != binary["bundled_sha256"]
                    or binary["bundled_sha256"]
                    != lock["files"][path]["sha256"]
                    or path not in component["files"]
                    or binary["version"] != vendor["version"]
                )
            ):
                raise ValueError("CAD_VENDOR_BINARY_PROOF_CHANGED")
            if vendor["name"] in {"vc14_runtime", "vcomp14"} and (
                binary["original_sha256"] != binary["bundled_sha256"]
            ):
                raise ValueError("CAD_MICROSOFT_BINARY_MODIFIED")
            covered.add(path)
    if covered != expected or len(covered) != 24:
        raise ValueError("CAD_VENDOR_BINARY_COVERAGE")
    jxr = next(v for v in vendors if v["name"] == "jxrlib")
    freeimage = next(v for v in vendors if v["name"] == "freeimage")
    jxr_component = next(
        c for c in lock["components"] if c["name"] == "cad-vendor-jxrlib"
    )
    if jxr["linkage"] != "STATIC_IN_FREEIMAGE" or not all(
        b["path"] in jxr_component["files"] for b in freeimage["binaries"]
    ):
        raise ValueError("CAD_STATIC_JXR_COVERAGE")
