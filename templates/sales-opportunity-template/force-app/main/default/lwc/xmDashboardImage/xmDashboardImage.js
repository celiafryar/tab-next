import { LightningElement, api } from "lwc";
import LOGO from "@salesforce/resourceUrl/APEX_essential_components";

/**
 * xmDashboardImage: a zero-dependency image widget for Tableau Next dashboards.
 *
 * Shows a packaged static resource. The resource URL is resolved at build time
 * through @salesforce/resourceUrl, so the package namespace is applied
 * automatically in subscriber orgs. No external URLs, no ContentAsset lookup.
 *
 * Config values arrive as strings from the dashboard config panel even when
 * typed Integer, so numeric inputs are coerced and clamped.
 */
export default class XmDashboardImage extends LightningElement {
  @api staticResourceName; // optional override; blank = packaged logo
  @api imageScale = "Fit to Height"; // Fit to Width | Fit to Height | Fill | Original
  @api horizontalAlignment = "Center"; // Left | Center | Right
  @api verticalAlignment = "Middle"; // Top | Middle | Bottom
  @api imageOpacity = 100; // 0..100
  @api backgroundColor; // optional CSS color behind the image
  @api altText = "Company logo";

  get resolvedSrc() {
    const name = (this.staticResourceName || "").trim();
    if (name) return `/resource/${encodeURIComponent(name)}`;
    return LOGO;
  }

  get containerStyle() {
    const parts = [
      "display:flex",
      "width:100%",
      "height:100%",
      "overflow:hidden",
      `justify-content:${this._justifyContent}`,
      `align-items:${this._alignItems}`,
      `opacity:${this._opacity}`
    ];
    const bg = (this.backgroundColor || "").trim();
    if (bg) parts.push(`background-color:${bg}`);
    return parts.join(";") + ";";
  }

  get imageStyle() {
    const scale = (this.imageScale || "").toLowerCase();
    let parts;
    switch (scale) {
      case "fit to width":
        parts = ["width:100%", "height:auto", "max-height:100%"];
        break;
      case "fill":
        parts = [
          "width:100%",
          "height:100%",
          "object-fit:cover",
          `object-position:${this._objectPosition}`
        ];
        break;
      case "original":
        parts = ["width:auto", "height:auto", "max-width:none", "max-height:none"];
        break;
      case "fit to height":
      default:
        parts = ["height:100%", "width:auto", "max-width:100%"];
        break;
    }
    parts.push("display:block");
    return parts.join(";") + ";";
  }

  get resolvedAlt() {
    return (this.altText || "").trim();
  }

  get _opacity() {
    let n = Number(this.imageOpacity);
    if (!Number.isFinite(n)) n = 100;
    n = Math.max(0, Math.min(100, n));
    return n / 100;
  }

  get _justifyContent() {
    switch ((this.horizontalAlignment || "").toLowerCase()) {
      case "left":
        return "flex-start";
      case "right":
        return "flex-end";
      default:
        return "center";
    }
  }

  get _alignItems() {
    switch ((this.verticalAlignment || "").toLowerCase()) {
      case "top":
        return "flex-start";
      case "bottom":
        return "flex-end";
      default:
        return "center";
    }
  }

  get _objectPosition() {
    const h = (this.horizontalAlignment || "").toLowerCase();
    const v = (this.verticalAlignment || "").toLowerCase();
    const x = h === "left" || h === "right" ? h : "center";
    const y = v === "top" || v === "bottom" ? v : "center";
    return `${x} ${y}`;
  }
}
