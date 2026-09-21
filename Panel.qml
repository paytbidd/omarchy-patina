import QtQuick
import QtQuick.Controls
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import qs.Commons
import qs.Ui
import "Model.js" as Model

Item {
  id: root

  property var shell: null
  property var manifest: null
  property bool opened: false
  property bool closingFromHost: false

  property bool applied: true
  property string gaps: "tight"
  property string corners: "soft"
  property int borderSize: 2
  property bool glow: true
  property bool applying: false
  property var queuedSet: null

  property string focusSection: "enabled"
  property int selectedIndex: 0
  property bool cursorActive: false

  readonly property string pluginId: (manifest && manifest.id) || "payton.patina"
  readonly property string bin: {
    var home = Quickshell.env("HOME") || ""
    return home + "/.config/omarchy/plugins/payton.patina/scripts/omarchy-patina"
  }
  readonly property color foreground: Color.foreground
  readonly property color background: Color.popups.background
  readonly property color accent: Color.accent
  readonly property string fontFamily: Style.font.family
  readonly property var fakeBar: QtObject {
    readonly property color foreground: root.foreground
    readonly property color background: root.background
    readonly property color urgent: Color.urgent
    readonly property string fontFamily: root.fontFamily
    readonly property string position: "top"
    readonly property bool vertical: false
    readonly property int barSize: 26
  }
  readonly property var visibleSections: ["enabled", "gaps", "corners", "border", "glow"]

  function open(payloadJson) {
    closingFromHost = false
    opened = true
    cursorActive = false
    focusSection = "enabled"
    selectedIndex = 0
    refresh()
    Qt.callLater(function() {
      if (root.opened && keyCatcher) keyCatcher.forceActiveFocus()
    })
  }

  function close() {
    closingFromHost = true
    opened = false
    closingFromHost = false
  }

  function dismiss() {
    if (shell && typeof shell.hide === "function") shell.hide(pluginId)
    else close()
  }

  function refresh() {
    if (!getProc.running) getProc.running = true
  }

  function applyState(raw) {
    var state = Model.parseState(raw)
    applied = state.applied
    gaps = state.gaps
    corners = state.corners
    borderSize = state.border_size
    glow = state.glow
  }

  function setValues(updates) {
    var payload = {}
    for (var i = 0; i < updates.length; i += 2)
      payload[updates[i]] = updates[i + 1]
    var args = [root.bin, "set", "--json", JSON.stringify(payload)]
    if (setProc.running) {
      queuedSet = args
      return
    }
    queuedSet = null
    applying = true
    setProc.command = args
    setProc.running = true
  }

  function setBorder(value) {
    borderSize = Math.max(1, Math.min(16, Math.round(value)))
    debounce.restart()
  }

  function flushBorder() {
    debounce.stop()
    setValues(["border_size", borderSize])
  }

  function sectionIsHorizontal(section) {
    return section === "gaps" || section === "corners" || section === "border"
  }

  function moveCursor(delta) {
    var sections = visibleSections
    var sIdx = sections.indexOf(focusSection)
    if (sIdx < 0) {
      focusSection = sections[0]
      selectedIndex = 0
      return
    }
    if (delta > 0 && sIdx < sections.length - 1) {
      focusSection = sections[sIdx + 1]
      selectedIndex = 0
    } else if (delta < 0 && sIdx > 0) {
      focusSection = sections[sIdx - 1]
      selectedIndex = 0
    }
  }

  function moveCursorH(delta) {
    if (focusSection === "border") {
      setBorder(borderSize + delta)
      return
    }
    if (focusSection === "gaps") {
      var gapOpts = ["tight", "default", "loose"]
      var g = Math.max(0, Math.min(2, gapOpts.indexOf(gaps)))
      selectedIndex = Math.max(0, Math.min(2, g + delta))
      return
    }
    if (focusSection === "corners") {
      var cornerOpts = ["sharp", "soft", "round"]
      var c = Math.max(0, Math.min(2, cornerOpts.indexOf(corners)))
      selectedIndex = Math.max(0, Math.min(2, c + delta))
    }
  }

  function activateCursor() {
    if (focusSection === "enabled") {
      applied = !applied
      setValues(["applied", applied])
    } else if (focusSection === "glow") {
      glow = !glow
      setValues(["glow", glow])
    } else if (focusSection === "gaps") {
      var gapOpts = ["tight", "default", "loose"]
      setValues(["gaps", gapOpts[selectedIndex] || gaps])
    } else if (focusSection === "corners") {
      var cornerOpts = ["sharp", "soft", "round"]
      setValues(["corners", cornerOpts[selectedIndex] || corners])
    } else if (focusSection === "border") {
      flushBorder()
    }
  }

  Process {
    id: getProc
    command: [root.bin, "get", "--json"]
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: {
        if (debounce.running || setProc.running) return
        root.applyState(text)
      }
    }
  }

  Process {
    id: setProc
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: if (text) root.applyState(text)
    }
    stderr: StdioCollector {
      waitForEnd: true
      onStreamFinished: if (text) console.warn("patina set:", text)
    }
    onRunningChanged: {
      if (running) return
      root.applying = false
      if (root.queuedSet) {
        var args = root.queuedSet
        root.queuedSet = null
        root.applying = true
        command = args
        running = true
      }
    }
  }

  Timer {
    id: debounce
    interval: 140
    repeat: false
    onTriggered: root.flushBorder()
  }

  PanelWindow {
    visible: root.opened
    anchors { top: true; bottom: true; left: true; right: true }
    color: "transparent"
    exclusionMode: ExclusionMode.Ignore
    WlrLayershell.namespace: "omarchy-patina"
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.keyboardFocus: root.opened ? WlrKeyboardFocus.Exclusive : WlrKeyboardFocus.None

    Rectangle {
      anchors.fill: parent
      color: Qt.rgba(0, 0, 0, 0.42)
      MouseArea {
        anchors.fill: parent
        onClicked: root.dismiss()
      }
    }

    BorderSurface {
      id: card
      width: Math.min(Style.space(400), parent.width - Style.space(32))
      height: Math.min(column.implicitHeight + card.contentTopInset + card.contentBottomInset, parent.height - Style.space(32))
      anchors.centerIn: parent
      color: root.background
      radius: Style.cornerRadius
      padding: Style.spacing.popupPadding
      borderSpec: Border.surfaceSpec("popups", "border", Color.popups.border, Math.max(1, Style.space(2)))

      MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.AllButtons
      }

      PanelKeyCatcher {
        id: keyCatcher
        anchors.fill: parent
        anchors.topMargin: card.contentTopInset
        anchors.rightMargin: card.contentRightInset
        anchors.bottomMargin: card.contentBottomInset
        anchors.leftMargin: card.contentLeftInset
        onMoveRequested: function(dx, dy) {
          if (!root.cursorActive) { root.cursorActive = true; return }
          if (dy !== 0) root.moveCursor(dy)
          else if (dx !== 0) root.moveCursorH(dx)
        }
        onActivateRequested: if (root.cursorActive) root.activateCursor()
        onCloseRequested: root.dismiss()

        Column {
          id: column
          width: parent.width
          spacing: Style.space(14)

          PanelHero {
            width: parent.width
            foreground: root.foreground
            fontFamily: root.fontFamily
            title: "Patina"
            meta: root.applied ? "On this workspace" : "Off — stock theme chrome"
            iconComponent: Component {
              Text {
                text: "󰃌"
                color: root.foreground
                font.family: root.fontFamily
                font.pixelSize: Style.font.display
              }
            }
          }

          Toggle {
            width: parent.width
            label: "Enabled"
            description: "Apply Patina chrome to the current theme."
            foreground: root.foreground
            accent: root.accent
            fontFamily: root.fontFamily
            checked: root.applied
            hasCursor: root.cursorActive && root.focusSection === "enabled"
            onHovered: function(on) {
              if (!on) return
              root.cursorActive = true
              root.focusSection = "enabled"
              root.selectedIndex = 0
            }
            onClicked: {
              root.applied = !root.applied
              root.setValues(["applied", root.applied])
            }
          }

          Column {
            width: parent.width
            spacing: Style.space(6)

            PanelSectionHeader {
              text: "GAPS"
              foreground: root.foreground
              fontFamily: root.fontFamily
            }

            ButtonGroup {
              width: parent.width
              foreground: root.foreground
              background: root.background
              accent: root.accent
              fontFamily: root.fontFamily
              focusable: false
              cursorIndex: root.cursorActive && root.focusSection === "gaps" ? root.selectedIndex : -1
              value: root.gaps
              options: [
                { value: "tight", label: "Tight" },
                { value: "default", label: "Default" },
                { value: "loose", label: "Loose" }
              ]
              onChanged: function(v) { root.setValues(["gaps", v]) }
              onHovered: function(index, on) {
                if (!on) return
                root.cursorActive = true
                root.focusSection = "gaps"
                root.selectedIndex = index
              }
            }
          }

          Column {
            width: parent.width
            spacing: Style.space(6)

            PanelSectionHeader {
              text: "CORNERS"
              foreground: root.foreground
              fontFamily: root.fontFamily
            }

            ButtonGroup {
              width: parent.width
              foreground: root.foreground
              background: root.background
              accent: root.accent
              fontFamily: root.fontFamily
              focusable: false
              cursorIndex: root.cursorActive && root.focusSection === "corners" ? root.selectedIndex : -1
              value: root.corners
              options: [
                { value: "sharp", label: "Sharp" },
                { value: "soft", label: "Soft" },
                { value: "round", label: "Round" }
              ]
              onChanged: function(v) { root.setValues(["corners", v]) }
              onHovered: function(index, on) {
                if (!on) return
                root.cursorActive = true
                root.focusSection = "corners"
                root.selectedIndex = index
              }
            }
          }

          Column {
            width: parent.width
            spacing: Style.space(6)

            Item {
              width: parent.width
              implicitHeight: Math.max(borderHeader.implicitHeight, borderValue.implicitHeight)

              PanelSectionHeader {
                id: borderHeader
                text: "BORDER"
                foreground: root.foreground
                fontFamily: root.fontFamily
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
              }

              Text {
                id: borderValue
                textFormat: Text.PlainText
                text: root.borderSize + "px"
                color: Qt.darker(root.foreground, 1.4)
                font.family: root.fontFamily
                font.pixelSize: Style.font.caption
                font.bold: true
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
              }
            }

            CursorSurface {
              id: borderRow
              width: parent.width
              height: borderSlider.implicitHeight + Style.spacing.controlGap
              hasCursor: root.cursorActive && root.focusSection === "border"
              foreground: root.foreground
              outline: true

              PanelSlider {
                id: borderSlider
                bar: root.fakeBar
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.leftMargin: Style.space(10)
                anchors.rightMargin: Style.space(10)
                minimum: 1
                maximum: 16
                step: 1
                integer: true
                tickCount: 8
                value: root.borderSize
                onMoved: function(v) {
                  root.cursorActive = true
                  root.focusSection = "border"
                  root.setBorder(v)
                }
                onReleased: function(v) {
                  root.setBorder(v)
                  root.flushBorder()
                }
              }

              HoverHandler {
                onHoveredChanged: if (hovered) {
                  root.cursorActive = true
                  root.focusSection = "border"
                  root.selectedIndex = 0
                }
              }
            }
          }

          Toggle {
            width: parent.width
            label: "Glow"
            description: "Hue-matched halo on the focused window."
            foreground: root.foreground
            accent: root.accent
            fontFamily: root.fontFamily
            checked: root.glow
            hasCursor: root.cursorActive && root.focusSection === "glow"
            onHovered: function(on) {
              if (!on) return
              root.cursorActive = true
              root.focusSection = "glow"
              root.selectedIndex = 0
            }
            onClicked: {
              root.glow = !root.glow
              root.setValues(["glow", root.glow])
            }
          }
        }
      }
    }
  }
}
