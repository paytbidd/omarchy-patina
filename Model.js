function parseState(raw) {
  var state = {
    applied: true,
    gaps: "default",
    corners: "soft",
    rounding: 6,
    border_size: 2,
    glow: false
  }
  try {
    var parsed = JSON.parse(String(raw || "{}"))
    if (parsed && typeof parsed === "object") {
      if (parsed.applied !== undefined) state.applied = !!parsed.applied
      if (parsed.gaps) state.gaps = String(parsed.gaps)
      if (parsed.corners) state.corners = String(parsed.corners)
      if (parsed.rounding !== undefined) state.rounding = Number(parsed.rounding)
      if (parsed.border_size !== undefined) state.border_size = Number(parsed.border_size)
      if (parsed.glow !== undefined) state.glow = !!parsed.glow
    }
  } catch (e) {}
  if (state.border_size < 1) state.border_size = 1
  if (state.border_size > 16) state.border_size = 16
  return state
}
