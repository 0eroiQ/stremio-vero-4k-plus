import QtQuick 2.15
import QtQuick.Window 2.15
import QtWebEngine 1.10

Window {
    id: window
    visible: true
    visibility: Window.FullScreen
    color: "black"
    title: "Stremio for Vero 4K+"

    WebEngineView {
        id: stremio
        anchors.fill: parent
        focus: true
        url: "http://127.0.0.1:8765/"

        Component.onCompleted: forceActiveFocus()

        onNewViewRequested: function(request) {
            request.openIn(stremio)
        }
    }
}
